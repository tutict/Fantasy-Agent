# Production Deployment

## Recommended Topology

- `mysql`, `redis`, `redpanda`, `elasticsearch`, and `backend` from `compose.yaml`
- `gateway` from `compose.prod.yaml` for HTTP and HTTPS ingress
- Flutter clients configured to call the gateway instead of direct backend ports

## Start Commands

```bash
docker compose build
docker compose -f compose.yaml -f compose.prod.yaml up -d
```

## Required Secrets And Assets

- `.env` copied from `.env.example`
- `APP_JWT_SECRET_KEY` replaced with a strong Base64 secret
- `ops/nginx/certs/tls.crt`
- `ops/nginx/certs/tls.key`

## Port Model

- `80`: Nginx HTTP
- `443`: Nginx HTTPS
- `8080`: direct backend access, recommended for internal-only use
- `8081`: direct Vert.x event bus access, recommended for internal-only use

## Reverse Proxy Routes

- `/api/*` -> Spring Boot backend
- `/actuator/*` -> Spring Boot backend
- `/swagger-ui/*` -> Spring Boot backend
- `/v3/api-docs` -> Spring Boot backend
- `/eventbus/*` -> Vert.x proxy with WebSocket upgrade support

## Health Model

- Docker healthchecks gate backend startup on infrastructure readiness
- Backend container exposes Docker `HEALTHCHECK`
- Gateway exposes `/healthz`
- `ops/smoke-test.ps1` validates `/actuator/health` and `/actuator/info`

## Hardening Notes

- Backend now runs as a non-root user inside the container
- Generic server exceptions are no longer echoed back to clients
- Android release signing is externalized and mandatory for release builds
