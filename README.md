# Domain Monitor

A self-hosted dashboard for scheduled SPF, DKIM and DMARC DNS health checks.

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

1. Copy `.env.example` to `.env`.
2. Generate a random `SECRET_KEY` and a Werkzeug password hash.
3. Create the persistent data directory with ownership for container UID/GID `10001`.
4. Run `docker compose build`.
5. Run the test suite from the built image.
6. Run `docker compose up -d --wait`.

Review `CHANGELOG.md` for release history.

## Scope

This application checks public DNS configuration. Passing DNS checks does not prove that outbound messages are being signed or that real messages achieve DMARC alignment.

## License

No open-source license has been selected yet. Until a license is added, copyright law reserves reuse and redistribution rights.
