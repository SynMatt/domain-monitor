# Regression tests

The tests use isolated temporary SQLite databases and synthetic example domains. They must not contain production domains, customer names, internal addresses, or credentials.

| File | Coverage |
|---|---|
| `test_app.py` | Core authentication, CSRF protection, login throttling, domain/selector validation, DKIM key parsing, scheduling, page rendering, history, and status mapping. |
| `test_bulk.py` | Bulk-import parsing, duplicate handling, atomic failure behaviour, queueing, authentication, and CSRF protection. |
| `test_capital_status.py` | Capitalised Pass, Warn, Fail, Unknown, Pending, and Stale labels plus version metadata. |
| `test_changelog.py` | Changelog access control, rendering, displayed version, and health-endpoint version. |
| `test_clickable_filters.py` | Clickable SPF/DKIM/DMARC filters, invalid-filter handling, stale-to-Unknown mapping, and zero-result views. |
| `test_counter_layout.py` | Status-counter spacing, responsive layout rules, version metadata, and changelog release entry. |
| `test_scheduler_visibility.py` | Hidden healthy-worker state and visible missing/stale-heartbeat warning. |
| `test_search_sort.py` | Search by domain or label, severity ordering, combined filters, invalid-sort fallback, and result counts. |
| `test_status_counters.py` | Pass/Warn/Fail/Unknown totals, empty dashboards, and stale-result classification. |

| `test_timezone_settings.py` | Timezone allow-list validation, Settings persistence, timezone-aware scheduling, daylight-saving behaviour, version metadata, and changelog entry. |

| `test_generic_placeholder.py` | Generic search-placeholder text, removal of organization-specific UI examples, version metadata, and changelog entry. |

| `test_ai_disclaimer.py` | Visible AI-assisted project disclaimer, maintenance warning, independent-validation guidance, version metadata, and changelog entry. |

Run the complete suite in the built container so the tests use the same pinned dependencies as production. From a development checkout, `./scripts/run-tests.sh` builds the image and runs every test once in a single container.

| `test_dns_provider_settings.py` | Mapping CRUD, authentication, CSRF, suffix boundaries, cached labels, fallback and schedule preservation. |
| `test_release_0142.py` | Compact history, grouping of unchanged results, one-time upgrade compaction, Flask pin, HTTPS-only RDAP and single-run test tooling. |
| `test_release_metadata.py` | Displayed and reported versions come from APP_VERSION, and the changelog starts with the current release. |
| `test_release_0143.py` | Host-fitted CPU and worker settings, manual override, dry run, settings preserved, and setup/update wiring. |
| `test_release_0144.py` | README review marker and changelog README line for every release, documented scripts, Hyper-V tuning, and hidden expected test logs. |
| `test_release_0145.py` | README update examples outside the generated block use `X.Y.Z`, never a real release number. |
| `test_release_0146.py` | Domain details layout, change summaries between history entries, grouped entries and the history_changes helper. |
| `test_release_0147.py` | README manual tuning example, configuration example labels worker/CPU values as automatic, details page described, no release notes in the README body. |
| `test_registrable_domain_expiry.py` | Public Suffix List registrable-domain expiry resolution for apex and subdomain inputs. |
