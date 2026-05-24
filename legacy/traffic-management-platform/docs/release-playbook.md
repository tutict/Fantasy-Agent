# Release Playbook

## Scope

This playbook covers frontend validation, backend validation, signing prerequisites, and post-deploy smoke checks.

## Release Inputs

- A Git tag or release branch
- Updated `.env` values for the target environment
- Android signing material in `flutter_app/android/key.properties` or equivalent environment variables
- TLS certificate files for `compose.prod.yaml` when the Nginx gateway is enabled

## Validation Steps

### Backend

```bash
cd backend
mvn test
```

### Frontend

```bash
cd flutter_app
flutter pub get
flutter analyze
flutter test test/responsive_viewport_test.dart
```

## Build Steps

### Backend image

```bash
docker compose build backend
```

### Flutter desktop

```bash
flutter build windows --dart-define=API_BASE_URL=https://api.example.com --dart-define=WS_BASE_URL=https://api.example.com/eventbus
```

### Flutter Android

```bash
flutter build apk --release --dart-define=API_BASE_URL=https://api.example.com --dart-define=WS_BASE_URL=https://api.example.com/eventbus
```

## Deployment

### Base stack

```bash
powershell -ExecutionPolicy Bypass -File .\ops\install.ps1
```

### Production stack with gateway

```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d
powershell -ExecutionPolicy Bypass -File .\ops\smoke-test.ps1 -BaseUrl https://api.example.com
```

## Exit Criteria

- Backend health is `UP`
- Backend info endpoint returns the expected version
- Frontend CI passed for the release commit
- Android release signing resolved from secure inputs
- TLS gateway is serving the expected certificate
