# Platform Bills — Testing Strategy (for Automation AI Agents)

> **Audience:** SDET + AI agents writing bill automation (Robot / RestAssured / Postman / etc.).  
> **Scope:** How to test bill **inquiry and pre-payment** flows, and what data to use (fake / real / stubbed).  
> **Companion docs:**
> - Full API/contracts: [`BILL_AUTOMATION_GUIDANCE_BOOK.md`](./BILL_AUTOMATION_GUIDANCE_BOOK.md)
> - Fake ID generator: [`scripts/bill_mng/fake_bill_generator.py`](../../scripts/bill_mng/fake_bill_generator.py)
> - Postman: [`postman/Bill-MNG-API.postman_collection.json`](./postman/Bill-MNG-API.postman_collection.json)

**Service under test:** Platform `bill-mng` (Bill Coordinator) — backend only.  
**Base path:** `/platform/api` · Port: `7074` (local) · UAT often via gateway e.g. `https://example.com/platform/api`

---

## 0. Agent instructions (read first)

When asked to write bill automation:

1. **Classify the test** → `@validation` | `@contract-wiremock` | `@uat-inquiry` | `@uat-pay` (see §3).
2. **Pick data strategy** from §4 — do **not** invent random billIds for UAT happy-path.
3. **Respect bill rules** in §5 (`BillUtils` checksum, length 6–13, min amount 10001).
4. **Assert** `result.title` + HTTP (business errors often **422**).
5. **Never** use production customer bills in CI.
6. For CI happy inquiry/pay → **WireMock + fixtures** (§6), not live Ghabzino/Finnotech.
7. For UAT smoke → **curated staging bill pool** (§4 Option E) from secrets/env.
8. UI “پرداخت با شناسه” ≠ “استعلام بدهی” — different payloads (§2).

**Prompt snippet for agents:**

```text
Use docs/sdet/BILLS_TESTING_STRATEGY.md as the source of truth for bill TEST DATA
and TEST LAYERS. Use BILL_AUTOMATION_GUIDANCE_BOOK.md for API contracts/enums.
Do not call live UAT inquiry with randomly generated billIds expecting SUCCESS.
Use fake_bill_generator.py only for Platform-validation / WireMock-paired tests.
```

---

## 1. What you are testing (product flows)

### 1.1 Backend happy path (API)

```text
GET  /bills/config
POST /bills/inquiry          ← focus of “before payment”
POST /bills/init             → PENDING + ticket
POST /bills/ticket/features
POST /bills/pay/wallet|dpg|ipg
[async] verify → CONFIRMED → settle → ORDERED
GET  /bills/{trackingCode}/details
```

### 1.2 UI screens (client apps — call same APIs)

| UI (Persian) | User enters | API |
|--------------|-------------|-----|
| **پرداخت با شناسه** | شناسه قبض + شناسه پرداخت (each 6–13 digits) | `POST /bills/inquiry` **default** `{ billId, payId }` |
| **استعلام بدهی** (e.g. قبض آب) | شناسه قبض only | `POST /bills/inquiry` `{ "payMethod": 3, "type": <BillType>, "inquiryId": "..." }` |
| Mobile | cell (+ operator) | `GET /bills/inquiry/{cellNumber}?operator=1\|2\|3` |

Button **ذخیره و استعلام** = save + inquiry (disabled until fields look valid).

### 1.3 Three gates every inquiry must pass

```text
Gate 1 — UI/API length          → 6..13 digits
Gate 2 — Platform BillUtils      → checksum + type + amount rules
Gate 3 — External provider      → Finnotech / Ghabzino / Enovin know the debt
```

| Gate | Fake random digits | Checksum generator | WireMock stub | Real staging bill |
|------|--------------------|--------------------|---------------|-------------------|
| 1 UI length | can pass | pass | pass | pass |
| 2 Platform | usually **fail** | **pass** | pass | pass |
| 3 Provider | **fail** | **fail** (live) | **pass** (stub) | **pass** (if unpaid) |

**Critical:** Checksum-valid fake ≠ live inquiry SUCCESS.

---

## 2. Inquiry payload cheat-sheet

### Default (پرداخت با شناسه)

```json
POST /bills/inquiry
{
  "billId": "{{billId}}",
  "payId": "{{payId}}"
}
```

### InquiryId / استعلام بدهی (e.g. water)

```json
POST /bills/inquiry
{
  "payMethod": 3,
  "type": 4,
  "inquiryId": "{{inquiryId}}"
}
```

`type` = API **BillType** int: WATER=4, ELECTRICITY=5, GAS=6, TELEPHONE=7, …

### Cell

```http
GET /bills/inquiry/09177171472?operator=1
```

`operator`: MCI=1, MTN=2, RIGHTEL=3.

### Required headers (typical)

```http
User-Id: <uuid>
Agent: ANDROID
Platform-Version: 2019-09-30
Client-Id: platform-client-id
X-Forwarded-For: 192.168.1.1
Content-Type: application/json
Authorization: Bearer <token>   # when via UAT gateway
```

---

## 3. Test layers (pyramid) — tag everything

```text
                 /\
                / UAT pay \          @uat-pay     ~5%   real disposable bills
               /-----------\
              / UAT inquiry \        @uat-inquiry ~10%  curated unpaid bills
             /---------------\
            / Contract+WireMock\     @contract    ~45%  fixtures + stubs
           /---------------------\
          / Validation / negative \  @validation  ~40%  synthetic invalid / checksum fakes
         /-------------------------\
```

| Tag | Environment | Data | Goal |
|-----|-------------|------|------|
| `@validation` | any / mock | Option A, B | Format, checksum, min amount, type mismatch |
| `@contract` | local bill-mng + WireMock | Option C | Happy + mapped provider errors, deterministic |
| `@uat-inquiry` | UAT gateway | Option E | Real provider smoke |
| `@uat-pay` | UAT + test wallet | Option E pay-pool | Full pay → poll ORDERED |

**Agent rule:** Default new tests to `@validation` or `@contract`. Only add `@uat-*` when secrets/pool exist.

---

## 4. All data options (complete matrix)

| ID | Option | What you use | Platform OK? | Live provider SUCCESS? | Pay E2E? | When to use |
|----|--------|--------------|-------------|------------------------|----------|-------------|
| **A** | Synthetic **invalid** | Bad length, empty, broken checksum | Fail on purpose | N/A | No | Negative / UI validation |
| **B** | Checksum-valid **fake** | `fake_bill_generator.py` / `BillUtils` rules | Yes | No (live) | No (live) | Platform gates; pair with WireMock for SUCCESS |
| **C** | **WireMock fixtures** | IT mapping IDs + stub JSON | Yes | N/A (mocked) | Yes (mocked) | **CI main path** |
| **D** | Shared staging **sandbox** | Team mock providers | Yes | Stubbed | Yes in sandbox | Team-wide fake UAT |
| **E** | Curated **UAT bill pool** | QA/ops staging bills | Yes | Yes if unpaid | Yes if allowed | Smoke only |
| **F** | Production bills | Real customers | Yes | Yes | Risky | **Forbidden in CI** |
| **G** | Test **cell** numbers | Telco/staging MSISDN | Format | If test lines exist | MTN special rules | Mobile flows |
| **H** | Recommendation / suggestion | Past ORDERED bills | N/A | Reuse / duplicate risk | Limited | Saved-bill UX |
| **I** | Mongo **seed** PENDING | DB insert | Skips inquiry | No | Partial | Internal pay-only units |

### 4.1 Option A — Invalid synthetic (always build this suite)

Examples:
- billId / payId length 5 or 14  
- empty payId on `/bills/init` → `INVALID_PARAMETER`  
- broken checksum → `INVALID_UTILITY_BILL`  
- `type` mismatch vs billId-derived type → `INVALID_UTILITY_BILL`  
- amount from payId &lt; 10001 → `BILL_AMOUNT_INVALID` on init  

No provider dependency. High volume, stable.

### 4.2 Option B — Fake checksum-valid bills

**Purpose:** Pass Gate 1–2 without a real debt.

**How to generate:** see §5 and `scripts/bill_mng/fake_bill_generator.py`.

```bash
python3 scripts/bill_mng/fake_bill_generator.py --type WATER --amount 25000 --account 12345678901
python3 scripts/bill_mng/fake_bill_generator.py --samples
python3 scripts/bill_mng/fake_bill_generator.py --validate 6535478830150 109572658
```

**Where fake bills ARE useful**
- UI enables استعلام with 6–13 digit fields  
- Assert Platform accepts body then returns provider error on live UAT  
- **CI:** same IDs registered in WireMock → SUCCESS  
- Type-code / amount encoding unit tests  

**Where fake bills are NOT useful**
- Expecting real بدهی amount on UAT without stub  
- Pay → ORDERED on live providers  
- Demo to PO of a “real” unpaid bill  

**On live UAT after Gate 2:**

```text
POST /bills/inquiry { fake }
  → Platform OK
  → Feign provider
  → BILL_NOT_FOUND / SERVICE_PROVIDER_EXCEPTION / FAILURE / …
```

### 4.3 Option C — WireMock (primary CI strategy)

**What is WireMock?**  
HTTP stub server. Platform Feign calls `localhost` instead of real Ghabzino/Finnotech/wallet. Stubs are JSON under `bill-mng/src/test/resources/*/mappings/`.

**Flow:**

```text
Robot/Postman → bill-mng → WireMock (fake Ghabzino) → canned Amount
                 Feign        NOT real provider
```

**IT enablement:** `@EnableContainers(... ImageType.Wiremock)`

**Example stub idea:** If `WaterBillID=2029334804610` → respond Amount=200000, Status=G00000.

**Stub folders:** `ghabzino`, `finnotech`, `enovin`, `wallet-mng`, `wallet-provider`, `switchpsp`, `uaa`, `user-mng`, `topup-mng`, `parsian`.

**Agent rule:** For `@contract` happy inquiry, use **IDs that already exist in mappings** (see §7), or generate ID **and** add a matching stub.

### 4.4 Option D — Shared sandbox

Same as C but ops runs persistent WireMock/fake providers for the whole QA team. Prefer if Platform already has this; otherwise use C in CI.

### 4.5 Option E — Real / staging curated pool

Maintain secrets (not in git):

```yaml
# secrets/uat_bills.yaml  (gitignored)
water_default:
  billId: "..."
  payId: "..."
  mode: inquiry_only   # or pay_allowed
gas_inquiryId:
  type: 6
  inquiryId: "..."
```

Rules:
- Owned by QA/ops; refresh when paid / `BILL_DUPLICATE_FOUND` / amount 0  
- Lock bill per parallel run  
- Separate inquiry-only vs pay-allowed  
- Duplicate window: last **60 days** for statuses CONFIRMED/PAID/ORDERED  

### 4.6 Options F–I (short)

- **F Production:** do not automate.  
- **G Mobile cells:** need test MSISDNs; MTN pay create blocked; init may proxy topup.  
- **H History/recommendations:** good for UX; bad as infinite fresh debt source.  
- **I Mongo seed:** skip inquiry; not full E2E.

---

## 5. Bill ID rules (must implement / assert)

Source: `com.platform.billcoordinator.util.BillUtils`

### 5.1 Length

- `billId`, `payId`: **6–13** characters (API `@Size`, UI hint).  
- Leading zeros stripped by Platform (`toStandardBillId` / `toStandardPayId`).

### 5.2 Check digit (mod-11 style)

```text
From right to left, multiply by 2,3,4,5,6,7,2,3,...
sum % 11 → if 0 or 1 then check=0 else check=11-mod
```

- **billId:** last digit = check over previous digits  
- **payId:** second-to-last = check over pay body; last = check over `billId + payBody` (match)

`validateUtilityBill(billId, payId)` = bill valid AND pay valid AND match.

### 5.3 Type digit inside billId

Second-to-last digit (before check) = utility code:

| Code | Type |
|------|------|
| 1 | WATER |
| 2 | ELECTRICITY |
| 3 | GAS |
| 4 | TELEPHONE |
| 5 | MOBILE (+ 3-digit operator prefix) |
| 6 | MUNICIPALITY |
| 8 | TAX |
| 9 | DRIVING_PENALTY |

**Do not confuse** with API `BillType` JSON ints (WATER=**4**, ELECTRICITY=**5**, …).

### 5.4 Amount from payId

```text
amount = Long.parse( payId without last 5 chars + "000" )
```

Examples:
- payId `51450157` → amount `514000`  
- payId `1501180` → amount `15000`  

**Min pay:** `bill.min.pay.amount` = **10001** Rials.

### 5.5 Known valid pairs (unit tests)

| billId | payId | valid |
|--------|-------|-------|
| 6535478830150 | 109572658 | true |
| 9635001104126 | 86970272 | true |
| 465310600140 | 9070306 | true |
| 9635001104126 | 109572658 | false |

### 5.6 Generator (Option B)

```bash
python3 scripts/bill_mng/fake_bill_generator.py --type WATER --amount 25000 --account 12345678901
# → billId + payId Platform-valid; live provider still unknown
```

Mobile helper in Platform: `cellNumberToBillId` / `cellNumberToPaymentId` (same checksum family).

---

## 6. WireMock flow (expanded for agents)

### 6.1 Mental model

```text
Without WireMock:  Client → bill-mng → Real Ghabzino/Finnotech
With WireMock:     Client → bill-mng → WireMock JSON stubs
```

Postman against **UAT gateway** does **not** use WireMock unless ops deploys a stub edge.

### 6.2 Contract test sequence (agent checklist)

1. Start Mongo, Redis, Rabbit, WireMock (or use bill-mng `*IT` pattern).  
2. Point Feign base URLs to WireMock ports.  
3. Choose fixture ID present in `mappings/`.  
4. `POST /bills/inquiry` with headers.  
5. Assert `result.title == SUCCESS` and amount from stub.  
6. Optional: `/bills/init` → `/bills/pay/wallet` with wallet stubs.  
7. Poll details until CONFIRMED/ORDERED if async verify enabled in that env.

### 6.3 Pairing fake generator + new stub

```text
1) Generate pair with fake_bill_generator.py
2) Add WireMock mapping: when provider receives that ID → return Amount X
3) Run inquiry against bill-mng pointed at WireMock
4) Assert SUCCESS
```

Without step 2, step 3 fails at Gate 3.

---

## 7. Ready fixture catalog (from bill-mng ITs)

Use these for `@contract` / WireMock-aligned tests (may need matching stubs):

### billId / payId

| billId | payId | Notes |
|--------|-------|-------|
| 2664034900143 | 51450157 | telephone happy |
| 2664034900143 | 1099157 | amount too low |
| 4079157230158 | 113802204 | MCI multi-term |
| 236047406238 | 35005608 | gas |
| 2498463593553 | 6980594 | MTN inquiry |
| 5743219100290 | 80020296 | driving penalty |
| 700880221142 | 1881238 | ticket info |
| 0247506993356 | 61601150 | MTN → topup init |
| 2029334804610 | (inquiryId water stub) | Ghabzino water mapping |

### Cells

| cell | Use |
|------|-----|
| 09177171472 | MCI success |
| 0917717147 | invalid length |
| 09037083670 | MTN |
| 09332475069 | MTN debt |

### Users (headers)

| Role | UUID |
|------|------|
| Primary | `2d04d8eb-e6fa-4b12-8dae-6d15b4d1fda0` |
| Debtor pending | `0beca23f-3bc5-4b49-adae-d4e47c1b720b` |

---

## 8. Assertion catalog (before / around payment)

| Case | Expected `result.title` (typical) |
|------|-----------------------------------|
| Happy inquiry (stub/real) | `SUCCESS` |
| Bad checksum / invalid id | `INVALID_UTILITY_BILL` |
| Type mismatch | `INVALID_UTILITY_BILL` |
| Empty/invalid param | `INVALID_PARAMETER` |
| Amount &lt; 10001 on init | `BILL_AMOUNT_INVALID` |
| Already paid (window) | `BILL_DUPLICATE_FOUND` |
| Provider unknown id | `BILL_NOT_FOUND` / provider-mapped / `FAILURE` |
| Inactive bill type | `BILL_TYPE_IS_INACTIVE` |
| Phone not supported | `BILL_PHONE_NUMBER_NOT_SUPPORTED` |
| Credit state | `BILL_ID_CREDIT_STATE` |
| Wallet insufficient | `WALLET_GW_CREDIT_NOT_ENOUGH` |

HTTP for business errors: often **422**.

Statuses after pay: PENDING→PAID→CONFIRMED→ORDERED (async Rabbit). Poll details; do not assume sync settle.

---

## 9. Recommended suite layout (Robot / any framework)

```text
tests/bill/
  validation/
    invalid_length.robot
    bad_checksum.robot
    amount_too_low.robot
    type_mismatch.robot
  contract/                    # WireMock profile
    inquiry_default_happy.robot
    inquiry_inquiryId_water.robot
    inquiry_cell_mci.robot
    init_and_wallet_pay.robot
  uat/                         # secrets required
    smoke_inquiry.robot        # @uat-inquiry
    smoke_pay.robot            # @uat-pay
data/
  invalid_bills.yaml           # Option A
  wiremock_fixtures.yaml       # §7
  # secrets/uat_bills.yaml     # Option E (gitignored)
tools/
  fake_bill_generator.py       # Option B
```

### Keywords agents should invent

```text
Generate Fake Bill    ${type}    ${amount}
Validate Bill Pair    ${billId}    ${payId}
Inquiry Default       ${billId}    ${payId}
Inquiry By InquiryId  ${type}    ${inquiryId}
Assert Result Title   ${response}    SUCCESS
```

---

## 10. Decision tree (for the AI agent)

```text
What is the goal?
│
├─ Prove UI/API rejects bad input?
│     → Option A (invalid synthetic). No real bill.
│
├─ Prove Platform accepts well-formed IDs / maps provider errors?
│     → Option B fakes (± live UAT for error titles) OR B+WireMock.
│
├─ Prove inquiry SUCCESS + amount in CI?
│     → Option C: fixture ID + WireMock stub. NOT live UAT random fakes.
│
├─ Prove real UAT provider integration?
│     → Option E curated pool. Skip if pool empty.
│
├─ Prove pay → ORDERED?
│     → Contract: WireMock wallet/IPG stubs
│     → UAT: pay_allowed bill + test wallet + poll status
│
└─ Unsure?
      → Write @validation first; ask human for UAT pool / sandbox.
```

---

## 11. Anti-patterns (do not do)

1. Random 13-digit billId on UAT expecting SUCCESS.  
2. Committing real customer bills to git.  
3. Paying shared UAT bills from parallel jobs without a lock.  
4. Assuming Postman UAT uses WireMock.  
5. Confusing API BillType `4` (WATER) with billId type digit `1`.  
6. Confusing admin path type `"1"` with API type `4`.  
7. Treating checksum-valid generator output as “real unpaid bill”.  
8. Skipping restore after `PUT /admin/bills/configs` global weight change.  
9. Using dashboard `/history` (app versions) as bill test data.  
10. Asserting ORDERED immediately after wallet pay without poll.

---

## 12. Quick links inside bill-mng repo

| Topic | Path |
|-------|------|
| Checksum / amount / type | `bill-mng/.../util/BillUtils.java` |
| Default inquiry validator | `.../validator/impl/DefaultBillRequestValidator.java` |
| InquiryId validator | `.../validator/impl/InquiryIdBillRequestValidator.java` |
| WireMock water stub example | `bill-mng/src/test/resources/ghabzino/mappings/*water*` |
| IT scenarios | `BillInquiryResourceIT`, `BillTicketResourceIT`, `BillResourceIT` |
| Valid pairs unit test | `ValidateUtilityBillTest.java` |
| Provider weights (admin) | Guidance book §20 |
| Full API catalog | Guidance book §5 |

---

## 13. One-page summary

| Need | Use |
|------|-----|
| Fake bills for Platform validation | `fake_bill_generator.py` (Option B) |
| Fake bills for SUCCESS inquiry in CI | Option B/C IDs **+ WireMock stub** |
| Real bills for UAT | Option E pool (secrets) |
| Most automation volume | Option A + Option C |
| Bill rules | length 6–13, mod-11 checksum, type digit, amount from payId, min 10001 |
| Before payment focus | `/bills/config`, `/bills/inquiry*`, then `/bills/init` |

---

*This file is the dedicated bills testing strategy for Platform bill-mng. Keep it next to your automation suite and point AI agents here for data/strategy decisions; use BILL_AUTOMATION_GUIDANCE_BOOK.md for full API contracts.*
