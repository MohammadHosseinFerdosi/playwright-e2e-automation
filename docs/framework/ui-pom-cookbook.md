# UI Page Object cookbook (Playwright)

How app / domain teams add UI coverage in the pytest suite.
Stack: native Playwright + `BasePage` — **not** Robot Browser / Selenium.

## Rules

1. Locators live on page classes under `tests/ui/pages/` — never in step files.
2. Every page inherits `tests.ui.pages.base_page.BasePage`.
3. Prefer API login inject (`AppUiAuth`) over full UI OTP unless the scenario is about auth itself.
4. Wire pages via fixtures in `tests/conftest.py` (function-scoped, xdist-safe).
5. Gherkin stays business language — steps call page methods, not selectors.

## Happy-path recipe (hub → domain)

```text
Given a logged-in customer          → AppUiAuth.inject_session / login
When they open a service from the hub     → family: `the customer opens <feature> from the hub`
Then they see the service screen          → XxxPage.should_be_on_…
```

### Minimal step sketch

```python
@given("a logged-in customer on the app hub")
def _(app_ui_auth: AppUiAuth, hub_page: HubPage, user_factory: UserFactory):
    user = user_factory.create(cell_number_prefix="0945")
    app_ui_auth.login_and_inject(user)  # or project’s inject helper
    hub_page.open()

@when(parsers.re(r"^the customer opens (?P<feature>[A-Za-z0-9 -]+) from the hub$"))
def _(feature: str, hub_page: HubPage, top_up_page: TopUpPage, ...) -> None:
    open_from_hub(feature, hub_page, top_up_page, ...)
```

## Adding a new page

1. Read Robot locators under `src/pages/app/*.resource` (behavior / selectors only).
2. Create `tests/ui/pages/app/<name>_page.py`:
   - `PATH` from Settings / CONSTANTS (e.g. `settings.top_up_page_path`)
   - `LOCATORS` dict (xpath/css) as class attribute
   - methods: `open`, `should_be_on_…`, actions (`enter_…`, `click_…`)
3. Add a fixture next to the other page fixtures in `tests/conftest.py`.
4. Keep steps thin; put multi-step UI asserts in `tests/services/` only if reused.

## Existing shells (foundation)

| Page | Module | Notes |
|------|--------|--------|
| Hub / home / login / onboarding | `tests/ui/pages/app/` | Auth + navigation |
| Bill landline + bill confirm | `tests/ui/pages/app/bill/` | First domain UI |
| Pay (transactions) | `pay_page.py` | Bottom-nav pay tab |
| Top-up | `top_up_page.py` | Charge flow shell |
| Wallet management | `wallet_management_page.py` | Balance screen |
| Checkout confirm (`/confirm`) | `checkout_confirm_page.py` | Shared confirm (top-up etc.) |
| Dashboard login | `tests/ui/pages/dashboard/` | Dashboard only |

Do **not** port all remaining Robot pages up front — add them when a team’s scenario needs them.

## Auth

| Path | When |
|------|------|
| `AppUiAuth` API inject | Default for e2e after login |
| `LoginPage` + Redis OTP | Auth / onboarding scenarios only |
| `DashboardUiAuth` | Dashboard UI |

## Running UI locally

```bash
.venv/bin/playwright install chromium
PYTHONPATH=. .venv/bin/pytest -m "platform_ui_hub or bill_tci_ui" -v
# headed debug:
PYTHONPATH=. .venv/bin/pytest -m platform_ui_hub --headed -v
```

Needs VPN / UAT + MySQL + Redis (for OTP if not using inject-only smoke).

## Tags

UI features: `@e2e` + suite + domain + unique `@feature` tag. Register new feature markers in `pyproject.toml`.
See `.cursor/rules/gherkin-style.mdc`.
