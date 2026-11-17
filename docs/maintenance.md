# 🧰 Maintenance scripts

Run these from the installation folder (normally `/opt/domain-monitor`).

## 📈 Measure Check-all performance

Start **Check all domains** in the dashboard, then immediately run:

```bash
sudo ./scripts/monitor-check-all.sh
```

Optional arguments: number of samples and seconds between them, for example `sudo ./scripts/monitor-check-all.sh 20 10`.

The script is read-only. It shows CPU and memory use, live batch progress, domains per minute, average seconds per domain, the slowest domains, and the real one-process timing for the three slowest domains. Those timing runs skip the expiry lookup and do not save results.

## 🧹 Remove old Docker images

Every update builds a new image, so old images accumulate.

```bash
sudo ./scripts/cleanup-images.sh
```

The script keeps the configured release, the two newest older releases (for rollback), and any image used by a container. It lists what it will remove and asks you to type `CLEANUP` first. It never touches containers, volumes, the database, `.env` or backups.
