# Domain Monitor

A self-hosted dashboard for scheduled SPF, DKIM and DMARC DNS health checks.

## AI-assisted project disclaimer

This software was developed with substantial AI assistance. It is provided **as-is**, may contain errors or security issues, and may not be actively maintained.

Review the source code, test it in a non-production environment, protect credentials and backups, and independently validate all results before relying on the software. No warranty or support commitment is provided.

## Features

- Password-protected web dashboard
- Shared daily check schedule with manual checks that do not shift the schedule
- SPF, configured-selector DKIM and DMARC validation
- Result history and stale-result detection
- Status counters, clickable filters, search and sorting
- Bulk domain import
- Pacific/Auckland timezone support
- Docker Compose deployment
- In-app changelog

## Security defaults

The example Compose file binds the web interface to `127.0.0.1:8282`. Use an SSH tunnel or an HTTPS reverse proxy. Do not expose the application directly to the internet over HTTP.

Runtime credentials, the SQLite database, backups and domain lists are deliberately excluded from this repository.

## Quick start

1. Copy `.env.example` to `.env`. Keep both values inside single quotes because Werkzeug password hashes contain `$` characters that Docker Compose can otherwise interpret.
2. Generate a random `SECRET_KEY`, for example with `openssl rand -hex 32`.
3. Build the image with `docker compose build`.
4. Set the administrator password with `sudo ./scripts/set-admin-password.sh`. The script generates the hash inside the built image and verifies the value loaded by the web container.
5. Create the persistent data directory with ownership for container UID/GID `10001`.
6. Run the test suite from the built image.
7. Start the services with `docker compose up -d --wait`.

See [`scripts/README.md`](scripts/README.md) for password-reset and verification details.

Review `CHANGELOG.md` for release history.

## Updating

Check for and install stable releases with:

```bash
sudo ./scripts/update.sh --check
sudo ./scripts/update.sh
```

See [`docs/upgrading.md`](docs/upgrading.md) for explicit-version updates, backup, restore, verification, and rollback behaviour.

## Scope

This application checks public DNS configuration. Passing DNS checks does not prove that outbound messages are being signed or that real messages achieve DMARC alignment.


## Repository structure

### Root files

| Path | Purpose |
|---|---|
| `.env.example` | Safe placeholder environment variables for the Flask session secret and administrator password hash. Copy to `.env` locally and replace every placeholder. |
| `.gitignore` | Excludes runtime secrets, SQLite databases, backups, logs, caches, IDE settings, and other local-only files from Git. |
| `CHANGELOG.md` | Versioned release history using Added, Changed, Fixed, Removed, and Security categories. |
| `Dockerfile` | Builds the non-root Python image used by both the web service and scheduled worker. |
| `README.md` | Project overview, security defaults, quick-start guidance, and repository map. |
| `SECURITY.md` | Private vulnerability-reporting guidance and rules for keeping production information out of reports. |
| `app.py` | Main Flask application, authentication, SQLite schema, DNS validators, scheduling logic, worker loop, filters, search, and API health endpoint. |
| `compose.yaml` | Runs the web and worker containers with persistent storage, health checks, resource limits, dropped capabilities, and a localhost-only example port binding. |
| `requirements.txt` | Pinned Python runtime dependencies used to build reproducible container images. |

### Subfolders

| Directory | Purpose |
|---|---|
| [`scripts/`](scripts/README.md) | Administrative helpers for secure password setup and verification. |
| [`static/`](static/README.md) | Browser icon assets served by Flask. |
| [`templates/`](templates/README.md) | Jinja templates for every browser page and shared layout. |
| [`tests/`](tests/README.md) | Regression tests covering security, validation, scheduling, dashboard behaviour, and release metadata. |

## Release process

Every release must update `APP_VERSION`, the displayed version, `CHANGELOG.md`, the Docker image tag used for deployment, and a matching annotated Git tag. Application changes require regression tests before deployment. Public pushes must pass the privacy scan and must never contain `.env`, databases, backups, customer domains, internal hostnames, private IP addresses, or production credentials.

## License

Domain Monitor is released under the [MIT License](LICENSE). The license permits use, copying, modification, distribution, sublicensing, and sale, subject to retaining the copyright and permission notice. The software is provided as-is without warranty.
