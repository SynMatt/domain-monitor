# Jinja templates

These server-rendered templates make up the Domain Monitor web interface. `base.html` supplies the shared page shell and the remaining templates extend it.

| File | Purpose |
|---|---|
| `base.html` | Shared HTML shell, navigation, favicon declarations, responsive CSS, security-conscious layout, version label, and footer. |
| `changelog.html` | In-application release history generated from `CHANGELOG.md`. |
| `detail.html` | Domain summary tiles, current SPF/DKIM/DMARC results side by side, and a collapsible history list showing what changed between entries. |
| `edit.html` | Add/edit form for domains, client labels, DKIM selectors, and minimum acceptable DMARC policy. |
| `index.html` | Primary dashboard containing counters, clickable status filters, search, sorting, result counts, and domain cards. |
| `login.html` | Administrator password sign-in form. |
| `settings.html` | Shared Pacific/Auckland daily-check schedule configuration. |

Templates must not contain organization names, customer domains, internal addresses, or production credentials.

| `dns_providers.html` | Custom DNS provider mappings and unrecognised nameserver review. |
