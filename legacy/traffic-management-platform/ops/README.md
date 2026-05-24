# Operations

`ops/install.ps1`

- Validates `.env`
- Validates `compose.yaml`
- Pulls images, builds backend image, starts the stack
- Runs `ops/smoke-test.ps1` unless `-SkipSmokeTest` is passed

`ops/upgrade.ps1`

- Revalidates Compose deployment
- Pulls images, rebuilds backend image, rolls the stack forward
- Runs `ops/smoke-test.ps1` unless `-SkipSmokeTest` is passed

`ops/smoke-test.ps1`

- Waits for `/actuator/health` to report `UP`
- Verifies `/actuator/info`
- Defaults to `SERVER_PORT` from `.env`, but can target any `-BaseUrl`

`ops/backup-db.ps1`

- Creates a MySQL logical backup inside `APP_OPERATIONS_BACKUP_DIRECTORY`
- Output file pattern: `traffic-YYYYMMDD-HHMMSS.sql`

`ops/restore-db.ps1 -BackupFile <path> -Force`

- Restores a SQL dump back into the MySQL service
- Requires explicit `-Force` because it overwrites live database state

`compose.prod.yaml`

- Adds an Nginx reverse proxy with HTTP and HTTPS listeners
- Requires TLS files at `ops/nginx/certs/tls.crt` and `ops/nginx/certs/tls.key`
