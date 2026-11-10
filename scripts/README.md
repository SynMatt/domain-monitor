# Administrative scripts

| File | Purpose |
|---|---|
| `set-admin-password.sh` | Securely prompts for a new administrator password, backs up `.env`, generates a Werkzeug password hash inside the application image, writes quoted environment values, recreates the containers, and verifies the password against the hash loaded by the running web container. |

## Set or reset the administrator password

Run on the Docker host from any directory:

```bash
sudo ./scripts/set-admin-password.sh
```

For an installation outside `/opt/domain-monitor`, set `DOMAIN_MONITOR_ROOT`:

```bash
sudo DOMAIN_MONITOR_ROOT=/path/to/domain-monitor ./scripts/set-admin-password.sh
```

Password input is hidden. The script requires at least 12 characters and never prints the password or generated hash. A timestamped `.env` backup is retained beside the active environment file.
