# Deployment Notes

## Production Docker Compose

Use the production env file explicitly whenever running the production Compose file:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml config
docker compose --env-file .env.production -f docker-compose.prod.yml up --build
```

Why this matters:

- `--env-file .env.production` lets Docker Compose resolve placeholders like `${POSTGRES_PASSWORD}`.
- `env_file: .env.production` passes variables into Django and Celery containers.
- Database containers only receive the specific variables they need through their `environment` sections.

