# 🛡️ Domain Monitor

A self-hosted dashboard for monitoring domain email security and DNS health.

Domain Monitor checks **SPF**, **DKIM**, **DMARC**, DNS hosting, and domain-expiry information. It runs scheduled checks, keeps history, supports manual checks, and is designed to be operated with Docker Compose.

> [!WARNING]
> This project was developed with substantial AI assistance. Review the source, test changes outside production, protect credentials and backups, and independently validate results before relying on them.

## ✨ Features

- SPF validation, including DNS lookup counts and nested `include:` records
- DKIM checks for configured selectors, including CNAME targets
- DMARC validation, policy checks, warnings, and reporting addresses
- Recursive and authoritative DNS evidence
- Friendly DNS-host labels, custom provider mappings, and DNS-host search
- Domain-expiry checks using RDAP, `.nz` WHOIS fallback, and manual dates
- Scheduled daily checks and per-domain **Check now**
- Protected **Check all domains** batches with progress and cancellation
- Parallel checks, with CPU and worker limits set automatically to suit the host
- Search, filters, sorting, history, backups, and safe update scripts
- Compact history: identical results are grouped, and full DNS detail is kept for the newest check
- Non-root containers, CSRF protection, security headers, and rate-limited login

## 🖥️ What the dashboard shows

Each domain card includes:

- Domain and optional client label
- DNS host
- SPF, DKIM, and DMARC status
- Domain-expiry status when available
- Last-check and next-check times
- **Details & history**, **Edit settings**, and **Check now** actions

Dashboard search matches domain names, client labels, friendly DNS-host names, and cached nameserver hostnames.

## 🧱 How it works

```text
Browser
   │
   ▼
Web container ───── SQLite database
   │                       ▲
   │                       │
   └──────── Worker container
               │
               ├─ SPF / DKIM / DMARC
               ├─ DNS host and authoritative evidence
               └─ RDAP / WHOIS expiry checks
```

- The **web** container serves the dashboard and queues checks.
- The **worker** container performs scheduled and manual checks.
- SQLite stores domains, results, history, settings, batches, and custom provider mappings.
- Runtime secrets and machine-specific settings remain in the private `.env` file.

## 🚀 Quick start

### Requirements

- Linux host with Docker Engine and Docker Compose v2
- At least 2 GB RAM
- A persistent local directory for the SQLite database and backups
- Outbound DNS and HTTPS access

### Install

```bash
git clone https://github.com/SynMatt/domain-monitor.git
cd domain-monitor
cp .env.example .env
chmod 600 .env
```

Set a secure administrator password. The helper also sets CPU and worker limits to suit this host:

```bash
sudo ./scripts/set-admin-password.sh
```

Start Domain Monitor:

```bash
docker compose up -d --build --wait
```

Check container health:

```bash
docker compose ps
curl --fail http://127.0.0.1:8282/health
```

The public default binds to `127.0.0.1:8282`. Set `HOST_BIND_IP` and `HOST_PORT` in `.env` when LAN access or a reverse proxy is required.

## ⚙️ Essential configuration

The private `.env` file controls the deployment. Do not commit it.

```dotenv
HOST_BIND_IP='127.0.0.1'
HOST_PORT='8282'
CHECK_WORKERS='4'
CONTAINER_CPUS='2'
```

| Setting | Purpose | Default |
|---|---|---:|
| `HOST_BIND_IP` | Address exposed by Docker | `127.0.0.1` |
| `HOST_PORT` | Host-side web port | `8282` |
| `CHECK_WORKERS` | Domains checked concurrently | Auto |
| `CONTAINER_CPUS` | Maximum CPU cores available to each container | Auto |
| `RESOURCE_TUNING` | `auto` sets the two values above to suit the host; `manual` keeps your own values | `auto` |

Keep secrets such as `SECRET_KEY` and `ADMIN_PASSWORD_HASH` only in `.env` or an approved secret-management system.

## ⚡ Performance and host sizing

Since version `0.14.0`, all checks for one domain run in a single child process. This significantly reduces application startup overhead.

`scripts/tune-resources.sh` picks these values from the CPU cores and memory Docker can see. On Hyper-V virtual machines it uses CPU cores only, because Dynamic Memory makes the memory reading change from minute to minute:

| Host resources | `CHECK_WORKERS` | `CONTAINER_CPUS` |
|---|---:|---:|
| 1 CPU core, or under 3 GB RAM | 2 | Same as cores |
| 2–3 CPU cores, 3 GB+ RAM | 4 | Same as cores |
| 4+ CPU cores, 3 GB+ RAM | 4 | 4 |

The tuner runs during setup (`set-admin-password.sh`) and on every update. To check or re-apply it at any time:

```bash
cd /opt/domain-monitor
sudo ./scripts/tune-resources.sh --dry-run   # show what would change
sudo ./scripts/tune-resources.sh             # apply and recreate containers
```

`CONTAINER_CPUS` is never left higher than the host's cores, because Docker refuses to start containers when it is.

To use your own values, also set `RESOURCE_TUNING='manual'` so the tuner keeps them. Example for a larger host:

```bash
cd /opt/domain-monitor

sudo sed -i '/^CHECK_WORKERS=/d; /^CONTAINER_CPUS=/d' .env
sudo sh -c "printf \"\nCHECK_WORKERS='4'\nCONTAINER_CPUS='4'\n\" >> .env"
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

Verify the CPU limit:

```bash
WORKER_ID=$(sudo docker compose ps -q worker)

sudo docker inspect \
  --format 'CPU limit: {{.HostConfig.NanoCpus}}' \
  "$WORKER_ID"
```

A four-core limit appears as `4000000000` nanocpus.

In one measured deployment, Domain Monitor processed 164 domains in approximately 1.2 minutes with four workers and a four-core container limit. Results vary with host performance, DNS response times, DKIM selectors, and registry services.

## 🔄 Updating

Check for a newer stable release:

```bash
cd /opt/domain-monitor
sudo ./scripts/update.sh --check
```

Install the latest stable release:

```bash
sudo ./scripts/update.sh
```

Install a specific release:

```bash
sudo ./scripts/update.sh --version X.Y.Z
```

Replace `X.Y.Z` with a version from the [changelog](CHANGELOG.md). The commands at the end of this README always show the current release.

The updater creates a verified backup, builds the selected release, runs tests, recreates the containers, and verifies the running version, image, binding, and database. If validation fails, it attempts an automatic rollback.

## 💾 Backups and restore

Create a manual backup:

```bash
cd /opt/domain-monitor
sudo ./scripts/backup.sh
```

Backups include the SQLite database and a manifest containing the application version, integrity result, domain count, and history count.

Restore only during an approved maintenance window:

```bash
sudo ./scripts/restore.sh \
  /opt/domain-monitor/backups/BACKUP-DIRECTORY
```

Keep a separate off-host copy of important backups. A local backup does not protect against VM, disk, or host failure.

## 🗂️ History and database size

Every check is saved to the domain's history, which is shown under **Details & history**. That page shows a summary (overall status, last checked, DNS host and expiry), the current SPF, DKIM and DMARC results side by side, and a collapsed history list. Each history entry shows its date, statuses and what changed since the entry before it, such as *DKIM pass → warn* or *SPF record changed*; select it to see full details.

- **Identical results are grouped.** When a check gives the same result as the one before, the existing entry is extended instead of adding a new one. It shows as *Same result for N checks since …*. Timing, trigger and cache details are ignored when comparing.
- **Full DNS detail is kept for the newest entry only.** Older entries keep statuses, messages, warnings and records, and show *Summary only* under DNS evidence.
- **Limits:** up to 90 days and 1,000 entries per domain.

Version 0.14.2 slimmed existing history once and reclaimed the space, so the database is much smaller after upgrading from an earlier release. No entries are deleted. To check the size:

```bash
cd /opt/domain-monitor
sudo docker compose exec -T web ls -lh /data/monitor.sqlite3
```

## 🌐 DNS provider directory

Open **Settings → Manage DNS providers** to add, edit, or delete friendly provider mappings.

Example:

| Nameserver suffix | Display name |
|---|---|
| `dns.example.net` | `Example DNS` |

Custom mappings apply to cached results and future domains. Full nameservers remain available under **Details & history**.

## 📆 Domain expiry

Domain Monitor uses:

1. RDAP when the registry publishes an expiration event
2. Official `.nz` WHOIS fallback for `.nz` domains
3. Optional manual expiry dates from a registrar portal

Some registries, including `.nz`, may not publish expiry dates. Domain Monitor shows **Not published by registry** rather than guessing. Manual dates can be entered under **Edit settings**.

## 🔍 Troubleshooting

### Containers are not healthy

```bash
cd /opt/domain-monitor
sudo docker compose ps
sudo docker compose logs --tail=100 web worker
```

### A check appears stale

- Click **Check now** once.
- Wait for **Queued → Checking → Updated just now**.
- Open **Details & history** to inspect the latest saved result and DNS evidence.

### DNS results differ from another checker

Domain Monitor records the recursive answer and authoritative DNS evidence. Compare the returned records, TTLs, response codes, and nameservers. Different public resolvers may temporarily show different cached views.

### Update fails with "range of CPUs is from 0.01 to N"

`CONTAINER_CPUS` in `.env` is higher than the number of CPU cores the host has, so Docker refuses to start the containers. Let the tuner fix it, then run the update again:

```bash
cd /opt/domain-monitor
sudo ./scripts/tune-resources.sh
```

From 0.14.3 the updater does this automatically before building.

### The tuner shows much less memory than the VM has

On Hyper-V with **Dynamic Memory**, Linux only sees the memory currently assigned, which goes up and down. Since 0.14.4 the tuner detects Hyper-V and decides from CPU cores only. If you want the reading to be stable as well, turn off Dynamic Memory in the VM's settings and give it a fixed amount.

### Test output during updates

Some tests deliberately make checks time out or crash to prove they are handled. Their log lines are hidden, so a passing update shows only dots and `OK`. To see them when investigating a failure:

```bash
cd /opt/domain-monitor-github
DM_TEST_LOGS=1 ./scripts/run-tests.sh
```

### Worker health

```bash
sudo docker compose exec -T worker python app.py worker-health
```

### Database integrity

```bash
sudo docker compose exec -T web python - <<'PY'
import sqlite3
with sqlite3.connect('/data/monitor.sqlite3') as database:
    print(database.execute('PRAGMA integrity_check').fetchone()[0])
PY
```

## 🔐 Security notes

- Keep `.env`, backups, and the SQLite database out of Git.
- Do not expose the service directly to the internet without HTTPS, access controls, and an appropriate reverse proxy.
- Containers run as a non-root user with dropped capabilities and read-only filesystems where practical.
- Treat DNS health as configuration evidence, not proof that every message is signed or aligned.
- Review third-party dependencies and release changes before production deployment.

## 🧪 Development and releases

Use a separate development checkout. Every application change must include:

- Version update
- Changelog entry using **Added**, **Changed**, **Fixed**, **Removed**, or **Security** as appropriate
- Regression tests
- README updated for every user-visible change: features, settings, scripts and troubleshooting. Then set the review marker at the end of this file to the new version. A test fails the build if the marker or a changelog README line is missing.
- Candidate Docker build and complete test-suite pass before tagging

Run the full suite from a development checkout with `./scripts/run-tests.sh`. Add a name to run only matching tests, for example `./scripts/run-tests.sh history`.

Release tags use semantic versioning, for example `v0.14.0`.

## 📄 License

Licensed under the MIT License. See [LICENSE](LICENSE).

<!-- README reviewed for release: 0.14.6 -->

<!-- BEGIN UPDATE COMMANDS -->
## Updating Domain Monitor

Latest documented release: **v0.14.6**

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
sudo ./scripts/update.sh --version 0.14.6
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
