# Operations Runbook

## Installation

```bash
powershell -ExecutionPolicy Bypass -File .\ops\install.ps1
```

This validates `.env`, validates Compose, starts the stack, and runs a smoke test.

## Upgrade

```bash
powershell -ExecutionPolicy Bypass -File .\ops\upgrade.ps1
```

This rebuilds the backend image, restarts the stack, and runs a smoke test.

## Smoke Test

```bash
powershell -ExecutionPolicy Bypass -File .\ops\smoke-test.ps1
```

You can target a gateway URL directly:

```bash
powershell -ExecutionPolicy Bypass -File .\ops\smoke-test.ps1 -BaseUrl https://api.example.com
```

## Backup

```bash
powershell -ExecutionPolicy Bypass -File .\ops\backup-db.ps1
```

## Restore

```bash
powershell -ExecutionPolicy Bypass -File .\ops\restore-db.ps1 -BackupFile .\backups\traffic-YYYYMMDD-HHMMSS.sql -Force
```

## Rollback Guidance

1. Stop traffic at the gateway or maintenance window.
2. Restore the most recent known-good database dump if the schema or data changed incompatibly.
3. Redeploy the previously validated application revision.
4. Run `ops/smoke-test.ps1` against the rollback target.

## Remaining Manual Operations

- Redis, Redpanda, and Elasticsearch data are still stateful and need platform-level backup policies outside the provided PowerShell scripts.
- TLS certificate rotation is still an operator responsibility.
