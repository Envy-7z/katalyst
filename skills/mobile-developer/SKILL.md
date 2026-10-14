---
name: mobile-developer
description: Mobile engineering across Flutter, Android native (Kotlin/Compose/Gradle), and iOS native (Swift/SwiftUI/simctl). Use when developing, debugging, building, or testing mobile apps, emulators, devices, platform channels, Maestro UI flows, or mobile architecture.
---

# Mobile Developer (Flutter, Android & iOS Engineering)

Guidelines, invariants, and commands for autonomous mobile development.

## 1. Core Workflow & Anti-Crash Invariants

- **Zero-Leak Security Guard**: NEVER stage, commit, or echo private mobile credentials:
  - Keystores: `*.jks`, `*.keystore`, `key.properties`
  - Firebase & Services: `google-services.json`, `GoogleService-Info.plist`
  - Apple Signing: `*.p8`, `*.p12`, `*.mobileprovision`, `embedded.provisionprofile`
- **Gradle Daemon Hygiene**: Avoid orphaned Gradle processes. Run Gradle with `--daemon` locally, but use `--no-daemon` in bounded automated scripts when needed. Check lock contention with `./gradlew --status`.
- **Flutter Build Cache**: Before diagnosing unexplained widget or platform channel build errors, run `flutter clean && flutter pub get` to rule out stale `.dart_tool` cache.

## 2. Device, Emulator & Port Automation (`katalyst-mobile`)

Use the bundled `katalyst-mobile` CLI in `~/.local/bin/`:
- **Detect all targets**: `katalyst-mobile devices`
- **List emulators & simulators**: `katalyst-mobile emulators`
- **Launch emulator/simulator**: `katalyst-mobile boot <target>`
- **Automatic Port Reversal**: `katalyst-mobile reverse 3000 8080 5432`
- **PID-Scoped Logcat**: `katalyst-mobile logcat com.example.app`
- **Fast Build Clean**: `katalyst-mobile clean`
- **Hot-Reload Machine Daemon**: `katalyst-mobile flutter-run`

## 3. Autonomous Mobile UI Testing with Maestro MCP

When validating UI flows on real emulators or simulators:
1. Ensure Maestro CLI is available (`katalyst-mobile maestro-setup`).
2. Maestro MCP allows coding agents to:
   - Read live screen hierarchy (`inspectViewHierarchy`).
   - Interact like a user: `tapOn`, `inputText`, `scrollUntilVisible`, `back`.
   - Assert visible text and view states.
3. Save repeatable test journeys into `.maestro/<feature>.yaml` so they run in CI deterministically.

## 4. Architecture & Code Conventions

### Flutter (Dart):
- **State Management**: Prefer declarative patterns (BLoC/Cubit, Riverpod, or ValueNotifier). Separate UI presentation from business logic controllers.
- **Platform Channels**: Use strongly typed MethodChannel contracts:
  - Prefix channel names with domain (e.g. `com.app.channels/payment`).
  - Always handle `PlatformException` and `MissingPluginException`.
- **Responsive Layout**: Adapt to tablet, foldables, and phone viewports using `LayoutBuilder` and `MediaQuery.sizeOf(context)`. Test tap targets (minimum 48x48 dp).

### Android Native (Kotlin):
- **UI**: Jetpack Compose with unidirectional data flow (UDF). State hoisted to `ViewModel` exposing `StateFlow<UiState>`.
- **Concurrency**: Kotlin Coroutines with `viewModelScope` and `Dispatchers.IO` for disk/network I/O.
- **Gradle Configuration**: Place dependencies in `libs.versions.toml` (version catalogs). Avoid deprecated `compile` or broad wildcard dependencies.

### iOS Native (Swift):
- **UI**: SwiftUI with `@Observable` (or `ObservableObject` / `@StateObject` on earlier iOS targets).
- **Dependency Management**: Swift Package Manager (SPM) preferred over CocoaPods.
- **Concurrency**: Swift modern async/await with `@MainActor` isolation for UI state changes.

## 5. Verification Checklist Before Marking Work Complete

1. **Static Analysis & Lint**:
   - Flutter: `flutter analyze`
   - Android: `./gradlew lint` or `./gradlew check`
   - iOS: `swiftlint` (if configured)
2. **Unit & Widget Tests**:
   - Flutter: `flutter test`
   - Android: `./gradlew testDebugUnitTest`
   - iOS: `xcodebuild test -workspace App.xcworkspace -scheme App -destination 'platform=iOS Simulator,name=iPhone 16'`
3. **Packaging Sanity**:
   - Android debug build: `./gradlew assembleDebug`
   - Flutter APK build: `flutter build apk --debug`
