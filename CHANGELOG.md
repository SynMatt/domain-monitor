# Domain Monitor changelog

## 1.2.1 - 2026-11-19

### Changed
- Saving a domain's settings now returns to that domain's details page instead of the dashboard. The confirmation message and the queued check are unchanged. Adding domains still returns to the dashboard.
- Reviewed the README for this release; no wording changes were needed.

## 1.2.0 - 2026-11-19

### Added
- Added per-domain approved SPF and DMARC record sections with an optional approval reason. Matching warnings remain visible for audit but no longer affect the effective status.
- Added plain-language **What is wrong and how to fix it** details for supported SPF and DMARC warnings, including the exact record section that can be reviewed or approved.

### Changed
- Domain details now show a blue **Manually approved exception** notice directly below the normal result message, plus the original warning and matched DNS fragment.
- Approved exceptions are included in configuration-at-check-time and history fingerprints. Changing an approval or its matching DNS record creates a distinct result rather than rewriting history.
- Updated and reviewed the README for approved configuration exceptions.

### Security
- Only warning results can be approved. Fail and Unknown results always remain Fail or Unknown. Approved fragments are limited, length-checked, and matched only against the current SPF or DMARC record.

## 1.1.0 - 2026-11-18

### Added
- Add domain now accepts one domain or many, one per line. A line can be `domain` or `domain,client label`; the Label field is used for lines without their own label.
- When DKIM selectors are left blank, new domains are saved with `selector1` and `selector2`, so Edit settings shows exactly what is checked.

### Changed
- Replaced the separate Bulk add page with Add domain. One domain or many use the same workflow: every line is checked first, nothing is saved if any line is invalid, existing domains are skipped unchanged, and the shared daily schedule does not move. The old `/bulk-add` address redirects to Add domain.
- Reordered the top navigation: Dashboard, Add domain, Settings and Change log, then Refresh, Check all domains and Log out. The current page is marked.
- A manual expiry date can only be set when adding a single domain.
- Updated the README to describe the combined Add domain form and reviewed it for this release.
- Rewrote the bulk-import tests for the combined form.

### Security
- Add domain rejects oversized pasted text on the server as well as in the browser.

## 1.0.0 - 2026-11-18

### Added
- Added a Versioning section to the README that defines when the major, minor and patch numbers change.
- Added a test that fails the build when the newest changelog entry breaks those rules, for example an entry with an Added section that only raises the patch number.

### Changed
- First stable release. From this version, a change that can break existing data, settings or the update procedure is made only in a major release.
- Reworded two old changelog lines and a test so the previous GitHub account name no longer appears in the repository.
- Reviewed the README for this release and added the Versioning section.

### Security
- Widened the no-real-data test to also reject the previous GitHub account name.

## 0.15.2 - 2026-11-18

### Security
- Removed the last real DNS provider name from a test fixture. Tests now use reserved example names only.

### Changed
- Widened the no-real-data test to also reject that provider name.
- Reviewed the README for this release; no wording changes were needed.

## 0.15.1 - 2026-11-18

### Security
- Removed real hostnames from the README example and the test fixtures. Documentation and tests now use reserved example domains only.

### Added
- Added a test that fails the build if documentation, tests or scripts contain known real customer or provider names.

### Changed
- Updated the README example for external SPF warnings to use a reserved example domain.
- Release commits now use the GitHub no-reply email address.

## 0.15.0 - 2026-11-18

### Added
- Added actionable warning categories in message text: Action required, Action recommended, Recommendation, External provider, and Temporary lookup issue.
- Added regression fixtures from the 166-domain warning audit covering direct and included SPF records, obsolete DMARC tags, subdomain policy, reporting guidance, weak DKIM keys, and missing selectors.

### Changed
- Expanded 1024-bit DKIM warnings with a 2048-bit rotation recommendation and clarified that existing signing may still work.
- Missing DKIM selectors now instruct administrators to confirm whether the selector is active, remove stale monitor configuration, or repair DNS.
- Obsolete DMARC pct, ri, and rf tags are presented as low-priority cleanup recommendations.
- DMARC sp=none, missing rua, and excess rua destinations now explain impact and the appropriate review action.
- Oversized SPF records owned by included providers are identified as external-provider recommendations.
- Updated the README with an Actionable warning categories section and reviewed it for this release.

### Fixed
- Direct-domain SPF warnings are no longer mislabelled as external-provider issues. External ownership now requires a different hostname found in the parsed SPF include chain.

## 0.14.9 - 2026-11-18

### Changed
- Rebuilt and reviewed the README so each operational topic is documented once and current repository references use `SynMatt/domain-monitor`.
- Changed the generated release block to contain current-version commands without repeating the Updating or Backups sections.

### Fixed
- Restored required resource-tuning and domain-details guidance while removing broken Markdown, duplicated instructions, and stale current-document repository references.

## 0.14.8 - 2026-11-18

### Changed
- External SPF warnings now clearly identify problems inherited from an included SPF provider. When an included record uses an `a` mechanism but has no A/AAAA records, Domain Monitor identifies the issue as belonging to the included SPF provider.
- Updated the README with the new external SPF warning behaviour and reviewed it for this release.

## 0.14.7 - 2026-11-17
### Fixed
- README: the manual example for a larger host now sets `RESOURCE_TUNING='manual'`. Without it the tuner replaced the values on the next update.
- README: the configuration example now shows `RESOURCE_TUNING='auto'` and labels `CHECK_WORKERS` and `CONTAINER_CPUS` as set automatically, instead of presenting them as fixed values.
### Changed
- README: rewrote the History section to describe the 0.14.6 details page (summary tiles, side-by-side results and the change list).
- README: shortened the performance and troubleshooting sections and removed release-by-release notes, which belong in the changelog.
## 0.14.6 - 2026-11-17
### Changed
- Redesigned the domain details page. The top shows Overall status, Last checked, DNS host and Current domain expiry as tiles, with Edit settings and Check now beside the domain name.
- Current SPF, DKIM and DMARC results are shown once, side by side, with a coloured edge for their status. Warnings are listed under each result.
- History is a compact list of collapsed entries. Each shows the date, overall and per-check status, the trigger, grouped check count, and what changed since the entry before it. Select an entry for its full details.
- Nameservers now appear under DNS host instead of under Domain expiry.
- Updated the README History section and the templates README to describe the new details page.
### Fixed
- The details page no longer starts the subtitle with a stray separator when a domain has no client label.
## 0.14.5 - 2026-11-17
### Fixed
- The README's Updating section showed `--version 0.14.0` as the example release. Hand-written examples now use `X.Y.Z` and point to the changelog; only the generated commands at the end of the README show the current version.
### Added
- Added a test that fails the build if a real version number appears in a README update example outside the generated block, so examples cannot go stale again.
## 0.14.4 - 2026-11-17
### Changed
- On Hyper-V virtual machines the resource tuner decides from CPU cores only. Dynamic Memory made the memory reading change between runs, which could switch `CHECK_WORKERS` between 2 and 4.
- Expected log lines from tests that deliberately make checks time out or crash are hidden, so a passing build or update shows only dots and OK. `DM_TEST_LOGS=1` shows them.
- Updated the README for 0.14.2 to 0.14.4: new History and database size section, automatic CPU and worker tuning in Features, and troubleshooting for the CPU-range update error, Hyper-V memory readings and test output.
### Added
- Added a README review marker and a test that fails the build unless each release updates it and includes a changelog README line, so the README cannot fall behind again.
- Added a test that every user-facing script is documented in the README or the docs folder.
## 0.14.3 - 2026-11-17
### Added
- Added `scripts/tune-resources.sh`, which sets `CONTAINER_CPUS` and `CHECK_WORKERS` in `.env` to suit the host's CPU cores and memory. It shows old and new values, keeps a `.env.backup-tune-*` copy, and supports `--dry-run`.
- Added `RESOURCE_TUNING` to `.env`: `auto` (default) follows the host; `manual` keeps your own values.
### Changed
- New setups are tuned automatically: `set-admin-password.sh` runs the tuner before any container starts.
- Every update runs the tuner after checking out the release, so moving a VM to different hardware is picked up on the next update.
### Fixed
- Updates no longer fail with "range of CPUs is from 0.01 to N" when `CONTAINER_CPUS` is higher than the host's cores; it is lowered to fit, even in manual mode.
- `set-admin-password.sh` no longer removes every other `.env` setting (network binding, image version, CPU and worker limits) when it saves the new password.
## 0.14.2 - 2026-11-17
### Changed
- History keeps full DNS diagnostics only on each domain's newest entry. Older entries keep statuses, messages, warnings and records, without the expanded SPF include tree or raw resolver timings.
- Consecutive checks with the same result now extend one history entry, shown as Same result for N checks, instead of adding a row every time. Timing, trigger and cache details are ignored when comparing.
- Existing history is compacted once when the worker starts, then the database is vacuumed to reclaim space. No history entries are deleted.
- The test suite runs in one container and one process. Shared test fixtures no longer re-run the core tests in every file.
- The version shown in the page header now comes from APP_VERSION, and tests no longer hard-code the release number.
### Added
- Added `scripts/run-tests.sh` to build a candidate image and run the full suite once, with an optional test-name filter.
- DNS evidence now says when a nameserver has no IPv4 or IPv6 address instead of leaving the error blank.
### Fixed
- Removed unused imports reported by pyflakes.
- The expiry lookup User-Agent no longer reports an old version.
### Security
- Updated Flask to 3.1.3 (PYSEC-2026-2151).
- RDAP expiry lookups refuse any URL that is not HTTPS.
- Marked the reviewed subprocess, SQL placeholder and sort-order patterns so security scans show only new findings.
## 0.14.1 - 2026-11-17
### Added
- Added `scripts/monitor-check-all.sh`, a read-only Check-all monitor showing live progress, CPU and memory use, domains per minute, seconds per domain and the slowest domains. Slow-domain timings use the real one-process check path.
- Added `scripts/cleanup-images.sh` to remove old Docker image tags after a preview and confirmation, keeping the configured release, the two newest older releases and any image used by a container.
- Added `docs/maintenance.md`.
### Fixed
- The monitor's live progress line no longer fails with a Python quoting error.
- The monitor no longer times the six checks as separate processes, which overstated per-domain time after 0.14.0.
## 0.14.0 - 2026-11-17
### Changed
- Each domain is now checked in one child process instead of six, removing five application start-ups per domain. Measured start-up cost was 4-6 seconds each, which dominated check time.
- The container CPU limit is now configurable with `CONTAINER_CPUS` (default 2) instead of a fixed single core.
- One child process covers SPF, DKIM, DMARC, DNS evidence, DNS host and expiry, with a 240-second limit per domain; each step is still isolated so one failure cannot discard the others.
### Added
- Check-all progress now shows the average seconds per domain.
### Upgrade notes
- Optional: add `CONTAINER_CPUS='4'` to `.env` on hosts with at least four CPU cores. The value must not exceed the host's core count.
## 0.13.10 - 2026-11-17
### Added
- Added Cancel remaining checks to an active Check-all run.
### Changed
- Cancelling stops queued batch items immediately while allowing up to the currently running worker count to finish safely.
- Domains that were individually queued before Check all remain queued after cancellation.
### Security
- The cancellation action is authenticated, CSRF-protected, transactional, and preserves completed history.
## 0.13.9 - 2026-11-17
### Added
- Dashboard cards now update automatically when their queued check completes, keeping search, filters, sorting and scroll position.
- Pending cards show Check queued, or Checking during a Check-all run; recently completed cards show Updated just now.
- Added an authenticated status endpoint that returns only pending and completion state for dashboard cards.
### Changed
- Confirmed expiry dates and Not published by registry results are reused for 24 hours instead of being looked up on every check, reducing check time and registry traffic.
- Temporary expiry lookup errors are still retried on the next check.
### Fixed
- DNS evidence no longer reports a difference when recursive and authoritative DNS both return NXDOMAIN.
- Recursive resolver errors are treated as unavailable evidence rather than a recursive/authoritative mismatch.
## 0.13.8 - 2026-11-16

### Added
- Added bounded parallel domain checking with four workers by default and a supported range of one to eight.
- Added active worker count, elapsed time, and estimated remaining seconds to Check-all progress data.

### Changed
- Check-all still permits only one batch, but up to four different domains can be checked concurrently.
- Individual Check now requests do not duplicate domains already queued or running in the active batch.
- Interrupted running batch items return to queued when the worker restarts.

### Security
- Each worker uses short-lived SQLite connections; database writes remain transactional and preserve revision checks.
- `.nz` WHOIS lookups remain bounded by existing timeouts and response-size limits.

## 0.13.7 - 2026-11-16

### Added
- Added dashboard search by friendly DNS host/provider name and cached nameserver hostname.

### Changed
- Updated the search label and example to show that DNS hosts such as Cloudflare and Microsoft can be searched.
- DNS-host searching uses cached check results and custom provider mappings without performing DNS lookups during page loads.

## 0.13.6 - 2026-11-16

### Fixed
- Restored the exact dashboard scroll position after Check now instead of re-centering the domain card.
- Refresh now preserves the current dashboard scroll position as well as search, filters, and sorting.
- Saved dashboard positions expire after two minutes and remain limited to the current browser tab.

### Changed
- Added an explicit dashboard Refresh hook without inline JavaScript or external dependencies.

## 0.13.5 - 2026-11-16

### Added
- Added sticky dashboard navigation while domain cards scroll.
- Added card-level Check queued feedback for pending manual checks.

### Fixed
- Check now on a dashboard card restores the same card after reload instead of jumping to the top.
- Dashboard search, status filters, sort selection, and scroll position remain intact after queuing a manual check.

### Security
- Scroll restoration uses same-tab session storage only and adds no inline script or external dependency.

## 0.13.4 - 2026-11-16
### Added
- Added protected Check-all batches with completed/total progress on the dashboard.
- Added queued, running and failed counts with three-second progress updates.
### Fixed
- Prevented repeated Check-all clicks from creating duplicate batches or rewriting queued work.
- Preserved active batch progress across worker restarts.
### Security
- Kept batch status behind authentication and exposed operational counts only.
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
- Added the MIT License.
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
