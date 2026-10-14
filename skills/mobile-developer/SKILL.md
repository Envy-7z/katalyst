---
name: mobile-developer
description: Expert mobile engineering across Flutter, Android native (Kotlin/Gradle), and iOS native (Swift/Xcode). Use when developing, debugging, building, or testing mobile apps, emulators, devices, platform channels, or mobile architecture.
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

## 2. Device & Emulator Management

Quick inspection via `katalyst-mobile` (installed in `~/.local/bin/`):
- List all targets: `katalyst-mobile devices`
- List emulators & simulators: `katalyst-mobile emulators`
- Reverse local backend port to Android: `katalyst-mobile reverse <port>` (e.g. `katalyst-mobile reverse 3000`)
- Clean all mobile build artifacts: `katalyst-mobile clean`

### Native CLI Fallbacks:
- **Android ADB**:
  ```bash
  adb devices -l
  adb reverse tcp:3000 tcp:3000
  adb logcat -v time -s "TAG_NAME:V"
  ```
- **iOS Simctl**:
  ```bash
  xcrun simctl list devices available
  xcrun simctl boot "<device-uuid>"
  open -a Simulator
  ```
- **Flutter**:
  ```bash
  flutter devices
  flutter run -d <device-id>
  flutter run -d chrome --web-port=3000
  ```

## 3. Architecture & Code Conventions

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

## 4. Verification Checklist Before Marking Work Complete

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
