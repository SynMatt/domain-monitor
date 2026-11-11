# Domain Monitor changelog
## 0.13.3 - 2026-11-11
### Added
- Added automated recursive and authoritative DNS evidence for SPF, DMARC and configured DKIM selectors.
- Added authoritative consensus, TTL, response-code, resolver and query-time details to domain history.
### Changed
- Manual and scheduled checks now record whether recursive DNS matches the authoritative nameservers.
- DNS disagreement is reported as evidence and does not silently overwrite SPF, DKIM or DMARC health.
### Security
- Authoritative queries are bounded to eight nameservers, use short timeouts, and never run during dashboard page loads.

## 0.13.2 - 2026-11-11

### Added
- Added optional manual domain-expiry dates and source notes for registries that do not publish expiry information.
- Added a bounded `.nz` WHOIS fallback through `whois.irs.net.nz` after unsupported RDAP lookups.

### Changed
- Domain expiry now distinguishes Not checked yet, Not published by registry, Temporary lookup error, and a confirmed expiry date.
- Manual expiry dates take priority over automatic registry results and are preserved in SQLite backups.
- Refreshed README copy/paste update commands for 0.13.2.

### Security
- WHOIS responses are size-limited, time-limited, and parsed only for explicit expiry fields; Updated Date is never treated as expiry.


## 0.13.1 - 2026-11-11

### Fixed
- Check now on the dashboard now returns to the same dashboard view instead of opening the domain details page.
- Dashboard search, filter and sort query parameters are preserved after queuing a check.
- Check now on a domain details page continues to return to that domain.

### Security
- Check-now return paths accept only local application paths and reject external or protocol-relative redirects.

### Changed
- Refreshed README copy/paste update commands for 0.13.1.

## 0.13.0 - 2026-11-11

### Added
- Added cached domain registration expiry checks using RDAP expiration events.
- Added expiry date and days remaining to dashboard cards and domain history.
- Added green, amber and red expiry indicators for over 90 days, 31–90 days, and 30 days or fewer/expired.

### Changed
- Expiry is collected by the isolated checker during domain checks and never during dashboard page loads.
- Expiry lookup failures display Unavailable and do not change SPF, DKIM or DMARC health.
- Refreshed README copy/paste update commands for 0.13.0.

## 0.12.3 - 2026-11-11

### Added
- Added Check now beside Edit settings on each domain details page.

### Changed
- Manual checks from a domain details page return to that same domain page.
- Duplicate Check now requests no longer re-queue the domain or increment its revision while a manual check is already pending.
- Refreshed README copy/paste update commands for 0.12.3.

### Fixed
- Manual Check now preserves the domain's existing daily due time.

## 0.12.2 - 2026-11-11

### Changed
- Refresh now reloads the current page instead of always returning to the dashboard.
- Dashboard Refresh preserves the current search text, SPF/DKIM/DMARC filter and selected sort by keeping the current query string.
- Refreshed README copy/paste update commands for 0.12.2.

## 0.12.1 - 2026-11-11

### Changed
- Changed the default dashboard sort to Domain A-Z.
- Invalid or missing sort values now safely fall back to Domain A-Z; Failures first remains available as an explicit choice.
- Refreshed README copy/paste update commands for 0.12.1.

## 0.11.4 - 2026-11-11

### Added
- Added Settings DNS provider directory with authenticated, CSRF-protected custom mapping creation, editing and deletion.
- Added built-in Crazy Domains and DreamIT Host nameserver mappings and an unrecognised nameserver list.

### Changed
- Custom mappings override built-in labels and apply immediately to cached results and future domains.
- Unknown providers use a compact nameserver-domain fallback; different known providers display Multiple providers.
- Refreshed README copy/paste update commands.

### Security
- Validated suffix boundaries and provider names; stored custom mappings in SQLite state so existing backups preserve them.

## 0.11.3 - 2026-11-11

### Added
- Recognised Microsoft DNS nameservers under bdm.microsoftonline.com.

### Changed
- Applied provider mappings to cached nameservers during display without additional DNS queries or rewriting history.
- Refreshed README update commands for 0.11.3.

## 0.11.2 - 2026-11-11

### Fixed
- Removed oversized fixed-height card rows and unused metadata gaps.
- Replaced DNS scrollbars with a single-line ellipsis; full values remain available in the tooltip and Details & history.
- Restored compact card spacing and bottom-aligned actions without reserving empty label or stale-warning rows.

## 0.11.1 - 2026-11-11

### Changed
- Shortened the displayed label to DNS host on cards and history.
- Aligned domain card sections using consistent metadata rows.

### Fixed
- Long nameserver lists no longer push badges, dates and buttons down relative to neighbouring cards. Nameservers remain accessible in a scrollable DNS field and in history.

## 0.11.0 - 2026-11-11

### Added
- Added copy/paste update, verification and backup instructions to the README.
- Added a README command generator and a regression test matching the documented release to APP_VERSION.
- Added detected DNS host to cards and nameserver evidence to history.
- Added cached NS lookup during manual and scheduled checks, conservative provider matching, and hostname fallback.

### Changed
- DNS host lookup failures do not affect SPF, DKIM or DMARC health.
- Refreshed README update commands for 0.11.0.

## 0.10.5 - 2026-11-11

### Fixed
- Moved the container readability normalization after all Dockerfile `COPY` instructions so regression tests, documentation, and scripts are readable by the non-root container user.
- Added a regression check that the final permission-normalization instruction occurs after the test-suite copy.

## 0.10.4 - 2026-11-11

### Changed
- Update failures now report the exact build, test, startup, or verification step that failed.
- Rollback reports the restored source version, running version, image tag, and published binding.

### Fixed
- Cleared exported image and binding variables before rollback so restored `.env` values control the rollback image and network binding.
- Restored `.env` before rebuilding the previous release, preventing old source from being mislabeled with the failed target version.
- Added explicit rollback verification output for source/container/image consistency.

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
