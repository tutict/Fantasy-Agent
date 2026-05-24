# Backend Deployment Notes

## Profiles

- Default profile: local-oriented defaults for direct development
- `prod` profile: graceful shutdown, health probes, response compression, explicit CORS defaults, and externalized infrastructure settings

Start locally with explicit production settings:

```bash
mvn spring-boot:run "-Dspring-boot.run.profiles=prod"
```

## Important Environment Variables

- `APP_DB_URL`, `APP_DB_USERNAME`, `APP_DB_PASSWORD`
- `APP_REDIS_HOST`, `APP_REDIS_PORT`
- `APP_KAFKA_BOOTSTRAP_SERVERS`
- `SPRING_ELASTICSEARCH_URIS`
- `SPRING_DATA_ELASTICSEARCH_REPOSITORIES_ENABLED`
- `APP_JWT_SECRET_KEY`
- `APP_CORS_ALLOWED_ORIGINS`
- `APP_BOOTSTRAP_ADMIN_ENABLED`, `APP_BOOTSTRAP_ADMIN_USERNAME`, `APP_BOOTSTRAP_ADMIN_PASSWORD`
- `JAVA_OPTS`

## Runtime Container Bootstrap

`RunDocker` is now opt-in. It only starts Redis, Redpanda, and Elasticsearch containers when:

```bash
APP_RUNTIME_BOOTSTRAP_CONTAINERS=true
```

This is suitable for local convenience only. Production deployments should provide managed services or use [compose.yaml](/C:/Users/tutic/IdeaProjects/Final-Assignment-Agent/compose.yaml).

## Health And Observability

- Health: `/actuator/health`
- Info: `/actuator/info`
- Metrics exposure is still configurable through `MANAGEMENT_ENDPOINTS_WEB_EXPOSURE_INCLUDE`
- The container image now includes an internal Docker `HEALTHCHECK`
- The base Compose stack also waits for MySQL, Redis, Redpanda, and Elasticsearch health before starting the backend

## Docker

Build the backend image:

```bash
docker build -t final-assignment-backend:latest ./backend
```

The backend image expects external dependencies to already exist. Flyway migrations bundled in `src/main/resources/db/migration` run automatically on startup.
