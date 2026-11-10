# Domain Monitor changelog

## 0.10.3 - 2026-11-10

### Changed
- Update checks now report the source version, running container version, and latest stable release separately.
- The updater rebuilds and recreates containers when checked-out source and running container versions drift.

### Fixed
- Persisted `DOMAIN_MONITOR_VERSION` in `.env` so Compose no longer falls back to `domain-monitor:latest`.
- Preserved the active host binding and port in `.env` during updates.
- Added post-update verification for the image tag, running version, published binding, database integrity, domain count, and history count.

## 0.10.2 - 2026-11-10

### Added
- Added environment-controlled host binding through `HOST_BIND_IP` and `HOST_PORT`.
- Added a one-time migration path for existing script-managed installations.

### Changed
- The public default remains securely bound to `127.0.0.1:8282`, while local deployments can preserve an explicit LAN address in the untracked `.env` file.

### Fixed
- Normalized source and test permissions and Python import paths so the non-root container user can run the regression suite.
- Normalized source and test permissions so the non-root container user can run the regression suite.
- Enabled Git-managed updates without overwriting deployment-specific network bindings.

## 0.10.1 - 2026-11-10

### Fixed
- Fixed updater backups so SQLite online backups are written directly from the bind-mounted host database.
- Fixed restore ownership handling by using numeric UID/GID syntax without account-name lookup.
- Fixed rollback to stop containers before replacing the SQLite database.

### Security
- Rollback now restores the database atomically through a temporary file before restarting services.

## 0.10.0 - 2026-11-10

### Added
- Added supported `update.sh`, `backup.sh`, and `restore.sh` commands.
- Added stable-release checks, explicit-version updates, regression testing, database verification, and automatic rollback.
- Added upgrading and recovery documentation.

### Changed
- Standardized public installations around a clean Git clone with runtime credentials, database, backups, and local overrides outside tracked source.

### Security
- Updates stop when tracked files contain local modifications.
- Every update creates a consistent SQLite backup and validates integrity and record counts before completion.

## 0.9.4 - 2026-11-10

### Added
- Added `scripts/set-admin-password.sh` for secure administrator password setup, environment backup, container recreation, and in-container password verification.
- Added documentation for administrator password setup and recovery.

### Fixed
- Fixed public deployment guidance so Werkzeug password hashes containing `$` characters are stored inside single quotes in `.env`.
- Added verification against the password hash actually loaded by the running web container.

### Security
- Password input remains hidden and is never written to shell history or application logs.
- The real `.env`, administrator password, generated hash, and session key remain excluded from Git.

## 0.9.3 - 2026-11-10

### Added
- Added the MIT License with copyright attributed to `mx5matt`.
- Added a direct license link and reuse summary to the project README.

### Changed
- Updated the public source version to 0.9.3 for the licensing release.

## 0.9.2 - 2026-11-10

### Added
- Added a visible AI-assisted project disclaimer to the application footer.
- Added clear guidance that the software is provided as-is, may contain errors or security issues, may not be actively maintained, and requires independent validation before operational use.

## 0.9.1 - 2026-11-10

### Fixed
- Replaced the organization-specific dashboard search example with the generic placeholder `example.com or client name`.

### Security
- Removed an organization reference from the production user interface and public-source workflow.

## 0.9.0 - 2026-11-10

### Added
- Added a Settings dropdown for selecting the timezone used by daily scheduling and displayed timestamps.
- Added a curated list of common IANA timezones, including New Zealand, Australia, Asia, Europe, United States, and UTC options.

### Changed
- Changing the timezone now recalculates the next scheduled check for every domain using the selected local time.
- Daylight-saving transitions are handled by the selected timezone rather than being fixed to Pacific/Auckland.

### Security
- Timezone values are restricted to a server-defined allow-list instead of accepting arbitrary user input.

## 0.8.2 - 2026-11-10

### Changed
- Hidden the normal “Scheduler: running” badge to reduce dashboard clutter.
- Scheduler heartbeat monitoring remains active and now displays a prominent warning only when the worker is not reporting.

## 0.8.1 - 2026-11-10

### Changed
- Capitalised per-domain status badge labels: Pass, Warn, Fail, Unknown, Pending and Stale.

## 0.8.0 - 2026-11-10

### Added
- Added dashboard search by domain name or client label.
- Added sorting by severity, domain name, last checked time and next scheduled check.
- Added a visible “Showing X of Y domains” result count.

### Changed
- The default dashboard order is now Failures first.
- Search and sorting work together with SPF, DKIM and DMARC status filters and remain in the page URL across refreshes.

## 0.7.3 - 2026-11-10

### Fixed
- Prevented SPF, DKIM and DMARC summary cards from touching or overlapping at desktop widths.
- Balanced left and right internal spacing while retaining a single-line counter layout.
- Added a one-column responsive layout below 1100 pixels to preserve visible gaps between cards.

## 0.7.2 - 2026-11-10

### Fixed
- Added extra right-side spacing after the Unknown counter so each summary card has a balanced white edge.
- Kept all four status counters on one line at standard desktop widths.

## 0.7.1 - 2026-11-10

### Fixed
- Kept Pass, Warn, Fail and Unknown counters on one line within each SPF, DKIM and DMARC summary card on standard desktop widths.
- Added compact responsive wrapping for narrower screens so status counters remain readable without horizontal page scrolling.

## 0.7.0 - 2026-11-10

### Added
- Added an in-app **Change log** page and navigation button.
- Added clickable SPF, DKIM and DMARC status counters that filter domain cards by Pass, Warn, Fail or Unknown.
- Added a visible active-filter summary and **Clear filter** action.

### Fixed
- Fixed invalid dashboard filter parameters so they safely fall back to the full domain list.
- Fixed the clickable-filter regression test so it checks rendered banner markup rather than matching the CSS class definition.

### Changed
- Adopted semantic versioning for application releases.
- Future application changes must update both the displayed version and this changelog.

## 0.6.0 - 2026-11-10

### Added
- Added SPF, DKIM and DMARC status counter boxes for Pass, Warn, Fail and Unknown.

### Changed
- Stale, pending and missing results are counted as Unknown rather than Pass.

### Fixed
- Fixed feature detection in the status-counter installer so the Bulk add summary variable is not mistaken for installed counters.

## 0.5.0 - 2026-11-10

### Added
- Added the Domain Monitor shield and verified-email favicon in ICO and PNG formats.

## 0.4.0 - 2026-11-10

### Added
- Added **Check all domains** to queue immediate checks for every domain.

### Changed
- Already queued domains are not queued twice.
- Bulk checks leave the fixed daily schedule unchanged.

## 0.3.0 - 2026-11-10

### Added
- Added bulk domain import with optional labels, shared DKIM selectors and a shared minimum DMARC policy.
- Added duplicate skipping and atomic validation for bulk imports.

## 0.2.0 - 2026-11-10

### Added
- Added one shared daily check time for all domains.
- Added Pacific/Auckland timezone support, including NZST and NZDT handling.
- Added a Settings page for the daily schedule.

### Fixed
- Fixed **Check now** so manual checks no longer reset the next scheduled daily check.

### Changed
- New and edited domains receive an immediate check while retaining the shared schedule.
- Missed scheduled checks run once when the worker resumes.

## 0.1.0 - 2026-11-09

### Added
- Initial self-hosted Domain Monitor release.
- Added password-protected dashboard, SQLite persistence and Docker Compose deployment.
- Added SPF, configured-selector DKIM and DMARC DNS health checks.
- Added manual checks, daily checks, result history, stale-result handling and worker health reporting.
- Added green Pass, amber Warn, red Fail and grey Unknown states.

### Security
- Bound the initial web service to localhost for SSH-tunnel access.
- Added CSRF protection, security headers, rate-limited login attempts, non-root containers, dropped capabilities and read-only container filesystems.
