# Answers for external SDET framework (pytest) — from bill-mng repo truth

> Generated for the automation-framework questionnaire.  
> **UNKNOWN** = not in this repo; ask Platform QA / bill squad / platform.  
> Do **not** invent unpaid real bills. Do **not** paste production PII.

---

## 1) Environments & base URLs

### 1.1 Base URLs

| Env | Full base for `/bills/*` | Source |
|-----|--------------------------|--------|
| **Local bill-mng** | `http://localhost:7074/platform/api` | `server.port=7074`, `spring.mvc.servlet.path=/platform/api` |
| **UAT microservice (uatms)** | `https://example.com/bill-mng/platform/api` | Confirmed by your MS path; matches SpringDoc staging server pattern `/{spring.application.name}/platform/api` → `/bill-mng/platform/api` (`SpringDocConfig.java` + helm service name `bill-mng`) |
| **UAT app/gateway** | UNKNOWN exact public app URL for bill APIs | App clients typically hit API gateway, not uatms directly. For **bill-mng microservice automation**, **uatms …/bill-mng/platform/api is the correct target** you already use. |

Example local:
`http://localhost:7074/platform/api/bills/inquiry`

Example uatms:
`https://example.com/bill-mng/platform/api/bills/inquiry`

Is `/bill-mng/platform/api` the only correct slug on uatms?  
**YES for bill-mng microservice routing** (service name + servlet path). Other hostnames (e.g. `example.com` without `/bill-mng`) are **APP/gateway** paths — use only if your call must go through that edge; not required for the validation suite you already ship on uatms.

### 1.2 Shared bill sandbox / stub edge (Option D)

**DOES NOT EXIST in this repo** as a deployable sandbox profile or docker-compose stub edge.

What exists:
- **In-repo WireMock** for Maven `*IT` via Testcontainers (`AbstractResourceIT` + `@EnableContainers(... Wiremock)`)
- Real UAT providers behind uatms (what you hit today)

**Who would own Option D:** Platform QA platform / bill squad + DevOps — not defined in bill-mng.

### 1.3 Staging OpenAPI / Swagger

| Item | Value |
|------|--------|
| Staging enabled | YES (`application-staging.properties` springdoc urls; `SpringDocConfig` `@Profile("staging")`) |
| Prod | DISABLED |
| Relative docs | `/platform/api/v3/api-docs`, swagger-ui relative `../v3/api-docs` |
| Expected on uatms (pattern) | `https://example.com/bill-mng/platform/api/v3/api-docs` |
| Swagger UI | `…/bill-mng/platform/api/swagger-ui.html` or springdoc default under servlet context |

**Confirm live 200 with curl** — gateway may restrict docs. If 404/401 → UNKNOWN (platform ACL).

---

## 2) Auth & identity for external automation

### 2.1 uatms bill-mng headers

| Question | Answer from repo |
|----------|------------------|
| Are User-Id + Agent + Platform-Version + Client-Id enough? | **YES for bill-mng itself** — no JWT filter in-service; identity from headers (`RequestContextInterceptor`). Matches your MS validation suite. |
| When is Bearer required? | **When calling APP/API gateway that enforces OAuth**, not when uatms routes allow header-only microservice access. Your observation “no Bearer on uatms for these calls” is consistent with bill-mng design. |

Also send `X-Forwarded-For` for pay paths (payment component).

### 2.2 Recommended User-Id

| UUID | Role in repo |
|------|----------------|
| `2d04d8eb-e6fa-4b12-8dae-6d15b4d1fda0` | Primary IT fixture user |
| `0beca23f-3bc5-4b49-adae-d4e47c1b720b` | Debtor in pending ITs |

**May you keep using the IT UUID on UAT?**  
**UNKNOWN / risky.** Repo does not provision that user on UAT. For validation-only (no ownership checks), any UUID often works. For pending ownership, recommendations, wallet pay tied to a real wallet — you need a **real UAT user** from UAA.

**Who knows:** Platform QA / UAA owners — request a dedicated automation user.

### 2.3 APP-side login

**UNKNOWN** in bill-mng repo (no client credentials for Platform app login).  
Use your existing Postman “Platform UAT - App User Login” / UAA flow when hitting non-uatms gateways.  
**Who:** Identity / UAA team.

### 2.4 Admin APIs

| Permission | Source |
|------------|--------|
| `READ_BILL_CONFIGS` | `deployment/user-mng-roles-2020-07-27.sql` |
| `UPDATE_BILL_CONFIGS` | same |
| `BILL_SEARCH` | `deployment/user-mng-roles-2020-04-14.sql` |

Granted in SQL to **role id 1** (admin). bill-mng does **not** enforce these itself — **user-mng / gateway** does when requests go through staff/admin edge.

| Question | Answer |
|----------|--------|
| How does external suite auth for admin on UAT? | UNKNOWN — typically staff/admin gateway + user with those permissions. Not proven on bare uatms. |
| Dedicated QA admin test user? | **DOES NOT EXIST in this repo.** Request from QA/user-mng. Vault/secret name: UNKNOWN. |

**Recommendation:** Treat admin weight tests as **blocked** until QA provides admin user + correct admin base URL (may differ from uatms bill-mng). Prefer GET-only or isolated env.

---

## 3) WireMock / local contract stack (Option C) — CRITICAL

### 3.1 Supported way for EXTERNAL framework

| Option | Exists? |
|--------|---------|
| a) docker-compose (bill-mng + WireMock + Mongo + Redis + Rabbit) | **DOES NOT EXIST** |
| b) Script / Makefile / README to start WireMock + point Feign | **DOES NOT EXIST** (only `docs/sdet/*` conceptual guidance) |
| c) Prebuilt “test profile” image for external consumers | **DOES NOT EXIST** in repo |
| d) Only AbstractResourceIT / Testcontainers inside Maven | **YES — this is the only supported path today** |

**Implication for pytest:** You cannot “just” point pytest at UAT and get WireMock. Options:
1. **Ask bill squad** to publish a compose/test image (owned work — DOES NOT EXIST yet).  
2. **Build your own** compose: run WireMock with copied mappings + run bill-mng locally with Feign URLs overridden (unsupported officially; possible DIY).  
3. Stay on **UAT validation + request Option E pool** for smoke SUCCESS.

### 3.2 Paths & Feign wiring

**Mapping roots** (under `bill-mng/src/test/resources/`):

| Folder | Path |
|--------|------|
| ghabzino | `ghabzino/mappings/` |
| finnotech | `finnotech/mappings/` |
| enovin | `enovin/mappings/` |
| wallet-mng | `wallet-mng/mappings/` |
| wallet-provider | `wallet-provider/mappings/` |
| switchpsp | `switchpsp/mappings/` |
| uaa | `uaa/mappings/` |
| user-mng | `user-mng/mappings/` |
| topup-mng | `topup-mng/mappings/` |
| parsian | `parsian/mappings/` |

**Example happy stubs (file names):**
- Water: `ghabzino/mappings/webservices_coresvc_waterbillinquiry-9fdccd54-03da-4db5-9f93-a9064a295b28.json` (WaterBillID `2029334804610`)
- Gas: `ghabzino/mappings/webservices_coresvc_gasbillinquiry-46fe3419-e915-449f-8ca9-9189086208c6.json`
- Telephone fixedline: `ghabzino/mappings/webservices_coresvc_fixedlinebillinquiry-*.json` (inquiryId style `02144473213`)
- Wallet spend: `wallet-provider/mappings/wallets_spend-89688c47-e739-4829-a387-63e22578df18.json`

**Feign / WireMock property keys** (`application-test.properties`):

```properties
platform.container.wiremock.ghabzino.mappings=ghabzino/mappings
platform.container.wiremock.ghabzino.url-reference=ghabzino.base.url

platform.container.wiremock.finnotech.mappings=finnotech/mappings
platform.container.wiremock.finnotech.url-reference=platform.client.finnotech.baseUrl

platform.container.wiremock.enovin.mappings=enovin/mappings
platform.container.wiremock.enovin.url-reference=platform.client.enovin.baseUrl

platform.container.wiremock.wallet-provider.mappings=wallet-provider/mappings
platform.container.wiremock.wallet-provider.url-reference=platform.component.payment.wallet-provider-base-url

platform.container.wiremock.wallet-mng.mappings=wallet-mng/mappings
platform.container.wiremock.wallet-mng.url-reference=platform.component.payment.wallet-mng-base-url,wallet.mng.base.url
# … switch-psp, user-mng, uaa, topup-mng, parsian similarly
```

Standalone ports in `*/test.properties` (examples): ghabzino/finnotech `:5053`, enovin `:5051`.

Local (non-test) still points at nginx-bill / uatms — see `application-local.properties`.

### 3.3 Copy mappings + WireMock Docker alone?

| Approach | Verdict |
|----------|---------|
| WireMock alone without bill-mng | **Insufficient** for testing Platform contracts — you need bill-mng as SUT |
| Copy mappings + WireMock + **local bill-mng** with Feign → WireMock | **DIY possible**, **not officially supported** |
| Must rewire Feign | **YES** — otherwise bill-mng calls real providers |

### 3.4 Fixture catalog — WireMock-safe vs UAT

| ID | WireMock / IT | Live UAT |
|----|---------------|----------|
| Water inquiryId `2029334804610` | YES (ghabzino stub) | UNKNOWN (may not exist / paid) |
| Gas inquiryId `3236047426` / bill `236047406238` | YES (stub) | UNKNOWN |
| Tel default `2664034900143` / `51450157` | Used in ITs; **no dedicated stub for that billId** (amount from payId path) | You saw `BILL_TYPE_IS_INACTIVE` — type inactive on UAT, not necessarily bad id |
| MCI `4079157230158` / `113802204`, cell `09177171472` | YES (enovin/finnotech stubs) | UNKNOWN |
| Unit-test pair `6535478830150` / `109572658` | Platform-valid checksum | **You saw SUCCESS once** → may be a real/staging debt that can become paid/duplicate → treat as **FLAKY**, not a stable pool |
| Wallet ticket `4d8ab90e5ed949a0a0353157cd97dca93` | YES (wallet-provider stub) | **Do not use on UAT** |

### 3.5 After wallet pay — verify/settle / poll

| Item | Answer |
|------|--------|
| Verify REST | **Disabled** (`platform.component.payment.properties.utilitybill.verify-resource-enabled=false`) |
| Verify/settle | **Async Rabbit** (`bill.verify`, `bill.settle`) — YES in IT when Rabbit Testcontainer up and listeners enabled |
| Poll target | Prefer **ORDERED (12)** for full happy end; **CONFIRMED (7)** acceptable mid-state |
| Typical wait | UNKNOWN for external; ITs use async messaging. Suggest poll 30–120s with backoff for local; UAT may be longer |
| `verify.time.window` | `600000` ms (10 min) in props; verification window time also `bill.verification.window.time=10` (minutes) |

Note: `application-test.properties` has `scheduling.enabled=false` — some schedulers off; listeners may still process verify/settle queues.

### 3.6 Minimal run book

**Official:** DOES NOT EXIST.

**Closest in-repo:**

```bash
# From bill-mng module — runs ITs with Testcontainers WireMock (not pytest)
./mvnw -pl bill-mng test -Dtest=BillInquiryResourceIT
```

**DIY external (unsupported sketch):**

```text
1) docker run mongo / redis / rabbit
2) docker run wiremock -v ghabzino/mappings:/home/wiremock/mappings -p 5053:8080
   (repeat ports/mappings per provider as needed)
3) Run bill-mng with profile that sets ghabzino.base.url=http://host:5053
   (and other Feign URLs) + Mongo/Redis/Rabbit
4) curl -X POST http://localhost:7074/platform/api/bills/inquiry \
     -H 'User-Id: …' -H 'Agent: ANDROID' -H 'Platform-Version: 2019-09-30' \
     -H 'Client-Id: platform-client-id' -H 'Content-Type: application/json' \
     -d '{"payMethod":3,"type":4,"inquiryId":"2029334804610"}'
```

**Who should deliver a real compose:** bill-mng DEV + platform.

---

## 4) Curated UAT / staging bill pool (Option E)

### 4.1 Existing pool?

**DOES NOT EXIST in bill-mng repo.**  
No vault path, Confluence link, or spreadsheet checked in.

**Who owns / who to ask:** Platform **QA for bill / utility payments** + **bill-mng squad** (DEV). Process: UNKNOWN — ask your SDET lead / bill PO for “staging bill catalog”.

### 4.2 If pool is created — required shape

```yaml
# secrets/uat_bills.yaml  (keys only — placeholders)
water_default:
  billId: "REPLACE"
  payId: "REPLACE"
  mode: inquiry_only   # or pay_allowed
electricity_inquiryId:
  payMethod: 3
  type: 5
  inquiryId: "REPLACE"
  mode: inquiry_only
gas_default:
  billId: "REPLACE"
  payId: "REPLACE"
  mode: pay_allowed
telephone_default:
  billId: "REPLACE"
  payId: "REPLACE"
  mode: inquiry_only
meta:
  refresh_on: [BILL_DUPLICATE_FOUND, amount_zero, BILL_NOT_FOUND]
  parallel_lock: one_job_per_bill_id
  duplicate_window_days: 60
```

### 4.3 Mobile

| Item | Answer |
|------|--------|
| Approved test MSISDNs | **DOES NOT EXIST in repo** (IT cells like `09177171472` are WireMock fixtures) |
| MTN pay-create blocked | **YES** in code (`UnsupportedMtnBillPaymentException` / `BILL_MTN_OPERATOR_PAYMENT_NOT_SUPPORTED`) |
| MTN init → topup | **YES when** `mtn.bill.charge.payment.enabled=true` (default in `application.properties`) via `MtnBillTicketDelegatorAspect` |

### 4.4 Which types ACTIVE on UAT?

**UNKNOWN from repo** — stored in Mongo `bill_configs` / admin UI, not in git.  
Your `BILL_TYPE_IS_INACTIVE` for telephone fixture means **TELEPHONE currently inactive on that UAT**, not that the ID is invalid.

**How to discover:** `GET /bills/config` (app config) and/or `GET /admin/bills/configs` (needs admin) on uatms; or ask QA.

---

## 5) Data rules & fixtures confirmation

### 5.1 Still true on current main

| Rule | Confirmed? | Property / code |
|------------------|-----------------|
| billId/payId length 6–13 | YES | DTO `@Size`, UI |
| min pay 10001 | YES | `bill.min.pay.amount=10001` |
| duplicate window 60 days | YES | `bill.last.pay.days.before.today=-60` for CONFIRMED/PAID/ORDERED |
| business errors HTTP 422 + `result.title` | YES | `CustomizedResponseEntityExceptionHandler` |
| REST verify disabled / async Rabbit | YES | `verify-resource-enabled=false`; queues `bill.verify` / `bill.settle` |

### 5.2 Unit-test pair `6535478830150` / `109572658`

- Platform checksum: **still valid** (`ValidateUtilityBillTest`).  
- Live UAT SUCCESS once: **not a stable automation fixture** — treat as **FLAKY** (can be paid, duplicated, or provider-side change). Do not build suite on it without Option E ownership.

### 5.3 More safe INVALID cases on live UAT (no provider)

Beyond length/checksum/type/amount:
- Empty/missing required fields → `INVALID_PARAMETER`  
- Invalid cell length → `INVALID_PARAMETER`  
- `payMethod:3` without `type` → `INVALID_UTILITY_BILL_TYPE`  
- Unsupported/undefined utility prefix → `INVALID_UTILITY_BILL` / type errors  
- Init with empty payId → `INVALID_PARAMETER`  

Provider-dependent errors (`BILL_NOT_FOUND`, etc.) need Gate 3 — not “safe validation-only”.

---

## 6) Wallet pay prerequisites

### 6.1 Path

Configured dual bases:
- `platform.component.payment.wallet-provider-base-url` (spend — IT stubs under `wallet-provider/`)
- `wallet.mng.base.url` / `platform.component.payment.wallet-mng-base-url` (wallet-mng bill payment stubs)

Public API: `POST /bills/pay/wallet` with `{ "ticket" }`.

Exact UAT routing: **UNKNOWN** beyond local props pointing wallet-mng at uatms.

### 6.2 Min balance / wallet type

**UNKNOWN** in bill-mng (wallet service rules). Bill amount ≥ 10001 Rials.  
Insufficient → `WALLET_GW_CREDIT_NOT_ENOUGH` (from ITs).

### 6.3 Test user pattern

| Goal | Recommendation |
|------|----------------|
| CI pay SUCCESS | WireMock wallet stubs + IT ticket pattern (**not UAT**) |
| UAT pay smoke | Real UAA user + charged wallet — **UNKNOWN** who provisions; ask Wallet + QA |

Fixed IT UUID alone is **not** enough for real wallet spend on UAT.

---

## 7) Admin / provider weights

### 7.1 GET → PUT per-type → restore on shared UAT?

**Not recommended** until dedicated admin auth + ownership. Prefer **isolated env**. If allowed by QA: YES only with mandatory restore + mutex.

### 7.2 Global PUT `/admin/bills/configs` (no type)

**YES — overwrites ALL types** (`BillConfigServiceImpl.updateBillInquiryConfig`).  
External suites should **NEVER** call it on shared UAT without restore (+ ideally never).

### 7.3 CellNumber weights from properties?

**YES** — `WeightedRandomBillInquiryProviderSelectionStrategy.selectCellNumberProvider` uses `configs.getCellNumberInquiryProviderWeight`, **not** Mongo admin distributions. Admin UI sliders = billId/payId / inquiryId path for non-mobile-inquiryId cases.

---

## 8) Mongo / Redis / Rabbit

### 8.1 Collections (still accurate)

`utility_bills`, `bill_configs`, `bill_inquiry_configs`, `bill_inquiry_data`, `bill_inquiry_log`, `utility_bill_recommendations`, `supported_bill_organizations`, `refunds`

### 8.2 Staging Mongo for external SDET

**DOES NOT EXIST / not documented** for external VPN access in this repo.  
Local props mention hosts for DEV VPN — not a grant for pytest.  
**Assume DB asserts only inside bill-mng ITs** unless platform gives a read-only role.  
**Who:** DBA / bill squad / platform.

### 8.3 Redis

- Cache name: `bill-configs`  
- TTL: `bill.config.redis.ttl.hour=1`  
- Evicted on admin config update (`@CacheEvict`)  
**Do not flush Redis in shared UAT** from automation unless ops approves.

---

## 9) Deliverables

| Deliverable | Status |
|-------------|--------|
| A) docker-compose for external consumers | **DOES NOT EXIST** — request from bill DEV |
| B) Mapping file list for SUCCESS inquiry / inquiryId water / wallet chain | See §3.2 / §3.4 (copy from `src/test/resources/**/mappings`) |
| C) Feign → WireMock env vars | See §3.2 `platform.container.wiremock.*` + url-reference keys |
| D) `uat_bills.yaml` template | See §4.2 (placeholders only) |
| E) Fixture table WireMock vs UAT | See §3.4 |
| F) Contact / Slack / Jira | **UNKNOWN** — ask SDET lead / bill PO for component name |

---

## 10) Explicit non-goals — CONFIRMED

External suite should **NOT**:
- [x] Use production customer bills  
- [x] Use dashboard `/history` (app versions) as bill data  
- [x] Blind global `PUT /admin/bills/configs` on shared UAT without restore  
- [x] Assume Postman/UAT uses WireMock  

---

## End checklist

- [ ] **External WireMock path exists?** → **NO** (only Maven Testcontainers ITs). DIY unsupported; ask DEV for compose.
- [ ] **UAT bill pool exists?** → **NOT in repo** → **request from QA/bill squad** (Option E).
- [ ] **Recommended next slice for SDET:**
  1. **Keep shipping** `@validation` on uatms (done).  
  2. **`GET /bills/config` smoke** on uatms (discover active types — explains TELEPHONE inactive).  
  3. **Request Option E** unpaid staging bills (inquiry_only first).  
  4. **Parallel track:** ask bill-mng DEV for **docker-compose / contract env** (Option C) for CI SUCCESS without real bills.  
  5. Defer wallet pay E2E and admin weight mutations until users + pool + policy exist.

---

*Source: bill-mng repo (`application*.properties`, `AbstractResourceIT`, WireMock mappings, `deployment/*roles*.sql`, `BillUtils` / service code, `docs/sdet/*`). Platform ownership items marked UNKNOWN.*
