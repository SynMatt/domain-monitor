# Domain Monitor

A self-hosted dashboard for scheduled SPF, DKIM and DMARC DNS health checks.

## AI-assisted project disclaimer

This software was developed with substantial AI assistance. It is provided **as-is**, may contain errors or security issues, and may not be actively maintained.

Review the source code, test it in a non-production environment, protect credentials and backups, and independently validate all results before relying on the software. No warranty or support commitment is provided.

## Features
- Detected DNS host on domain cards, with nameserver evidence in history

- Password-protected web dashboard
- Shared daily check schedule with manual checks that do not shift the schedule
- SPF, configured-selector DKIM and DMARC validation
- Result history and stale-result detection
- Status counters, clickable filters, search and sorting
- Bulk domain import
- Pacific/Auckland timezone support
- Bounded parallel checks with configurable `CHECK_WORKERS` (default 4, range 1-8)
- One checker process per domain, with a configurable container CPU limit (`CONTAINER_CPUS`, default 2)
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

The default listener is `127.0.0.1:8282`. To bind to a specific LAN address without editing tracked files, add these values to `.env`:

```dotenv
HOST_BIND_IP='192.0.2.10'
HOST_PORT='8282'
```

Review `CHANGELOG.md` for release history.

<!-- BEGIN UPDATE COMMANDS -->
## Updating Domain Monitor

Latest documented release: **v0.14.0**

Run these commands through SSH on the application host, not in a separate development checkout. Adjust the directory if your installation uses another path.

### Check for updates

```bash
cd /opt/domain-monitor
sudo ./scripts/update.sh --check
```

### Install the latest stable release

```bash
cd /opt/domain-monitor
sudo ./scripts/update.sh
```

### Install this release explicitly

```bash
cd /opt/domain-monitor
sudo ./scripts/update.sh --version 0.14.0
```

### Verify the deployment

```bash
cd /opt/domain-monitor
sudo ./scripts/update.sh --check
sudo docker compose ps
sudo docker compose exec -T web python -c 'import app; print(app.APP_VERSION)'
sudo docker compose config --images
sudo docker compose port web 8080
```

Source and running versions should agree, both services should be healthy, and the published binding should match your deployment.

### Manual backup

```bash
cd /opt/domain-monitor
sudo ./scripts/backup.sh
```

Updates briefly interrupt service. Keep an off-host backup. Backups contain sensitive configuration and domain data; never publish them.

These instructions assume a Git-managed installation with updater v0.10.5 or later. Older or script-managed installations need a reviewed migration/bootstrap first. Do not force a checkout over local changes. If an update fails, stop and retain its output and backup path before attempting recovery.

Never share full `docker compose config` output: it can expose credentials. Use `docker compose config --quiet` for validation.

See [the upgrade guide](docs/upgrading.md) for more information.
<!-- END UPDATE COMMANDS -->

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

### DNS host detection

Nameservers are collected during checks, not page loads. Provider labels are inferred. Unrecognised providers show compact nameserver-domain hints; lookup failures show Unknown. Existing results show Not checked yet until refreshed. DNS host lookup does not affect email-health status.

Microsoft 365 nameservers under `bdm.microsoftonline.com` display as **Microsoft**. Provider mappings also apply to cached nameserver results without new DNS requests. Provider identity is inferred from nameservers, not from the registrar or email provider.

## DNS provider directory

Open Settings, then Manage DNS providers. Add a nameserver suffix (for example `dns.example.net`) and a friendly provider name. Custom mappings take precedence over built-in mappings and immediately affect cached card labels. Edit names or delete mappings from the same page. Mappings are stored in the SQLite database and included in backups. No page-load DNS requests or external AI lookups are made. Full nameservers remain in Details & history. Suggested suffixes are conservative hostname hints, not verified company identities or registrable-domain calculations.

## Performance and host sizing

Since version 0.14.0, Domain Monitor runs all checks for one domain in a single child process, substantially reducing startup overhead.

The default settings are suitable for most small installations:

```dotenv
CHECK_WORKERS='4'
CONTAINER_CPUS='2'
```

- `CHECK_WORKERS` controls how many domains are checked concurrently.
- `CONTAINER_CPUS` controls the maximum CPU cores available to each container.
- Do not set `CONTAINER_CPUS` higher than the CPU cores available to Docker.
- Start conservatively and increase the values only after measuring a complete Check-all run.

Suggested starting values:

| Host resources | CHECK_WORKERS | CONTAINER_CPUS |
|---|---:|---:|
| 1-2 CPU cores, 2 GB RAM | 2 | 1 |
| 2-4 CPU cores, 4 GB RAM | 4 | 2 |
| 4+ CPU cores, 8 GB RAM | 4 | 4 |

For an existing installation, update the private `.env` file:

```bash
cd /opt/domain-monitor

sudo sed -i \
  '/^CHECK_WORKERS=/d; /^CONTAINER_CPUS=/d' \
  .env

sudo sh -c \
  "printf \"\nCHECK_WORKERS='4'\nCONTAINER_CPUS='4'\n\" >> .env"

sudo chmod 600 .env

sudo docker compose up -d \
  --force-recreate \
  --wait \
  --wait-timeout 180
```

Verify the worker count:

```bash
sudo docker compose exec -T worker python -c \
  'import app; print("Workers:", app.check_workers())'
```

Verify the worker CPU limit:

```bash
WORKER_ID=$(sudo docker compose ps -q worker)

sudo docker inspect \
  --format 'CPU limit: {{.HostConfig.NanoCpus}}' \
  "$WORKER_ID"
```

A four-core limit appears as:

```text
CPU limit: 4000000000
```

In one measured deployment, Domain Monitor processed 164 domains in approximately 1.2 minutes using four workers and a four-core container limit. Results vary depending on the host, DNS response times, configured DKIM selectors, and registry services.

Existing installations preserve their private `.env` during upgrades. If `CONTAINER_CPUS` is absent, Docker Compose uses the default of two cores.
