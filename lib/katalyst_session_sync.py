#!/usr/bin/env python3
"""Read-only Cursor/Codex transcript importer for resumable OMP sessions."""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import sqlite3
import tempfile
import uuid
from typing import Any, Iterable


SESSION_NAMESPACE = uuid.UUID("b82684c4-41de-4bc0-a9ec-66bd09f55454")
PROVENANCE_TYPE = "dev.katalyst.foreign-session"


@dataclasses.dataclass
class ImportedMessage:
    role: str
    text: str
    timestamp: str
    kind: str = "text"
    tool_id: str | None = None
    tool_name: str | None = None
    tool_arguments: Any = None
    images: list[dict[str, str]] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class ImportedSession:
    source: str
    source_id: str
    source_path: Path
    cwd: str
    title: str
    timestamp: str
    updated_at: str
    archived: bool
    messages: list[ImportedMessage]
    source_hash: str
    warnings: int = 0
    model: str | None = None
    branches: Any = None


def iso_timestamp(value: Any, fallback: float | None = None) -> str:
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 10_000_000_000 else value
        return dt.datetime.fromtimestamp(seconds, dt.timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, str) and value:
        try:
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            pass
    return dt.datetime.fromtimestamp(fallback or 0, dt.timezone.utc).isoformat().replace("+00:00", "Z")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_from_blocks(blocks: Any, accepted: set[str]) -> str:
    if isinstance(blocks, str):
        return blocks
    if not isinstance(blocks, list):
        return ""
    return "\n".join(
        str(block.get("text", ""))
        for block in blocks
        if isinstance(block, dict) and block.get("type") in accepted and block.get("text")
    ).strip()


def reconstruct_cursor_cwd(encoded: str, home: Path) -> str:
    if encoded in {"", "empty-window", "unknown"}:
        return str(home)
    tokens = encoded.split("-")
    current = Path("/")
    index = 0
    while index < len(tokens):
        chosen = None
        for end in range(len(tokens), index, -1):
            candidate = current / "-".join(tokens[index:end])
            if candidate.exists():
                chosen = candidate
                index = end
                break
        if chosen is None:
            current = current / tokens[index]
            index += 1
        else:
            current = chosen
    return str(current)


def cursor_metadata(home: Path) -> dict[str, dict[str, Any]]:
    db = home / "Library/Application Support/Cursor/User/globalStorage/conversation-search.db"
    if not db.is_file():
        return {}
    result: dict[str, dict[str, Any]] = {}
    try:
        connection = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        for row in connection.execute(
            "SELECT id, title, updated_at, is_archived, branches FROM conversations"
        ):
            result[str(row[0])] = {
                "title": row[1] or "",
                "updated_at": row[2],
                "archived": bool(row[3]),
                "branches": row[4],
            }
        connection.close()
    except (sqlite3.Error, OSError):
        return {}
    return result


def scan_cursor(root: Path, home: Path) -> list[ImportedSession]:
    metadata = cursor_metadata(home)
    sessions: list[ImportedSession] = []
    for path in sorted(root.glob("*/agent-transcripts/*/*.jsonl")):
        source_id = path.stem
        messages: list[ImportedMessage] = []
        external_files: set[Path] = set()
        warnings = 0
        fallback_time = path.stat().st_mtime
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    warnings += 1
                    continue
                role = row.get("role")
                message = row.get("message")
                if role not in {"user", "assistant"} or not isinstance(message, dict):
                    continue
                timestamp = iso_timestamp(row.get("timestamp") or message.get("timestamp"), fallback_time)
                parts: list[str] = []
                content = message.get("content", [])
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") == "text" and block.get("text"):
                            parts.append(str(block["text"]))
                        elif block.get("type") in {"thinking", "reasoning"} and block.get("text"):
                            parts.append(f"[Historical Cursor reasoning]\n{block['text']}")
                        elif block.get("type") == "tool_use":
                            name = str(block.get("name") or "unknown")
                            tool_input = json.dumps(block.get("input", {}), ensure_ascii=False, sort_keys=True)
                            parts.append(f"[Historical Cursor tool call: {name}]\n{tool_input}")
                            for match in re.findall(r"agent-tools[/\\\\]([0-9a-fA-F-]{36}\.txt)", tool_input):
                                external_path = path.parents[2] / "agent-tools" / match
                                if external_path.is_file():
                                    external_files.add(external_path)
                                    output = external_path.read_text(encoding="utf-8", errors="replace")
                                    parts.append(
                                        f"[Historical Cursor external tool output: {match}]\n{output}"
                                    )
                        elif block.get("type") in {"tool_result", "tool_output"}:
                            output = block.get("content") or block.get("output") or ""
                            if not isinstance(output, str):
                                output = json.dumps(output, ensure_ascii=False, sort_keys=True)
                            parts.append(f"[Historical Cursor tool result]\n{output}")
                text = "\n\n".join(part for part in parts if part).strip()
                if text:
                    messages.append(ImportedMessage(role, text, timestamp))
        if not messages:
            continue
        info = metadata.get(source_id, {})
        project_key = path.parents[2].name
        title = str(info.get("title") or messages[0].text.splitlines()[0][:120] or "Cursor session")
        timestamp = messages[0].timestamp
        updated = iso_timestamp(info.get("updated_at"), fallback_time)
        digest = hashlib.sha256(path.read_bytes())
        digest.update(json.dumps(info, ensure_ascii=False, sort_keys=True).encode())
        for external_path in sorted(external_files):
            digest.update(str(external_path).encode())
            digest.update(external_path.read_bytes())
        sessions.append(
            ImportedSession(
                source="cursor",
                source_id=source_id,
                source_path=path,
                cwd=reconstruct_cursor_cwd(project_key, home),
                title=title,
                timestamp=timestamp,
                updated_at=updated,
                archived=bool(info.get("archived", False)),
                messages=messages,
                source_hash=digest.hexdigest(),
                warnings=warnings,
                branches=info.get("branches"),
            )
        )
    return sessions


def codex_titles(root: Path) -> dict[str, str]:
    path = root / "session_index.jsonl"
    titles: dict[str, str] = {}
    if not path.is_file():
        return titles
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("id") and row.get("thread_name"):
                titles[str(row["id"])] = str(row["thread_name"])
    return titles


def codex_historical_message(payload: dict[str, Any], timestamp: str) -> ImportedMessage | None:
    item_type = payload.get("type")
    if item_type == "message" and payload.get("role") in {"user", "assistant"}:
        text = text_from_blocks(payload.get("content"), {"input_text", "output_text", "text"})
        images: list[dict[str, str]] = []
        references: list[str] = []
        for block in payload.get("content", []) if isinstance(payload.get("content"), list) else []:
            if not isinstance(block, dict) or block.get("type") != "input_image":
                continue
            image_url = block.get("image_url")
            if isinstance(image_url, str):
                match = re.match(r"^data:([^;,]+);base64,(.+)$", image_url, re.S)
                if match:
                    images.append({"mimeType": match.group(1), "data": match.group(2)})
                else:
                    references.append(f"[Historical Codex image reference: {image_url}]")
        combined = "\n".join(part for part in [text, *references] if part)
        return ImportedMessage(str(payload["role"]), combined, timestamp, images=images) if combined or images else None
    if item_type == "reasoning":
        text = text_from_blocks(payload.get("summary"), {"summary_text", "text"})
        text = text or text_from_blocks(payload.get("content"), {"reasoning_text", "text"})
        return ImportedMessage("assistant", text, timestamp, "thinking") if text else None
    if item_type in {"function_call", "custom_tool_call"}:
        name = str(payload.get("name") or "unknown")
        arguments = payload.get("arguments", payload.get("input", ""))
        if not isinstance(arguments, str):
            arguments = json.dumps(arguments, ensure_ascii=False, sort_keys=True)
        try:
            parsed_arguments = json.loads(arguments)
        except json.JSONDecodeError:
            parsed_arguments = {"input": arguments}
        call_id = str(payload.get("call_id") or payload.get("id") or "")
        return ImportedMessage("assistant", "", timestamp, "tool_call", call_id, name, parsed_arguments)
    if item_type in {"function_call_output", "custom_tool_call_output"}:
        output = payload.get("output", "")
        if not isinstance(output, str):
            output = json.dumps(output, ensure_ascii=False, sort_keys=True)
        call_id = str(payload.get("call_id") or "")
        return ImportedMessage("toolResult", output, timestamp, "tool_result", call_id, None)
    return None


def scan_codex(root: Path) -> list[ImportedSession]:
    titles = codex_titles(root)
    sessions: list[ImportedSession] = []
    paths = list((root / "sessions").glob("**/rollout-*.jsonl"))
    paths.extend((root / "archived_sessions").glob("**/rollout-*.jsonl"))
    for path in sorted(paths):
        meta: dict[str, Any] = {}
        response_messages: list[ImportedMessage] = []
        event_messages: list[ImportedMessage] = []
        warnings = 0
        model = None
        tool_names: dict[str, str] = {}
        fallback_time = path.stat().st_mtime
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    warnings += 1
                    continue
                payload = row.get("payload", {})
                if row.get("type") == "session_meta" and isinstance(payload, dict):
                    meta = payload
                elif row.get("type") == "turn_context" and isinstance(payload, dict):
                    model = payload.get("model") or model
                elif row.get("type") == "response_item" and isinstance(payload, dict):
                    timestamp = iso_timestamp(row.get("timestamp"), fallback_time)
                    converted = codex_historical_message(payload, timestamp)
                    if converted:
                        if converted.kind == "tool_call" and converted.tool_id and converted.tool_name:
                            tool_names[converted.tool_id] = converted.tool_name
                        elif converted.kind == "tool_result" and converted.tool_id:
                            converted.tool_name = tool_names.get(converted.tool_id, "unknown")
                        response_messages.append(converted)
                elif row.get("type") == "event_msg" and isinstance(payload, dict):
                    if payload.get("type") in {"user_message", "agent_message"} and payload.get("message"):
                        role = "user" if payload["type"] == "user_message" else "assistant"
                        event_messages.append(
                            ImportedMessage(role, str(payload["message"]), iso_timestamp(row.get("timestamp"), fallback_time))
                        )
                elif row.get("type") == "compacted" and isinstance(payload, dict):
                    summary = payload.get("message") or payload.get("summary")
                    if isinstance(summary, str) and summary.strip():
                        response_messages.append(
                            ImportedMessage(
                                "assistant",
                                f"[Historical Codex compaction]\n{summary.strip()}",
                                iso_timestamp(row.get("timestamp"), fallback_time),
                                "thinking",
                            )
                        )
        messages = response_messages or event_messages
        if not meta or not messages:
            continue
        # `session_meta.id` identifies the parent Codex thread in some
        # rollouts, so several independent transcript files can share it.
        # The final UUID in a rollout filename is the stable session identity.
        matches = re.findall(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
            path.stem,
        )
        source_id = matches[-1] if matches else str(meta.get("session_id") or meta.get("id") or path.stem)
        title = titles.get(source_id) or messages[0].text.splitlines()[0][:120] or "Codex session"
        sessions.append(
            ImportedSession(
                source="codex",
                source_id=source_id,
                source_path=path,
                cwd=str(meta.get("cwd") or root.parent),
                title=title,
                timestamp=iso_timestamp(meta.get("timestamp"), fallback_time),
                updated_at=iso_timestamp(path.stat().st_mtime, fallback_time),
                archived="archived_sessions" in path.parts,
                messages=messages,
                source_hash=file_hash(path),
                warnings=warnings,
                model=str(model) if model else None,
            )
        )
    return sessions


def title_slot(title: str, updated_at: str) -> str:
    safe_title = title.replace("\n", " ").strip()
    base = {"type": "title", "v": 1, "title": safe_title, "updatedAt": updated_at, "pad": ""}
    encoded = json.dumps(base, ensure_ascii=False, separators=(",", ":"))
    target_without_newline = 255
    available = target_without_newline - len(encoded.encode("utf-8"))
    if available < 0:
        while available < 0 and safe_title:
            safe_title = safe_title[:-1]
            base["title"] = safe_title
            encoded = json.dumps(base, ensure_ascii=False, separators=(",", ":"))
            available = target_without_newline - len(encoded.encode("utf-8"))
    base["pad"] = " " * max(0, available)
    return json.dumps(base, ensure_ascii=False, separators=(",", ":"))


def omp_bucket(cwd: str, home: Path) -> str:
    try:
        relative = Path(cwd).resolve().relative_to(home.resolve())
        encoded = "-" + "-".join(relative.parts)
    except (ValueError, OSError):
        encoded = "--" + cwd.strip("/").replace("/", "-") + "--"
    return encoded or "-home"


def render_omp_session(session: ImportedSession, target_id: str) -> bytes:
    rows: list[dict[str, Any]] = [
        {
            "type": "session",
            "version": 3,
            "id": target_id,
            "title": session.title,
            "titleSource": "user",
            "timestamp": session.timestamp,
            "cwd": session.cwd,
        }
    ]
    parent_id: str | None = None
    if session.model and "/" in session.model:
        entry_id = uuid.uuid5(SESSION_NAMESPACE, f"{target_id}:model").hex[:8]
        rows.append(
            {
                "type": "model_change",
                "id": entry_id,
                "parentId": parent_id,
                "timestamp": session.timestamp,
                "model": session.model,
                "resolvedModelIsFallback": False,
            }
        )
        parent_id = entry_id
    for index, message in enumerate(session.messages):
        entry_id = uuid.uuid5(SESSION_NAMESPACE, f"{target_id}:message:{index}").hex[:8]
        timestamp_ms = int(
            dt.datetime.fromisoformat(message.timestamp.replace("Z", "+00:00")).timestamp() * 1000
        )
        if message.kind == "tool_result":
            rendered_message = {
                "role": "toolResult",
                "toolCallId": message.tool_id or f"historical-{index}",
                "toolName": message.tool_name or "unknown",
                "content": [{"type": "text", "text": message.text}],
                "isError": False,
                "timestamp": timestamp_ms,
            }
        else:
            if message.kind == "tool_call":
                content = [{
                    "type": "toolCall",
                    "id": message.tool_id or f"historical-{index}",
                    "name": message.tool_name or "unknown",
                    "arguments": message.tool_arguments if isinstance(message.tool_arguments, dict) else {"input": message.tool_arguments},
                }]
            else:
                content_type = "thinking" if message.kind == "thinking" else "text"
                content_key = "thinking" if content_type == "thinking" else "text"
                content = []
                if message.text:
                    content.append({"type": content_type, content_key: message.text})
                content.extend(
                    {"type": "image", "mimeType": image["mimeType"], "data": image["data"]}
                    for image in message.images
                )
            rendered_message = {
                "role": message.role,
                "content": content,
                "attribution": "user" if message.role == "user" else "agent",
                "timestamp": timestamp_ms,
            }
        if message.role == "assistant":
            provider = "cursor" if session.source == "cursor" else "openai-codex"
            rendered_message.update(
                {
                    "api": "cursor-agent" if session.source == "cursor" else "openai-codex-responses",
                    "provider": provider,
                    "model": session.model or ("codex" if session.source == "codex" else "imported"),
                    "usage": {
                        "input": 0,
                        "output": 0,
                        "cacheRead": 0,
                        "cacheWrite": 0,
                        "totalTokens": 0,
                        "cost": {
                            "input": 0,
                            "output": 0,
                            "cacheRead": 0,
                            "cacheWrite": 0,
                            "total": 0,
                        },
                    },
                    "stopReason": "toolUse" if message.kind == "tool_call" else "stop",
                }
            )
        rows.append(
            {
                "type": "message",
                "id": entry_id,
                "parentId": parent_id,
                "timestamp": message.timestamp,
                "message": rendered_message,
            }
        )
        parent_id = entry_id
    provenance_id = uuid.uuid5(SESSION_NAMESPACE, f"{target_id}:provenance").hex[:8]
    rows.append(
        {
            "type": "custom",
            "id": provenance_id,
            "parentId": parent_id,
            "timestamp": session.updated_at,
            "customType": PROVENANCE_TYPE,
            "data": {
                "source": session.source,
                "sourceId": session.source_id,
                "sourcePath": str(session.source_path),
                "sourceCwd": session.cwd,
                "sourceHash": session.source_hash,
                "sourceUpdatedAt": session.updated_at,
                "archived": session.archived,
                "branches": session.branches,
                "parseWarnings": session.warnings,
                "targetOmpSessionId": target_id,
            },
        }
    )
    lines = [title_slot(session.title, session.updated_at)] + [
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def load_state(path: Path) -> dict[str, Any]:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(state, dict) and isinstance(state.get("sessions"), dict):
            return state
    except (OSError, json.JSONDecodeError):
        pass
    return {"version": 1, "sessions": {}}


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def target_matches_record(target: Path, record: dict[str, Any]) -> bool:
    try:
        return target.is_file() and file_hash(target) == record.get("targetHash")
    except OSError:
        return False


def discover_sessions(
    sources: Iterable[str], home: Path, cursor_root: Path, codex_root: Path
) -> list[ImportedSession]:
    result: list[ImportedSession] = []
    if "cursor" in sources and cursor_root.exists():
        result.extend(scan_cursor(cursor_root, home))
    if "codex" in sources and codex_root.exists():
        result.extend(scan_codex(codex_root))
    return result


def run_sync(
    sources: list[str],
    home: Path,
    cursor_root: Path,
    codex_root: Path,
    omp_root: Path,
    state_path: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    if dry_run:
        return _run_sync(sources, home, cursor_root, codex_root, omp_root, state_path, True)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_path.with_suffix(state_path.suffix + ".lock")
    with lock_path.open("a+") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        return _run_sync(sources, home, cursor_root, codex_root, omp_root, state_path, False)


def _run_sync(
    sources: list[str],
    home: Path,
    cursor_root: Path,
    codex_root: Path,
    omp_root: Path,
    state_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    state = load_state(state_path)
    counters = {
        "detected": 0,
        "imported": 0,
        "updated": 0,
        "unchanged": 0,
        "owned_by_omp": 0,
        "failed": 0,
        "warnings": 0,
        "would_import": 0,
        "would_update": 0,
        "failures": [],
    }
    sessions = discover_sessions(sources, home, cursor_root, codex_root)
    detected_by_source = {source: 0 for source in sources}
    for session in sessions:
        counters["detected"] += 1
        detected_by_source[session.source] = detected_by_source.get(session.source, 0) + 1
        counters["warnings"] += session.warnings
        key = f"{session.source}:{session.source_id}"
        record = state["sessions"].get(key)
        # A foreign transcript owns one stable OMP session. The source hash is
        # tracked separately so new source turns update that session in place
        # until OMP has added content of its own.
        target_id = str(uuid.uuid5(SESSION_NAMESPACE, key))
        bucket = omp_root / omp_bucket(session.cwd, home)
        target = bucket / f"{session.timestamp.replace(':', '-')}_{target_id}.jsonl"
        if not record and omp_root.exists():
            existing_targets = list(omp_root.rglob(f"*_{target_id}.jsonl"))
            if existing_targets:
                target = existing_targets[0]
        previous_record = record
        if record:
            target = Path(record["targetPath"])
            if not target.is_file():
                record = None
            else:
                if not target_matches_record(target, record):
                    record["ownedByOmp"] = True
                if record.get("ownedByOmp"):
                    counters["owned_by_omp"] += 1
                    continue
                if record.get("sourceHash") == session.source_hash:
                    counters["unchanged"] += 1
                    continue
        elif target.is_file():
            if not dry_run:
                state["sessions"][key] = {
                    "source": session.source,
                    "sourceId": session.source_id,
                    "sourcePath": str(session.source_path),
                    "sourceHash": session.source_hash,
                    "targetId": target_id,
                    "targetPath": str(target),
                    "targetHash": file_hash(target),
                    "ownedByOmp": True,
                    "updatedAt": session.updated_at,
                }
            counters["owned_by_omp"] += 1
            continue
        elif target.exists():
            # A deterministic target without state may have been continued in OMP.
            # Preserve it instead of assuming ownership after state loss.
            counters["owned_by_omp"] += 1
            continue
        content = render_omp_session(session, target_id)
        if dry_run:
            counters["would_update" if record else "would_import"] += 1
            continue
        try:
            atomic_write(target, content)
            state["sessions"][key] = {
                "source": session.source,
                "sourceId": session.source_id,
                "sourcePath": str(session.source_path),
                "sourceHash": session.source_hash,
                "targetId": target_id,
                "targetPath": str(target),
                "targetHash": hashlib.sha256(content).hexdigest(),
                "ownedByOmp": False,
                "updatedAt": session.updated_at,
            }
            counters["updated" if previous_record else "imported"] += 1
        except OSError as error:
            counters["failed"] += 1
            counters["failures"].append(
                {"source": session.source, "sourceId": session.source_id, "error": str(error)}
            )
    if not dry_run:
        state["lastSyncAt"] = iso_timestamp(dt.datetime.now(dt.timezone.utc).isoformat())
        state["detected"] = detected_by_source
        state["lastResult"] = counters
        atomic_write(state_path, (json.dumps(state, indent=2, sort_keys=True) + "\n").encode())
    counters["detected_by_source"] = detected_by_source
    return counters


def status_payload(
    sources: list[str], home: Path, cursor_root: Path, codex_root: Path, state_path: Path
) -> dict[str, Any]:
    state = load_state(state_path)
    cached = state.get("detected", {})
    by_source = {source: int(cached.get(source, 0)) for source in sources}
    records = list(state["sessions"].values())
    return {
        "detected": by_source,
        "imported": len(records),
        "ownedByOmp": sum(1 for record in records if record.get("ownedByOmp")),
        "lastSyncAt": state.get("lastSyncAt"),
        "lastResult": state.get("lastResult", {}),
    }


def parse_sources(value: str) -> list[str]:
    values = [item.strip().lower() for item in value.split(",") if item.strip()]
    invalid = set(values) - {"cursor", "codex"}
    if invalid:
        raise argparse.ArgumentTypeError(f"unsupported source(s): {', '.join(sorted(invalid))}")
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="katalyst-session-sync")
    subparsers = parser.add_subparsers(dest="command", required=True)
    sync_parser = subparsers.add_parser("sync", help="Import new or changed foreign sessions")
    sync_parser.add_argument("--sources", type=parse_sources, default=["cursor", "codex"])
    sync_parser.add_argument("--all", action="store_true", help="Import every detected session")
    sync_parser.add_argument("--dry-run", action="store_true")
    sync_parser.add_argument("--automatic", action="store_true", help=argparse.SUPPRESS)
    sync_parser.add_argument("--json", action="store_true")
    status_parser = subparsers.add_parser("status", help="Show detected and imported session counts")
    status_parser.add_argument("--sources", type=parse_sources, default=["cursor", "codex"])
    status_parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    home = Path.home()
    cursor_root = home / ".cursor" / "projects"
    codex_root = home / ".codex"
    omp_root = home / ".omp" / "agent" / "sessions"
    state_path = home / ".katalyst" / "imports" / "session-sync.json"
    if args.command == "sync":
        if args.automatic and (state_path.parent / "auto-sync-disabled").exists():
            payload = {"skipped": 1, "reason": "automatic sync disabled"}
        else:
            payload = run_sync(
                args.sources, home, cursor_root, codex_root, omp_root, state_path, args.dry_run
            )
    else:
        payload = status_payload(args.sources, home, cursor_root, codex_root, state_path)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif args.command == "status":
        counts = payload["detected"]
        cursor_status = "data detected" if counts.get("cursor", 0) else "not detected"
        codex_status = "data detected" if counts.get("codex", 0) else "not detected"
        failures = payload["lastResult"].get("failures", [])
        failure_suffix = ""
        if failures:
            failed_ids = ", ".join(str(item.get("sourceId", "unknown")) for item in failures[:3])
            failure_suffix = f" · Failed sessions: {failed_ids}"
        print(
            f"Cursor {cursor_status}: {counts.get('cursor', 0)} chats · "
            f"Codex {codex_status}: {counts.get('codex', 0)} chats · {payload['imported']} imported · "
            f"{payload['lastResult'].get('failed', 0)} failed{failure_suffix}"
        )
    else:
        print(
            " · ".join(
                f"{key.replace('_', ' ')}: {value}"
                for key, value in payload.items()
                if value and isinstance(value, (int, float))
            )
            or "No session changes"
        )
    return 1 if payload.get("failed", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
