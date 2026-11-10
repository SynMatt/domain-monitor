# Updating Domain Monitor

## Check for a stable update

```bash
sudo ./scripts/update.sh --check
```

## Install the latest stable release

```bash
sudo ./scripts/update.sh
```

## Install a specific release

```bash
sudo ./scripts/update.sh --version 0.10.0
```

The updater requires a clean Git clone. Runtime files such as `.env`, `data/`, `backups/`, and local Compose overrides remain untracked. Before checkout, the updater creates a consistent SQLite backup, records domain/history counts, builds the candidate, runs every regression test, starts the release, and validates version, database integrity, and record counts. A failed update triggers rollback.

## Backup and restore

```bash
sudo ./scripts/backup.sh
sudo ./scripts/restore.sh /path/to/backup
```

Keep an off-host copy of backups. A local backup does not protect against disk or host failure.

## Preserve a custom network binding

Keep deployment-specific values in the untracked `.env` file:

```dotenv
HOST_BIND_IP='192.0.2.10'
HOST_PORT='8282'
```

The repository default remains `127.0.0.1:8282`. The updater preserves `.env`, so custom bindings survive release checkouts.
## Source and container drift

`update.sh --check` compares three values: the checked-out source version, the running web-container version, and the latest stable Git tag. If the source is current but the container is stale, the updater rebuilds and recreates the services instead of incorrectly reporting that the installation is current.

The updater also stores `DOMAIN_MONITOR_VERSION`, `HOST_BIND_IP`, and `HOST_PORT` in the untracked `.env` file so image selection and network binding persist across releases.
## Rollback verification

If an update fails, the updater now identifies the failed stage, restores the backed-up `.env` and database, clears temporary image/binding environment variables, rebuilds the previous source, and reports the restored source version, running version, image tag, and published binding.

## Maintainer README release checklist

After changing APP_VERSION for each release, run:

```bash
python3 scripts/update-readme-version.py
python3 scripts/update-readme-version.py --check
python3 tests/test_readme_release_commands.py
```

Commit the generated README with the version update and changelog after the full candidate suite passes. The README test rejects a stale explicit-version command. This is a release-time safeguard, not a background process that edits GitHub automatically.
