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
RESOURCE_TUNING='auto'
# Set automatically by the tuner. Example values for a 2-core host:
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

`scripts/tune-resources.sh` sets `CHECK_WORKERS` and `CONTAINER_CPUS` from the CPU cores and memory Docker can see. It runs during setup and on every update.

| Host | `CHECK_WORKERS` | `CONTAINER_CPUS` |
|---|---|---|
| 1 CPU core, or under 3 GB RAM | 2 | Same as cores |
| 2–3 CPU cores | 4 | Same as cores |
| 4+ CPU cores | 4 | 4 |

On Hyper-V virtual machines only CPU cores are used, because Dynamic Memory makes the memory reading unreliable. `CONTAINER_CPUS` is never set higher than the host's cores.

Check or re-apply the settings:

```bash
cd /opt/domain-monitor
sudo ./scripts/tune-resources.sh --dry-run   # show what would change
sudo ./scripts/tune-resources.sh             # apply and recreate containers
```

To use your own values, set `RESOURCE_TUNING='manual'` so the tuner keeps them. Example for a larger host:

```bash
cd /opt/domain-monitor
sudo sed -i '/^CHECK_WORKERS=/d; /^CONTAINER_CPUS=/d; /^RESOURCE_TUNING=/d' .env
printf "CHECK_WORKERS='4'\nCONTAINER_CPUS='4'\nRESOURCE_TUNING='manual'\n" | sudo tee -a .env >/dev/null
sudo chmod 600 .env
sudo docker compose up -d --force-recreate --wait --wait-timeout 180
```

Verify the worker count and CPU limit:

```bash
sudo docker compose exec -T worker python -c 'import app; print("Workers:", app.check_workers())'
sudo docker inspect --format 'CPU limit: {{.HostConfig.NanoCpus}}' "$(sudo docker compose ps -q worker)"
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

Select **Details & history** on a domain card to see:

- **Summary tiles:** overall status, last checked, DNS host and domain expiry.
- **Current status:** the latest SPF, DKIM and DMARC results side by side, with warnings and technical details.
- **History:** one collapsed line per entry showing its date, statuses and what changed since the entry before it, such as *DKIM pass → warn* or *SPF record changed*. Select a line to see the full result.

To keep the database small:

- When a check gives the same result as the one before, that entry is extended instead of adding a new one. It shows *Same result for N checks since …*.
- Full DNS detail is kept for the newest entry only. Older entries show *Summary only* under DNS evidence.
- History is kept for up to 90 days and 1,000 entries per domain.

Check the database size:

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

`CONTAINER_CPUS` in `.env` is higher than the host's CPU cores. Fix it with the tuner, then run the update again:

```bash
cd /opt/domain-monitor
sudo ./scripts/tune-resources.sh
```

### The tuner shows much less memory than the VM has

On Hyper-V with **Dynamic Memory**, Linux only sees the memory currently assigned. The tuner detects Hyper-V and uses CPU cores only, so this does not affect its choices.

### Seeing hidden test output

Tests that deliberately make checks time out or crash have their log lines hidden, so a passing run shows only dots and `OK`. To see them:

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
- README updated for user-visible changes, with its review marker set to the new version
- Candidate Docker build and complete test-suite pass before tagging

Run the full suite from a development checkout with `./scripts/run-tests.sh`. Add a name to run only matching tests, for example `./scripts/run-tests.sh history`.

Release tags use semantic versioning, for example `v0.14.0`.

## 📄 License

Licensed under the MIT License. See [LICENSE](LICENSE).

## External SPF warnings

Domain Monitor follows nested SPF `include:` records. When an included provider contains an ineffective `a` mechanism, the warning identifies the problem as belonging to the included SPF provider.

Example:

```text
External SPF warning: _spf.provider.example.net uses an a mechanism but has no A/AAAA records. This issue is with the included SPF provider.
```

The result remains a warning because the monitored domain's SPF record can still be valid and other mechanisms in the included record can continue to authorize senders.
<!-- README reviewed for release: 0.14.8 -->

<!-- BEGIN UPDATE COMMANDS -->
## Updating Domain Monitor

Latest documented release: **v0.14.8**

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
sudo ./scripts/update.sh --version 0.14.8
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
