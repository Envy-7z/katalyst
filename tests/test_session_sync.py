import importlib.util
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import tempfile
import unittest


MODULE_PATH = Path(__file__).parents[1] / "lib" / "katalyst_session_sync.py"
spec = importlib.util.spec_from_file_location("katalyst_session_sync", MODULE_PATH)
sync = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sync
spec.loader.exec_module(sync)


def write_jsonl(path: Path, rows: list[dict], malformed: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
        if malformed:
            handle.write("{partial")


class SessionSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.cursor_root = self.home / ".cursor" / "projects"
        self.codex_root = self.home / ".codex"
        self.omp_root = self.home / ".omp" / "agent" / "sessions"
        self.state_path = self.home / ".katalyst" / "imports" / "session-sync.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_cursor_scan_converts_text_and_tool_history(self) -> None:
        session_id = "11111111-1111-4111-8111-111111111111"
        transcript = (
            self.cursor_root
            / "workspace-demo"
            / "agent-transcripts"
            / session_id
            / f"{session_id}.jsonl"
        )
        external_id = "77777777-7777-4777-8777-777777777777"
        external = transcript.parents[2] / "agent-tools" / f"{external_id}.txt"
        external.parent.mkdir(parents=True)
        external.write_text("external command output", encoding="utf-8")
        database = self.home / "Library/Application Support/Cursor/User/globalStorage/conversation-search.db"
        database.parent.mkdir(parents=True)
        connection = sync.sqlite3.connect(database)
        connection.execute("CREATE TABLE conversations (id TEXT, title TEXT, updated_at TEXT, is_archived INTEGER, branches TEXT)")
        connection.execute(
            "INSERT INTO conversations VALUES (?, ?, ?, ?, ?)",
            (session_id, "Archived Cursor fixture", "2026-09-11T00:00:00Z", 1, '["main"]'),
        )
        connection.commit()
        connection.close()
        write_jsonl(
            transcript,
            [
                {"role": "user", "message": {"content": [{"type": "text", "text": "Fix search"}]}},
                {
                    "role": "assistant",
                    "message": {
                        "content": [
                            {"type": "text", "text": "Checking."},
                            {"type": "tool_use", "name": "Read", "input": {"path": f"agent-tools/{external_id}.txt"}},
                        ]
                    },
                },
                {"type": "unknown_future_event", "value": 1},
            ],
            malformed=True,
        )

        sessions = sync.scan_cursor(self.cursor_root, self.home)

        self.assertEqual(len(sessions), 1)
        session = sessions[0]
        self.assertEqual(session.source_id, session_id)
        self.assertEqual(session.cwd, "/workspace/demo")
        self.assertEqual(session.messages[0].role, "user")
        self.assertIn("Fix search", session.messages[0].text)
        self.assertIn("Historical Cursor tool call: Read", session.messages[1].text)
        self.assertIn("external command output", session.messages[1].text)
        self.assertEqual(session.warnings, 1)
        self.assertTrue(session.archived)
        self.assertEqual(session.title, "Archived Cursor fixture")
        self.assertEqual(session.branches, '["main"]')

    def test_discovery_deduplicates_moved_cursor_transcript_by_newest_copy(self) -> None:
        session_id = "12121212-1212-4121-8121-121212121212"
        older = self.cursor_root / "old-project" / "agent-transcripts" / session_id / f"{session_id}.jsonl"
        newer = self.cursor_root / "new-project" / "agent-transcripts" / session_id / f"{session_id}.jsonl"
        write_jsonl(older, [{"role": "user", "message": {"content": [{"type": "text", "text": "older"}]}}])
        write_jsonl(newer, [{"role": "user", "message": {"content": [{"type": "text", "text": "newer"}]}}])
        newer.touch()

        sessions = sync.discover_sessions(["cursor"], self.home, self.cursor_root, self.codex_root)

        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].source_path, newer)

    def test_codex_scan_uses_response_items_without_event_duplicates(self) -> None:
        session_id = "22222222-2222-4222-8222-222222222222"
        rollout = self.codex_root / "sessions" / "2026" / "09" / "11" / f"rollout-x-{session_id}.jsonl"
        write_jsonl(
            rollout,
            [
                {
                    "timestamp": "2026-09-11T00:00:00Z",
                    "type": "session_meta",
                    "payload": {"id": session_id, "cwd": "/tmp/demo", "timestamp": "2026-09-11T00:00:00Z"},
                },
                {"timestamp": "2026-09-11T00:00:01Z", "type": "event_msg", "payload": {"type": "user_message", "message": "hello"}},
                {
                    "timestamp": "2026-09-11T00:00:01Z",
                    "type": "response_item",
                    "payload": {"type": "message", "role": "user", "content": [
                        {"type": "input_text", "text": "hello"},
                        {"type": "input_image", "image_url": "data:image/png;base64,aGVsbG8="},
                    ]},
                },
                {
                    "timestamp": "2026-09-11T00:00:02Z",
                    "type": "response_item",
                    "payload": {"type": "reasoning", "summary": [{"type": "summary_text", "text": "considering"}]},
                },
                {
                    "timestamp": "2026-09-11T00:00:03Z",
                    "type": "response_item",
                    "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "hi"}]},
                },
                {
                    "timestamp": "2026-09-11T00:00:04Z",
                    "type": "response_item",
                    "payload": {"type": "function_call", "call_id": "call-1", "name": "read", "arguments": "{\"path\":\"a.ts\"}"},
                },
                {
                    "timestamp": "2026-09-11T00:00:05Z",
                    "type": "response_item",
                    "payload": {"type": "function_call_output", "call_id": "call-1", "output": "file body"},
                },
                {
                    "timestamp": "2026-09-11T00:00:06Z",
                    "type": "compacted",
                    "payload": {"message": "earlier conversation summary"},
                },
            ],
        )

        sessions = sync.scan_codex(self.codex_root)

        self.assertEqual(len(sessions), 1)
        self.assertEqual([m.role for m in sessions[0].messages], ["user", "assistant", "assistant", "assistant", "toolResult", "assistant"])
        self.assertEqual(sessions[0].messages[1].kind, "thinking")
        self.assertEqual(sessions[0].messages[3].tool_arguments, {"path": "a.ts"})
        self.assertEqual(sessions[0].messages[4].tool_name, "read")
        self.assertIn("earlier conversation summary", sessions[0].messages[5].text)
        self.assertEqual(sessions[0].messages[0].images[0]["mimeType"], "image/png")

    def test_codex_rollout_filename_keeps_sessions_distinct_when_metadata_id_is_shared(self) -> None:
        shared_thread_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        session_ids = [
            "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        ]
        for session_id in session_ids:
            rollout = self.codex_root / "sessions" / "2026" / "09" / "11" / f"rollout-x-{session_id}.jsonl"
            write_jsonl(
                rollout,
                [
                    {"timestamp": "2026-09-11T00:00:00Z", "type": "session_meta", "payload": {"id": shared_thread_id, "cwd": "/tmp/demo"}},
                    {"timestamp": "2026-09-11T00:00:01Z", "type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": session_id}]}},
                ],
            )

        sessions = sync.scan_codex(self.codex_root)

        self.assertEqual({session.source_id for session in sessions}, set(session_ids))

    def test_codex_archived_session_is_marked_in_provenance(self) -> None:
        session_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        rollout = self.codex_root / "archived_sessions" / f"rollout-x-{session_id}.jsonl"
        write_jsonl(rollout, [
            {"timestamp": "2026-09-11T00:00:00Z", "type": "session_meta", "payload": {"id": session_id, "cwd": "/tmp/demo"}},
            {"timestamp": "2026-09-11T00:00:01Z", "type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "archived"}]}},
        ])
        sessions = sync.scan_codex(self.codex_root)
        self.assertEqual(len(sessions), 1)
        self.assertTrue(sessions[0].archived)
        rows = [json.loads(line) for line in sync.render_omp_session(sessions[0], "target").splitlines()]
        provenance = next(row for row in rows if row.get("customType") == sync.PROVENANCE_TYPE)
        self.assertTrue(provenance["data"]["archived"])

    def test_title_slot_is_exactly_256_bytes(self) -> None:
        line = sync.title_slot("A title", "2026-09-11T00:00:00Z")
        self.assertEqual(len((line + "\n").encode("utf-8")), 256)

    def test_render_uses_valid_omp_attribution(self) -> None:
        session = sync.ImportedSession(
            "cursor", "id", Path("/tmp/source"), "/tmp", "title",
            "2026-09-11T00:00:00Z", "2026-09-11T00:00:00Z", False,
            [
                sync.ImportedMessage("user", "question", "2026-09-11T00:00:00Z"),
                sync.ImportedMessage("assistant", "answer", "2026-09-11T00:00:01Z"),
            ],
            "hash",
        )
        rows = [json.loads(line) for line in sync.render_omp_session(session, "target").splitlines()]
        messages = [row["message"] for row in rows if row.get("type") == "message"]
        self.assertEqual([message["attribution"] for message in messages], ["user", "agent"])
        assistant = messages[1]
        self.assertEqual(assistant["api"], "cursor-agent")
        self.assertEqual(assistant["provider"], "cursor")
        self.assertEqual(assistant["model"], "imported")
        self.assertEqual(assistant["stopReason"], "stop")
        self.assertEqual(assistant["usage"]["totalTokens"], 0)
        self.assertEqual(assistant["usage"]["cost"]["total"], 0)

    @unittest.skipUnless(shutil.which("omp"), "OMP is not installed")
    def test_render_round_trips_through_omp_transcript_pipeline(self) -> None:
        session = sync.ImportedSession(
            "codex", "id", Path("/tmp/source"), str(self.home), "title",
            "2026-09-11T00:00:00Z", "2026-09-11T00:00:00Z", False,
            [
                sync.ImportedMessage("user", "question marker", "2026-09-11T00:00:00Z"),
                sync.ImportedMessage("assistant", "answer marker", "2026-09-11T00:00:01Z"),
            ],
            "hash",
            model="gpt-5.3-codex",
        )
        target = self.home / "session.jsonl"
        target.write_bytes(sync.render_omp_session(session, "target"))
        result = subprocess.run(
            ["omp", "render", str(target), "--plain", "--width", "120"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("question marker", result.stdout)
        self.assertIn("answer marker", result.stdout)
        rows = [json.loads(line) for line in target.read_text().splitlines()]
        assistant = next(row["message"] for row in rows if row.get("type") == "message" and row["message"]["role"] == "assistant")
        self.assertEqual((assistant["provider"], assistant["model"]), ("openai-codex", "gpt-5.3-codex"))

    @unittest.skipUnless(shutil.which("omp"), "OMP is not installed")
    def test_imported_session_lists_and_loads_over_omp_acp(self) -> None:
        cwd = self.home / "project"
        cwd.mkdir()
        target_id = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        session = sync.ImportedSession(
            "codex", "id", Path("/tmp/source"), str(cwd), "ACP imported fixture",
            "2026-09-11T00:00:00Z", "2026-09-11T00:00:00Z", False,
            [sync.ImportedMessage("user", "hello ACP", "2026-09-11T00:00:00Z")], "hash",
        )
        history = self.home / ".katalyst" / "history"
        target = self.omp_root / sync.omp_bucket(str(history), self.home) / f"2026-09-11T00-00-00Z_{target_id}.jsonl"
        target.parent.mkdir(parents=True)
        history.mkdir(parents=True)
        target.write_bytes(sync.render_omp_session(session, target_id, str(history)))
        rows = [json.loads(line) for line in target.read_text().splitlines()]
        self.assertEqual(next(row for row in rows if row.get("type") == "session")["cwd"], str(history))
        process = subprocess.Popen(
            ["omp", "acp"], env={**os.environ, "HOME": str(self.home)},
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )

        def request(request_id: int, method: str, params: dict) -> dict:
            process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}) + "\n")
            process.stdin.flush()
            while True:
                ready, _, _ = select.select([process.stdout, process.stderr], [], [], 10)
                self.assertTrue(ready, f"OMP ACP timed out during {method}")
                for stream in ready:
                    line = stream.readline()
                    if stream is process.stdout:
                        response = json.loads(line)
                        if response.get("id") == request_id:
                            return response

        try:
            request(1, "initialize", {"protocolVersion": 1, "clientCapabilities": {}})
            listed = request(2, "session/list", {"cwd": str(history)})
            self.assertEqual(listed["result"]["sessions"][0]["sessionId"], target_id)
            loaded = request(3, "session/load", {"sessionId": target_id, "cwd": str(history), "mcpServers": []})
            self.assertIn("configOptions", loaded["result"])
        finally:
            process.terminate()
            process.wait(timeout=5)
            process.stdin.close()
            process.stdout.close()
            process.stderr.close()
    def test_owned_legacy_session_gets_safe_history_projection(self) -> None:
        session_id = "45454545-4545-4454-8454-454545454545"
        transcript = self.cursor_root / "legacy-project" / "agent-transcripts" / session_id / f"{session_id}.jsonl"
        write_jsonl(transcript, [{"role": "user", "message": {"content": [{"type": "text", "text": "legacy source"}]}}])
        first = sync.run_sync(["cursor"], self.home, self.cursor_root, self.codex_root, self.omp_root, self.state_path)
        self.assertEqual(first["imported"], 1)
        state = sync.load_state(self.state_path)
        key = f"cursor:{session_id}"
        record = state["sessions"][key]
        canonical_target = Path(record["targetPath"])
        legacy_target = self.omp_root / "-legacy-workspace" / canonical_target.name
        legacy_target.parent.mkdir(parents=True, exist_ok=True)
        canonical_target.replace(legacy_target)
        record["targetPath"] = str(legacy_target)
        rows = legacy_target.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(rows):
            row = json.loads(line)
            if row.get("type") == "session":
                row["cwd"] = "/legacy/workspace"
                rows[index] = json.dumps(row, separators=(",", ":"))
                break
        legacy_target.write_text("\n".join(rows) + "\n", encoding="utf-8")
        record["targetHash"] = sync.file_hash(legacy_target)
        record["ownedByOmp"] = True
        record.pop("runtimeCwd", None)
        sync.atomic_write(self.state_path, (json.dumps(state) + "\n").encode())

        result = sync.run_sync(["cursor"], self.home, self.cursor_root, self.codex_root, self.omp_root, self.state_path)

        history = self.home / ".katalyst" / "history"
        projection = self.omp_root / sync.omp_bucket(str(history), self.home) / legacy_target.name
        self.assertEqual(result["owned_by_omp"], 1)
        self.assertEqual(legacy_target.read_text(encoding="utf-8").count("/legacy/workspace"), 1)
        self.assertTrue(projection.is_file())
        projection_rows = [json.loads(line) for line in projection.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(next(row for row in projection_rows if row.get("type") == "session")["cwd"], str(history))
        updated = sync.load_state(self.state_path)["sessions"][key]
        self.assertEqual(updated["historyProjectionPath"], str(projection))

    def test_sync_is_idempotent_and_does_not_overwrite_continued_session(self) -> None:
        session_id = "33333333-3333-4333-8333-333333333333"
        transcript = (
            self.cursor_root
            / "Users-me-Projects-demo"
            / "agent-transcripts"
            / session_id
            / f"{session_id}.jsonl"
        )
        write_jsonl(transcript, [{"role": "user", "message": {"content": [{"type": "text", "text": "one"}]}}])

        first = sync.run_sync(
            ["cursor"], self.home, self.cursor_root, self.codex_root, self.omp_root, self.state_path
        )
        second = sync.run_sync(
            ["cursor"], self.home, self.cursor_root, self.codex_root, self.omp_root, self.state_path
        )
        self.assertEqual(first["imported"], 1)
        self.assertEqual(second["unchanged"], 1)
        target = next(self.omp_root.rglob("*.jsonl"))
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"type": "custom", "id": "continued", "parentId": None, "timestamp": "2026-09-11T00:00:00Z", "customType": "test"}) + "\n")
        write_jsonl(transcript, [{"role": "user", "message": {"content": [{"type": "text", "text": "changed"}]}}])

        third = sync.run_sync(
            ["cursor"], self.home, self.cursor_root, self.codex_root, self.omp_root, self.state_path
        )

        self.assertEqual(third["owned_by_omp"], 1)
        self.assertIn("continued", target.read_text())

    def test_source_update_reuses_stable_target_without_duplication(self) -> None:
        session_id = "88888888-8888-4888-8888-888888888888"
        transcript = self.cursor_root / "Users-me-demo" / "agent-transcripts" / session_id / f"{session_id}.jsonl"
        write_jsonl(transcript, [{"role": "user", "message": {"content": [{"type": "text", "text": "before"}]}}])
        first = sync.run_sync(["cursor"], self.home, self.cursor_root, self.codex_root, self.omp_root, self.state_path)
        original = next(self.omp_root.rglob("*.jsonl"))
        original_target_id = sync.load_state(self.state_path)["sessions"][f"cursor:{session_id}"]["targetId"]
        write_jsonl(transcript, [{"role": "user", "message": {"content": [{"type": "text", "text": "after"}]}}])

        second = sync.run_sync(["cursor"], self.home, self.cursor_root, self.codex_root, self.omp_root, self.state_path)

        targets = list(self.omp_root.rglob("*.jsonl"))
        self.assertEqual(first["imported"], 1)
        self.assertEqual(second["updated"], 1)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0], original)
        self.assertIn("after", original.read_text())
        self.assertEqual(
            sync.load_state(self.state_path)["sessions"][f"cursor:{session_id}"]["targetId"],
            original_target_id,
        )

    def test_dry_run_writes_nothing(self) -> None:
        session_id = "44444444-4444-4444-8444-444444444444"
        transcript = self.cursor_root / "Users-me-demo" / "agent-transcripts" / session_id / f"{session_id}.jsonl"
        write_jsonl(transcript, [{"role": "user", "message": {"content": [{"type": "text", "text": "hello"}]}}])

        result = sync.run_sync(
            ["cursor"], self.home, self.cursor_root, self.codex_root, self.omp_root, self.state_path, dry_run=True
        )

        self.assertEqual(result["would_import"], 1)
        self.assertFalse(self.omp_root.exists())
        self.assertFalse(self.state_path.exists())

    def test_automatic_sync_respects_onboarding_toggle(self) -> None:
        marker = self.state_path.parent / "auto-sync-disabled"
        marker.parent.mkdir(parents=True)
        marker.write_text("disabled\n")
        result = subprocess.run(
            [sys.executable, str(MODULE_PATH), "sync", "--sources", "cursor,codex", "--all", "--automatic", "--json"],
            env={**os.environ, "HOME": str(self.home)}, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(json.loads(result.stdout)["skipped"], 1)

    def test_state_loss_never_overwrites_existing_revision(self) -> None:
        session_id = "55555555-5555-4555-8555-555555555555"
        transcript = self.cursor_root / "Users-me-demo" / "agent-transcripts" / session_id / f"{session_id}.jsonl"
        write_jsonl(transcript, [{"role": "user", "message": {"content": [{"type": "text", "text": "hello"}]}}])
        first = sync.run_sync(
            ["cursor"], self.home, self.cursor_root, self.codex_root, self.omp_root, self.state_path
        )
        target = next(self.omp_root.rglob("*.jsonl"))
        original = target.read_bytes()
        self.state_path.unlink()
        write_jsonl(transcript, [{"role": "user", "message": {"content": [{"type": "text", "text": "changed"}]}}])

        second = sync.run_sync(
            ["cursor"], self.home, self.cursor_root, self.codex_root, self.omp_root, self.state_path
        )

        self.assertEqual(first["imported"], 1)
        self.assertEqual(second["owned_by_omp"], 1)
        self.assertEqual(len(list(self.omp_root.rglob("*.jsonl"))), 1)
        self.assertEqual(target.read_bytes(), original)

    def test_concurrent_sync_serializes_state_and_target_writes(self) -> None:
        session_id = "66666666-6666-4666-8666-666666666666"
        transcript = self.cursor_root / "Users-me-demo" / "agent-transcripts" / session_id / f"{session_id}.jsonl"
        write_jsonl(transcript, [{"role": "user", "message": {"content": [{"type": "text", "text": "hello"}]}}])
        command = [sys.executable, str(MODULE_PATH), "sync", "--sources", "cursor", "--all", "--json"]
        environment = {**os.environ, "HOME": str(self.home)}
        first = subprocess.Popen(command, env=environment, stdout=subprocess.PIPE, text=True)
        second = subprocess.Popen(command, env=environment, stdout=subprocess.PIPE, text=True)
        first_output, _ = first.communicate(timeout=20)
        second_output, _ = second.communicate(timeout=20)

        self.assertEqual(first.returncode, 0, first_output)
        self.assertEqual(second.returncode, 0, second_output)
        results = [json.loads(first_output), json.loads(second_output)]
        self.assertEqual(sum(result["imported"] for result in results), 1)
        self.assertEqual(sum(result["unchanged"] for result in results), 1)
        self.assertEqual(len(list(self.omp_root.rglob("*.jsonl"))), 1)
        self.assertEqual(len(sync.load_state(self.state_path)["sessions"]), 1)


if __name__ == "__main__":
    unittest.main()
