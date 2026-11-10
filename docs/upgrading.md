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
