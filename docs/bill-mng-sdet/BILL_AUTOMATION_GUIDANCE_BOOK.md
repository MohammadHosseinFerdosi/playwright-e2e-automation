# Platform bill-mng — SDET Automation Guidance Book

> **Purpose:** Drop this file into your automation framework (or point your AI agent at it) and use it as the single source of truth to design bill API scenarios, Postman runs, RestAssured/Karate suites, and assertions.  
> **Repo analyzed:** Platform `bill-mng` (Bill Coordinator microservice).  
> **Companion artifacts:**
> - Postman collection: [`postman/Bill-MNG-API.postman_collection.json`](./postman/Bill-MNG-API.postman_collection.json)
> - Postman environment: [`postman/Bill-MNG-Local.postman_environment.json`](./postman/Bill-MNG-Local.postman_environment.json)
> - Cursor canvas overview: `~/.cursor/projects/.../canvases/bill-mng-sdet-guide.canvas.tsx`

---

## 0. How an AI / SDET should use this book

1. Read §1–§3 first (what the service is, architecture, happy path).
2. Use §4–§6 for request/response contracts and enums when writing clients.
3. Use §7 for status machines and business rules (assertions).
4. Use §8 for ResultStatus / error catalog (negative tests).
5. Import Postman collection (§9 / §12) for manual exploration; port the same folders into code.
6. Use §10 IT scenario catalog as your first backlog (already proven in-repo).
7. Use §11 fixtures (billId/payId/userId) from WireMock ITs.
8. Use **§20** for admin **provider weight** (Ghabzino/Finnotech split), dual config model, settlement weights, and what is NOT bill-mng (History API).
9. Remember: **no UI in this repo** — UI automation lives in Platform client apps; they call these APIs.

---

## 1. What this project is

| Item | Detail |
|------|--------|
| Name | Platform **Bill Coordinator** (`com.platform.billcoordinator`) |
| Role | Inquire Iranian utility bills, create payment tickets, pay (wallet/IPG/DPG), verify, settle with providers, recommend, refund, notify |
| Modules | `bill-mng-spec` (DTOs/enums/events JAR) + `bill-mng` (Spring Boot service) |
| Stack | Java 17, Spring Boot 3.3, Spring Cloud, OpenFeign, MapStruct, Lombok, SpringDoc OpenAPI 2.6 |
| Data | **MongoDB** (`utility_bills`, configs, recommendations, refunds…) |
| Cache | **Redis** |
| Messaging | **RabbitMQ** (verify, settle, recommendation, refund, notif, report) |
| Port | `7074` |
| Base path | `/platform/api` → full URL `http://{host}:7074/platform/api/...` |
| UI | **None** in this repository |
| README | None — this guide fills that gap for SDET |

**Entry point:** `bill-mng/src/main/java/com/platform/billcoordinator/BillCoordinatorApplication.java`

---

## 2. Architecture (how it was developed)

```
Mobile / Web Platform apps
        │
        ▼
   API Gateway  ──injects──►  User-Id, Agent, Platform-Version, Client-Id, X-Forwarded-For
        │
        ▼
   bill-mng :7074 /platform/api
        │
        ├── MongoDB (UtilityBill lifecycle)
        ├── Redis (bill config cache)
        ├── RabbitMQ (async verify / settle / refund / notif / report)
        └── Feign clients
              ├── Finnotech (billing inquiry)
              ├── Ghabzino (water/elec/gas/phone/mobile inquiry)
              ├── Enovin / Parsian / POD (settlement / wallet bill pay)
              ├── wallet-mng / wallet-provider
              ├── switch-psp (card/IPG/DPG)
              ├── user-mng
              ├── topup-mng (MTN bill→charge bridge)
              └── credit-mng (refunds)
```

### Package map (where to look)

| Path | Responsibility |
|------|----------------|
| `api/web/bill/*Resource.java` | Public REST for bills |
| `api/web/recommendation/` | Saved bills CRUD |
| `api/web/promotion/` | Banners |
| `api/web/admin/` | Ops flush/stats |
| `api/web/filter/RequestContextInterceptor` | Header → request context |
| `service/bill/base/impl/BillServiceImpl` | Status, pay, verify, settle, finalize |
| `service/bill/inquiry/**` | Provider selection + inquiry |
| `service/settlement/**` | Enovin/POD/Parsian settlement |
| `service/refund/**` | Reject → refund |
| `client/**` | Outbound Feign (stub these in contract tests) |
| `model/bill/UtilityBill` | Mongo document |
| `bill-mng-spec/.../spec/` | **API contract library** |
| `src/test/**/*IT.java` | Integration scenarios + WireMock |

### Payment library inheritance (important)

Many pay/ticket routes come from Platform `payment2` component:

- `BillTicketResource extends TicketResource` → `/bills/init`, `/bills/info/{ticket}`, `/bills/ticket/features*`
- `BillResource extends PayableEntityResource` → `/bills/pay/wallet`, `/bills/pay/dpg`, `/bills/search`, verify
- `BillController extends PayableEntityController` → IPG result callbacks

If OpenAPI on staging is incomplete, reverse contracts from ITs + this guide.

### Auth model

- **No JWT validation inside bill-mng.**
- Gateway (or test client) must send identity headers.
- Pending detail checks `User-Id == bill.debtor.userId`.
- Admin APIs need user-mng permissions: `BILL_SEARCH`, `READ_BILL_CONFIGS`, `UPDATE_BILL_CONFIGS`.

---

## 3. Happy path (primary automation flow)

```
1. GET  /bills/config
2. POST /bills/inquiry          → amount, billId, payId, billType, termType
3. POST /bills/init             → ticket + trackingCode ; status = PENDING(1)
4. POST /bills/ticket/features  → wallet / dpg / ipg
5. POST /bills/pay/wallet       → status = PAID(8)
6. [async] Rabbit bill.verify   → status = CONFIRMED(7)
7. [async] Rabbit bill.settle   → provider settlement
8. [async] finalize             → status = ORDERED(12)
9. GET  /bills/{trackingCode}/details  → assert end state
```

**Automation tip:** After step 5, poll step 9 with timeout/backoff until `ORDERED` or `CONFIRMED`. Do not assume sync finalize.

---

## 4. Headers (exact names)

From Platform `com.platform.component.common.Constants`:

| Header | Constant | Example | Required for |
|--------|----------|---------|--------------|
| `User-Id` | `REQUEST_HEADER_USER_ID` | UUID | Most bill APIs |
| `Agent` | `REQUEST_HEADER_AGENT` | `ANDROID` / `IOS` / `WEB` / `GATEWAY` / `APP_MEDIATOR` | Config, inquiry, init |
| `Platform-Version` | `REQUEST_HEADER_VERSION` | `2019-09-30` | Config/inquiry versioning |
| `Client-Id` | `REQUEST_HEADER_CLIENT_ID` | `platform-client-id` | Ticket/init |
| `X-Forwarded-For` | `REQUEST_HEADER_X_FORWARDED_FOR` | `192.168.1.1` | Pay |
| `ticket` | `REQUEST_HEADER_TICKET` | ticket string | Card OTP, some ticket ops |
| `User-Agent` | `REQUEST_HEADER_USER_AGENT` | okhttp/... | Optional |
| `market` | `REQUEST_HEADER_MARKET` | | Optional |
| `Authorization` | — | `Bearer …` | Only if calling via real gateway |

**HTTP business errors** typically return **422** with body:

```json
{
  "result": {
    "title": "BILL_DUPLICATE_FOUND",
    "status": <int>,
    "message": "..."
  }
}
```

Assert on `result.title` (enum name string), not only HTTP code.

---

## 5. Complete public API catalog

Base: `/platform/api`

### 5.1 Inquiry — `BillInquiryResource`

| Method | Path | Headers | Body | Response |
|--------|------|---------|------|----------|
| POST | `/bills/inquiry` | User-Id, Platform-Version, Agent | `BillInquiryRequest` | `BillInquiryResponse` |
| POST | `/bills/validate` | same | same | same (**deprecated** alias) |
| GET | `/bills/inquiry/{cellNumber}?operator=` | User-Id, Platform-Version, Agent | — | `CellNumberBillInquiryResponse` |
| POST | `/bills/inquiry-suggestion` | User-Id | `{}` | `BillInquirySuggestionResponse` |

`operator` default `1`: MCI=1, MTN=2, RIGHTEL=3.

### 5.2 Bill resource — `BillResource` + payment2

| Method | Path | Headers | Body | Response |
|--------|------|---------|------|----------|
| GET | `/bills/config?isMobileBill=` | Platform-Version, Agent, User-Id? | — | `BillConfigResponse` |
| GET | `/bills/recommendations` | Platform-Version, Agent, User-Id | — | `BillRecommendationResponse` |
| GET | `/bills/{trackingCode}/details` | — | — | `BillDetailResponse` |
| GET | `/bills/pending/{trackingCode}` | User-Id (= debtor) | — | `PendingDetailResponse` |
| POST | `/bills/search` | admin perms | search query | `BillListResponse` |
| POST | `/bills/pay/wallet` | X-Forwarded-For | `{ "ticket" }` | `InAppPayResponse` |
| POST | `/bills/pay/dpg` | X-Forwarded-For | pay request | `InAppPayResponse` |
| POST | `/bills/verify/{trackingCode}` | User-Id | — | **Disabled** (`verify-resource-enabled=false` → 403) |

### 5.3 Ticket — `BillTicketResource` (payment2)

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/bills/init` | `BillPaymentRequest` | `BillPaymentInitiateResponse` |
| GET | `/bills/info/{ticket}` | — | ticket/payment detail |
| POST | `/bills/ticket/features` | ticket request | feature list |
| POST | `/bills/ticket/features/assign` | assign request | `PayDetailResponse` |

### 5.4 IPG — `BillController` (payment2)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/bills/pay/ipg/{ticket}` | Start IPG |
| GET/POST | `/bills/pay/ipg/result` | PSP callback |
| GET | `/bills/ipg/result/{pspCode}/{traceId}` | Alternate callback |

### 5.5 Admin bills config — `BillAdminResource` `/admin/bills`

| Method | Path | Body | Notes |
|--------|------|------|-------|
| GET | `/admin/bills/configs` | — | Per-type + `totalInquiryDistributions` (see **§20**) |
| PUT | `/admin/bills/configs/{type}` | `BillConfigUpdateRequest` | Path `{type}` = **UtilityBillType code** `"1"`… ; can update **weights** and/or **active** |
| PUT | `/admin/bills/configs` | `{ inquiryDistributions }` | Applies **same weights to ALL bill types** |

Permissions (user-mng): `READ_BILL_CONFIGS`, `UPDATE_BILL_CONFIGS`.

### 5.6 Admin ops — `AdminResource` `/admin/bill`

| Method | Path | Params |
|--------|------|--------|
| GET | `/admin/bill/{type}/statistics` | start, end (epoch ms); type=0 BILL |
| POST | `/admin/bill/{type}/end-states/flush` | start, end |
| POST | `/admin/bill/settle/inquiry` | date (noop stub currently) |

### 5.7 Recommendations — `/recommendations`

| Method | Path | Notes |
|--------|------|-------|
| GET | `/recommendations/{type}?billType=` | type=`2` = UTILITY_BILL |
| PUT | `/recommendations/{type}` | update |
| DELETE | `/recommendations/{type}/{id}` | delete |

### 5.8 Promotion

| Method | Path | Headers |
|--------|------|---------|
| GET | `/promotion/banner/{type}` | Agent |

### 5.9 Cards (payment2)

| Method | Path | Headers | Body |
|--------|------|---------|------|
| POST | `/cards/otp` | ticket, User-Id | `{ pan, transactionType }` |

### 5.10 Settings (payment2 / setting) — IT covered

| Method | Path |
|--------|------|
| PUT | `/admin/settings/sdk/pay-gateways/{type}/toggle-gateway/{businessId}` |

`type=2` for UTILITY_BILL.

### 5.11 Outbound (not public — stub in contract tests)

| Client | Examples |
|--------|----------|
| Ghabzino | `/ElectricityBillInquiry`, `/GasBillInquiry`, `/WaterBillInquiry`, `/FixedLineBillInquiry`, `/MtnMobileBillInquiry`, `/MtnMobileDebtInquiry` |
| Finnotech | `/billing/v2/clients/{clientId}/billingInquiry`, `detailBillingInquiry` |
| Enovin | `/billinquiry`, `/token` |
| Parsian | `/FinancialOperation/ExternalBillPayment`, `InqueryTransactionFull` |
| TopUp | `/top-ups/init`, `/top-ups/ticket/features` |
| Credit | `/credit/purchases/refunds` |

WireMock stubs live under `bill-mng/src/test/resources/{provider}/mappings/`.

---

## 6. Request / response contracts (fields)

### 6.1 Polymorphic inquiry request

JSON discriminator: **`payMethod`**

| payMethod | Class | Fields |
|-----------|-------|--------|
| omitted / `1` | `DefaultBillInquiryRequest` | `billId` (6–13), `payId` (6–13), optional `type` |
| `2` (deprecated) | `SimpleBillInquiryRequest` | `billId`, optional `type` |
| `3` | `CustomBillInquiryRequest` | `inquiryId`, **`type` required** |

```json
{ "billId": "2664034900143", "payId": "51450157" }
```

```json
{ "payMethod": 3, "type": 6, "inquiryId": "3236047426" }
```

### 6.2 BillPaymentRequest (`POST /bills/init`)

Extends `BaseTicketRequest` + bill fields:

| Field | Rules |
|-------|-------|
| `billId` | NotBlank, size 6–13 |
| `payId` | NotBlank, size 6–13 |
| `callbackUrl` / `redirectUrl` | from BaseTicketRequest |
| `userId` | optional (often from header) |
| `amount` | parent may allow; service recalculates from payId |
| `type` | ticket type UTILITY_BILL |

```json
{
  "billId": "700880221142",
  "payId": "1881238",
  "callbackUrl": "https://example.com/web/test"
}
```

### 6.3 WalletPayRequest

```json
{ "ticket": "{{ticket}}" }
```

### 6.4 BillInquiryResponse

| Field | Type |
|-------|------|
| `result` | Result (title/status/message) |
| `billInfo` | BillInfoDto (**deprecated**) |
| `billInfos` | `List<BillInfoDto>` **use this** |

### 6.5 BillInfoDto

`amount`, `feeCharge`, `name`, `creationDate`, `trackingCode`, `expirationDate`, `payExpirationDate`, `imageId`, `billId`, `payId`, `billType`, `colorRange`, `targetCellNumber`, `targetTelephone`, `rrn`, `hintDto`, `remarkDto`, `termType` (`MID_TERM=0` / `FINAL_TERM=1`)

### 6.6 CellNumberBillInquiryResponse

`midTerm`, `finalTerm` (`BillInfoDto`), `result`

### 6.7 BillDetailResponse

`billInfo`, `result`

### 6.8 PendingDetailResponse

`status`, `color`, `imageId`, `title`, `amount`, `ticket`, `message`, `trackingCode`, `statusImageId`, `detailInfo`

### 6.9 BillConfigResponse

`configs: List<BillConfigDto>`, `landingConfig`, deprecated `icons`

**BillConfigDto:** `title`, `badgeTitle`, `badge`, `active`, `imageId`, `type`, `pageTitle`, `payMethods`, `inquiryMethods`, `description`, `payUrl`

### 6.10 BillConfigUpdateRequest

```json
{
  "active": true,
  "disableMessage": null,
  "inquiryDistributions": [
    { "provider": 0, "weight": 50 },
    { "provider": 1, "weight": 50 }
  ]
}
```

### 6.11 BillPaymentInitiateResponse

`ticket`, `payUrl`, `fallbackUrl`, deprecated `billInfo`, `result`

---

## 7. Enums (memorize these — two code systems!)

### 7.1 BillStatus (API / spec) — JSON int

| Name | Value | Meaning for tests |
|------|------:|-------------------|
| PENDING | 1 | After init — payable |
| FAILED | 2 | Pay failed — can retry pay |
| CANCELED | 4 | Canceled |
| EXPIRED | 5 | Expired |
| REVERSED | 6 | Wallet reverse after verify window |
| CONFIRMED | 7 | Verified — settlement running |
| PAID | 8 | Pay OK — awaiting verify |
| REJECTED | 11 | Settlement rejected → refund |
| ORDERED | 12 | **Happy end state** |
| READY_TO_REFUND | 13 | Spec only (not on Mongo `Status`) |

**Mongo `Status` enum** = same without `READY_TO_REFUND`.

### 7.2 BillType (API JSON int) vs UtilityBillType (admin path string)

| Name | API `BillType` | Model `UtilityBillType` code |
|------|---------------:|------------------------------|
| OTHER | 0 | `"0"` |
| WATER | 4 | `"1"` |
| ELECTRICITY | 5 | `"2"` |
| GAS | 6 | `"3"` |
| TELEPHONE | 7 | `"4"` |
| MUNICIPALITY | 8 | `"6"` |
| TAX | 9 | `"8"` |
| DRIVING_PENALTY | 10 | `"9"` |
| MCI_MOBILE | 11 | `"15"` |
| MTN_MOBILE | 12 | `"25"` |
| RIGHTEL_MOBILE | 13 | `"35"` |

**Pitfall:** Admin `PUT /admin/bills/configs/{type}` uses **model codes** (`"1"` for WATER), not API `4`.

### 7.3 BillInquiryMethod (`payMethod` in request)

| Name | JSON | Class |
|------|-----:|-------|
| DEFAULT | 1 | DefaultBillInquiryRequest |
| SIMPLE | 2 | SimpleBillInquiryRequest (deprecated) |
| INQUIRY_ID | 3 | CustomBillInquiryRequest |

**Pitfall:** DB `UtilityBillInquiryMethod` uses different ints (DEFAULT=0, SIMPLE=1, INQUIRY_ID=2). Do not mix when asserting Mongo documents.

### 7.4 Other enums

| Enum | Values |
|------|--------|
| BillInquiryProvider | FINNOTECH(0), GHABZINO(1), ENOVIN(2) |
| SettlementStatus | INITIATED(0), PENDING(1), FAILED(2), SUCCESS(3), UNKNOWN(4), NOT_FOUND(5) |
| SettlementProviderName | ENOVIN(0), POD(1), PARSIAN(2) |
| Operator | MCI(1), MTN(2), RIGHTEL(3) |
| TermType | MID_TERM(0), FINAL_TERM(1) |
| Type (admin) | BILL(0) |
| TransactionType for bills | UTILITY_BILL → **`2`** in recommendations/promotion/settings paths |

### 7.5 Agent header values (common)

`ANDROID`, `IOS`, `WEB`, `GATEWAY`, `APP_MEDIATOR`, `HYBRID_IOS`, `HYBRID_ANDROID`, …

---

## 8. Business rules (assert these)

Source: `BillServiceImpl` + validators + `application.properties`

| Rule | Value / behavior |
|------|------------------|
| Payable statuses | `PENDING`, `FAILED` |
| Verifiable status | `PAID` only |
| Duplicate block statuses | `CONFIRMED`, `PAID`, `ORDERED` |
| Duplicate window | last **60 days** (`bill.last.pay.days.before.today`) |
| Min amount | **10001** Rials (`bill.min.pay.amount`) |
| Ticket expiration | creation + **1h** (`utility.bill.expiration.hour`) |
| Wallet/DPG expiration extension | **120h** |
| Verify window | **10 min** before reverse |
| Verify retry | **2 min** |
| IPG inquiry max attempts | **5** then EXPIRED |
| MTN create payment | **blocked** → `BILL_MTN_OPERATOR_PAYMENT_NOT_SUPPORTED` |
| MTN init with flag | may **delegate to topup-mng** `/top-ups/init` |
| Inquiry duplicate | all terms paid → `BILL_DUPLICATE_FOUND`; mid-term can succeed if only final duplicated |
| Pending ownership | wrong User-Id → failure |
| HTTP verify API | **disabled** — verification is Rabbit async |
| Business errors HTTP | usually **422** |

### Status transition diagram

```
create ──────────────► PENDING
                         │
              pay ok     │     pay fail
                 ▼       │        ▼
               PAID ◄────┴──── FAILED (retry pay)
                 │
           verify ok │ verify fail (wallet, after window)
                 ▼              ▼
            CONFIRMED        REVERSED
                 │
           settle ok │ settle fail
                 ▼         ▼
             ORDERED    REJECTED → refund
```

Also: cancel → `CANCELED`; expire scheduler → `EXPIRED`.

---

## 9. ResultStatus / error catalog (negative automation)

Business exceptions map via `CustomizedResponseEntityExceptionHandler` (typically HTTP **422**).

### Core bill exceptions

| Exception | result.title |
|-----------|--------------|
| DuplicateBillException | `BILL_DUPLICATE_FOUND` |
| InvalidUtilityBillAmountException | `BILL_AMOUNT_INVALID` |
| InvalidUtilityBillException | `INVALID_UTILITY_BILL` |
| InvalidUtilityBillTypeException | `INVALID_UTILITY_BILL_TYPE` |
| InvalidUtilityBillParamException | `INVALID_UTILITY_BILL_PARAM` |
| InvalidCellNumberException | `INVALID_PARAMETER` |
| BillNotFoundException | `BILL_NOT_FOUND` |
| BillInCreditStateException | `BILL_ID_CREDIT_STATE` |
| InactiveBillTypeException | `BILL_TYPE_IS_INACTIVE` |
| PhoneNumberNotSupportedException | `BILL_PHONE_NUMBER_NOT_SUPPORTED` |
| UnsupportedMtnBillPaymentException | `BILL_MTN_OPERATOR_PAYMENT_NOT_SUPPORTED` |
| UnsupportedMtnBillOperatorException | `BILL_MTN_INQUIRY_OPERATOR_NOT_SUPPORTED` |
| UnsupportedMciBillOperatorException | `BILL_MCI_INQUIRY_OPERATOR_NOT_SUPPORTED` |
| PayByWalletNotSupportedException | `BILL_PAY_BY_WALLET_NOT_SUPPORTED` |
| MethodArgumentNotValidException | `INVALID_PARAMETER` |
| generic Exception | `FAILURE` |

### Wallet / PSP (from ITs + WalletMapper)

`WALLET_USER_NOT_FOUND`, `WALLET_GW_CREDIT_NOT_ENOUGH`, `WALLET_GW_TRANSACTION_DUPLICATE`, `PSPPROXY_ORDER_ID_DUPLICATE`, `PSPPROXY_BILL_DUPLICATE`, `PSPPROXY_BILLID_INVALID`, `PSPPROXY_PAYID_INVALID`

### Provider / infra

`SERVICE_PROVIDER_EXCEPTION`, `AUTHENTICATION_FAILURE`, `END_POINT_TIMEOUT`, `BAD_REQUEST`, `SUCCESS`, `FAILURE`

### Ghabzino-translated extras (provider layer)

`BILL_SERVICE_ERROR`, `BILL_INVALID_POST_PAY_NUMBER`, `BILL_INVALID_BILL_ID`, `BILL_INVALID_ELECTRICITY_BILL_ID`, `BILL_ELECTRICITY_BILL_ID_NOT_FOUND`, `BILL_INVALID_WATER_BILL_ID`, `BILL_WATER_BILL_ID_NOT_FOUND`, `BILL_INVALID_GAS_BILL_ID`, `BILL_INVALID_PAY_AMOUNT`, `BILL_UNAVAILABLE_ELECTRICITY_SERVICE`, `BILL_INVALID_TELEPHONE_NUMBER`, `BILL_GAS_SUBSCRIPTION_CODE_NOT_FOUND`, `BILL_PROCESSING_REQUEST`, `BILL_RESULT_NOT_FOUND`, `BILL_INVALID_BILL_TYPE_FOR_PAY`

---

## 10. RabbitMQ (async side effects)

From `queue.properties`:

| Queue / exchange | Role |
|------------------|------|
| `bill.verify` | After PAID → verify |
| `bill.settle` | After CONFIRMED → settle |
| `bill.recommendation` | Update recommendations |
| `bill.refund.reply` | Apply refund reply |
| `rfdmn.refund` | Publish refund request |
| `notif.sms` / `notif.push` | Notifications |
| `rep.activity.end.state` / `rep.activity.creation` | Reporting |
| `activity.event.exchange` | Fanout end-state |

Routing key for bill: `bill.rkey`.

**Automation implication:** E2E against real env needs eventual-consistency waits; ITs drive Rabbit via Testcontainers.

---

## 11. Mongo collections (DB assertions)

| Collection | Entity |
|------------|--------|
| `utility_bills` | UtilityBill |
| `bill_configs` | UtilityBillConfig |
| `bill_inquiry_configs` | BillInquiryConfig |
| `bill_inquiry_data` | UtilityBillInquiryData |
| `bill_inquiry_log` | BillInquiryLog |
| `utility_bill_recommendations` | BillRecommendation |
| `supported_bill_organizations` | SupportedBillOrganization |
| `refunds` | Refund |

Key fields on `UtilityBill`: `billId`, `payId`, `amount`, `feeCharge`, `type`, `status`, `ticket`, `trackingCode`, `inquiryId`, `inquiryMethod`, `debtor`, `creditor`, `payDetail`, `settlementAttempts`, `provider`, `expirationDate`, `payExpirationDate`.

---

## 12. Postman — how to import & run

### Files

1. Import **Collection:** `docs/sdet/postman/Bill-MNG-API.postman_collection.json`
2. Import **Environment:** `docs/sdet/postman/Bill-MNG-Local.postman_environment.json`
3. Select environment **Bill-MNG Local / Staging**
4. Set `baseUrl` to your target (local `http://localhost:7074/platform/api` or staging gateway URL)
5. If using real gateway, set `authToken` (Bearer)

### Collection design

| Folder | Contents |
|--------|----------|
| 01 Happy Path — Wallet Pay | config → inquiry → init → info → features → wallet → details → pending |
| 02 Inquiry Variants | validate, inquiryId, simple, cell MCI/MTN, suggestion, fixtures |
| 03 Ticket & Pay Channels | init variants, assign, DPG, IPG, search |
| 04 Negative Cases | empty payId, low amount, invalid bill, wrong user, wallet errors |
| 05 Recommendations & Promotion | CRUD + banner |
| 06 Admin | configs, distributions, stats, flush, settings toggle |
| 07 Cards | OTP |
| 08 Docs | OpenAPI / Swagger (staging) |

### Built-in scripts

**Collection pre-request:** upserts `User-Id`, `Agent`, `Platform-Version`, `Client-Id`, `X-Forwarded-For`, `Content-Type`; optional `Authorization` from `authToken`.

**Collection test:** accepts 2xx or 422; logs `result.title`; auto-saves `ticket` and `trackingCode` to environment.

### Environment variables

`baseUrl`, `userId`, `debtorUserId`, `agent`, `version`, `clientId`, `xff`, `billId`, `payId`, `callbackUrl`, `cellNumber`, `operator`, `ticket`, `trackingCode`, `inquiryId`, `billTypeApi`, `utilityBillTypeCode`, `recommendationType`, `recommendationId`, `authToken`, `businessId`

### Suggested Runner order (happy path)

Run folder **01 Happy Path** sequentially. After wallet pay, manually re-run **07 GET bills details** until ORDERED/CONFIRMED.

---

## 13. IT scenario catalog = first automation backlog

Reuse `@DisplayName` from these classes under `bill-mng/src/test/java/...`:

### BillInquiryResourceIT

| Scenario | Expect |
|----------|--------|
| mci duplicate billId/payId | `BILL_DUPLICATE_FOUND` |
| mci final duplicate, midterm new | `SUCCESS` |
| gas inquiryId duplicate | `BILL_DUPLICATE_FOUND` |
| default billId+payId | SUCCESS |
| invalid inquiryId | `BILL_NOT_FOUND` |
| irancell / driving penalty default | SUCCESS |
| type mismatch / invalid billId | `INVALID_UTILITY_BILL` |
| electricity/gas/water/telephone inquiryId | SUCCESS |
| mci invalid cell | `INVALID_PARAMETER` |
| mci/mtn cell success | `SUCCESS` |
| mci inactive type | `BILL_TYPE_IS_INACTIVE` |
| telephone credit state | `BILL_ID_CREDIT_STATE` |
| phone not supported | `BILL_PHONE_NUMBER_NOT_SUPPORTED` |
| gas subscription not found | `BILL_GAS_SUBSCRIPTION_CODE_NOT_FOUND` / `INVALID_UTILITY_BILL_PARAM` |
| undefined bill type | `INVALID_UTILITY_BILL_TYPE` |

### BillTicketResourceIT

empty payId → `INVALID_PARAMETER`; amount too low → `BILL_AMOUNT_INVALID`; duplicates → `BILL_DUPLICATE_FOUND`; web redirectUrl success; MTN→topup; ticket info; features list/assign.

### BillResourceIT

config; pending ownership / not found; wallet SUCCESS / insufficient / user not found / unsupported org / duplicate order.

### BillControllerIT

IPG callback → ORDERED / FAILED / stay PAID.

### Also

`BillAdminResourceIT`, `RecommendationResourceIT`, `PromotionBannerResourceIT`, `CardResourceIT`, `SettingAdminResourceIT`, settlement ITs.

**Base test harness:** `AbstractResourceIT` — Testcontainers Mongo+Redis+Rabbit+WireMock; `getHttpHeaders(userId)`; URL prefix `/platform/api`.

---

## 14. Concrete fixtures (from ITs / WireMock)

### Users

| Role | UUID |
|------|------|
| Primary userId | `2d04d8eb-e6fa-4b12-8dae-6d15b4d1fda0` |
| Debtor (pending) | `0beca23f-3bc5-4b49-adae-d4e47c1b720b` |
| Client-Id | `platform-client-id` |
| XFF | `192.168.1.1` |

### billId / payId

| billId | payId | Use |
|--------|-------|-----|
| 2664034900143 | 51450157 | telephone happy |
| 2664034900143 | 1099157 | amount too low |
| 4079157230158 | 113802204 | MCI multi-term |
| 236047406238 | 35005608 | gas |
| 2498463593553 | 6980594 | MTN inquiry |
| 5743219100290 | 80020296 | driving penalty |
| 9635001104126 | 176470327 | type mismatch |
| 0247506993356 | 61601150 | MTN → topup |
| 700880221142 | 1881238 | ticket info |

### Cells

| cell | Use |
|------|-----|
| 09177171472 | MCI success |
| 0917717147 | invalid length |
| 09037083670 | MTN bill |
| 09332475069 | MTN debt |

### Tickets (WireMock wallet)

| ticket | Expect |
|--------|--------|
| 4d8ab90e5ed949a0a0353157cd97dca93 | wallet success |
| 88fsfs4k5e4953sfs453uir444483 | insufficient |
| 4d8ab90e5ed949a0a035315704956049560493 | user not found |
| 34895id03854k5e495349879e3uir735j893 | duplicate order |

> Against **real staging**, generate tickets via `/bills/init` — do not rely on WireMock ticket strings.

---

## 15. Suggested automation suite structure

```
bill-api-tests/
  contracts/          ← copy or depend on bill-mng-spec JAR
  fixtures/           ← billId/payId/cells from §14
  clients/BillClient  ← headers filter like AbstractResourceIT
  scenarios/
    happy/WalletPayE2E
    inquiry/DefaultInquiry
    inquiry/InquiryId
    inquiry/CellNumber
    negative/AmountInvalid
    negative/Duplicate
    negative/PendingWrongUser
    admin/ConfigUpdate
    recommendation/Crud
  assertions/
    ResultStatusAssert
    BillStatusAssert (poll until)
```

### Assertion helpers to implement

```text
assertResult(response, "SUCCESS")
assertResult(response, "BILL_DUPLICATE_FOUND")
assertHttp(response, 422)
pollBillDetails(trackingCode, timeout) until status in {CONFIRMED, ORDERED}
assertPayable(status in PENDING|FAILED)
```

### Suggested suite additions (provider weight / admin)

```
scenarios/admin/
  GetInquiryConfigsShape
  PutPerTypeWeights_Restore
  PutActiveDisable_BillTypeInactive
  PutEmptyDistributions_Failure
```

### What NOT to automate here

- Pixel/UI flows → Platform Android/iOS/Web repos (deep links `/bill/confirm`, `/mobilebill/confirm`)
- Provider OAuth secrets rotation → ops
- Prod Swagger (disabled)
- Dashboard **History / app version** APIs (not bill-mng)
- Blind `PUT /admin/bills/configs` (global) on shared UAT without restore

---

## 16. How to run the service / tests locally

| Item | Detail |
|------|--------|
| Profiles | `local` (default Maven), `staging`, `prod`, `test` |
| Run app | `./mvnw -pl bill-mng spring-boot:run` (needs Platform Nexus + Mongo/Redis/Rabbit) |
| Run ITs | Surefire includes `*Test` and `*IT`; needs Docker for Testcontainers |
| Local management port | `17074` (`application-local.properties`) |
| Docker-compose | **None** in repo |
| Staging OpenAPI | `/platform/api/v3/api-docs`, Swagger UI (profile staging) |
| Prod OpenAPI | disabled |

---

## 17. Critical SDET pitfalls checklist

- [ ] Header is **`Platform-Version`**, not `Version`
- [ ] Admin path type codes ≠ API BillType ints (PUT `configs/1` vs GET `type: 4` for WATER)
- [ ] Request `payMethod` ints ≠ DB inquiry method ints
- [ ] Min amount is **10001**, not 10000
- [ ] Verify REST is **off**; wait for async Rabbit
- [ ] MTN payment create blocked; init may go to topup
- [ ] Duplicate window 60 days + statuses CONFIRMED/PAID/ORDERED
- [ ] Pending requires matching debtor User-Id
- [ ] Business errors → HTTP **422** + `result.title`
- [ ] Fixtures from WireMock ITs may not work on real staging without matching provider data
- [ ] Provider weights: Mongo (billId/payId) vs properties (cellNumber) — two systems
- [ ] `PUT /admin/bills/configs` (no type) overwrites **all** types — dangerous on shared UAT
- [ ] `totalInquiryDistributions` is **not** an aggregate sum (see §20)
- [ ] Dashboard **History** API is **not** bill-mng (app versions)

---

## 18. Source file index (deep links inside cloned repo)

| Concern | Path |
|---------|------|
| Parent POM | `pom.xml` |
| Spec DTOs | `bill-mng-spec/src/main/java/com/platform/billcoordinator/spec/` |
| Inquiry API | `bill-mng/.../api/web/bill/BillInquiryResource.java` |
| Bill API | `bill-mng/.../api/web/bill/BillResource.java` |
| Ticket API | `bill-mng/.../api/web/bill/BillTicketResource.java` |
| Admin config | `bill-mng/.../api/web/bill/BillAdminResource.java` |
| Provider weight select | `bill-mng/.../inquiry/impl/WeightedRandomBillInquiryProviderSelectionStrategy.java` |
| Admin config service | `bill-mng/.../config/impl/BillConfigServiceImpl.java` |
| Domain service | `bill-mng/.../service/bill/base/impl/BillServiceImpl.java` |
| Exception handler | `bill-mng/.../api/web/CustomizedResponseEntityExceptionHandler.java` |
| Headers interceptor | `bill-mng/.../api/web/filter/RequestContextInterceptor.java` |
| Queues | `bill-mng/src/main/resources/queue.properties` |
| App props | `bill-mng/src/main/resources/application.properties` |
| Payment paths | `bill-mng/src/main/resources/payment.properties` |
| IT base | `bill-mng/src/test/java/.../AbstractResourceIT.java` |
| WireMock | `bill-mng/src/test/resources/*/mappings/` |
| Roles SQL | `deployment/user-mng-roles-*.sql` (if present under deployment) |

---

## 19. Prompt snippet for your automation AI agent

Copy this when asking an agent to write scenarios:

```text
You are an SDET. Use docs/sdet/BILL_AUTOMATION_GUIDANCE_BOOK.md as the only
source of truth for Platform bill-mng API automation.

Write API automation scenarios for:
1) Happy path wallet pay (poll until ORDERED)
2) Negative: BILL_AMOUNT_INVALID, BILL_DUPLICATE_FOUND, INVALID_PARAMETER, pending wrong user
3) Inquiry variants: default, payMethod=3, cellNumber operator=1/2
4) Admin provider weights (§20): GET /admin/bills/configs assert
   inquiryDistributions + totalInquiryDistributions; PUT per-type 80/20
   Ghabzino/Finnotech; PUT active true/false; NEVER run global PUT
   on shared UAT without restore; empty distributions → FAILURE

Rules:
- Base URL {{baseUrl}}/… under /platform/api
- Headers: User-Id, Agent, Platform-Version, Client-Id, X-Forwarded-For
- Assert result.title and HTTP 422 for business errors
- Do not assume sync settle; poll details
- Use enums and fixtures from the guidance book
- Prefer bill-mng-spec types if framework is Java
- Provider: 0=FINNOTECH 1=GHABZINO 2=ENOVIN; weights drive inquiry routing
```

---

## 20. Provider weight & admin inquiry distribution (deep dive)

> Matches Platform admin UI **پرداخت قبض → تنظیم تقسیم سرویس** (e.g. فیبونک/Finnotech **20%**, قبضینو/Ghabzino **80%**).

### 20.1 Two different “config” models (do not mix)

| Model | Collection / API | Controls |
|-------|------------------|----------|
| **BillInquiryConfig** | Mongo + `GET/PUT /admin/bills/configs*` | **Who handles inquiry** (provider weights per bill type) |
| **UtilityBillConfig** | Mongo + same `PUT .../configs/{type}` with `active` | **Is bill type shown/enabled** in app (`GET /bills/config`), badges when disabled |

Same admin resource updates both depending on request fields (`inquiryDistributions` and/or `active` + `disableMessage`).

### 20.2 Provider enum ↔ UI labels

| JSON `provider` | Spec enum | UI (Persian admin) | Role |
|----------------:|-----------|--------------------|------|
| **0** | `FINNOTECH` | فیبونک / فیبانتک | Inquiry provider |
| **1** | `GHABZINO` | قبضینو | Inquiry provider |
| **2** | `ENOVIN` | Enovin | Inquiry provider (when configured) |

Weights are relative (EnumeratedDistribution). Example: `80` + `20` ⇒ ~80% / ~20% chance per inquiry. They do **not** need to sum to 100, but admin UI usually uses percentages that sum to 100.

### 20.3 GET `/admin/bills/configs` — response contract

```json
{
  "result": { "title": "SUCCESS", "status": 0, "message": "...", "level": "INFO" },
  "configs": [
    {
      "type": 5,
      "inquiryDistributions": [
        { "provider": 1, "weight": 80.0 },
        { "provider": 0, "weight": 20.0 }
      ]
    }
  ],
  "totalInquiryDistributions": [
    { "provider": 1, "weight": 80.0 },
    { "provider": 0, "weight": 20.0 }
  ]
}
```

| Field | Meaning for automation |
|-------|------------------------|
| `configs[].type` | **API `BillType` int** (WATER=4, ELECTRICITY=5, GAS=6, TELEPHONE=7, MUNICIPALITY=8, TAX=9, DRIVING_PENALTY=10, MCI=11, MTN=12, RIGHTEL=13) |
| `configs[].inquiryDistributions` | Weights used when inquiring that bill type (billId/payId / inquiryId path) |
| `totalInquiryDistributions` | **Not a true aggregate.** Implementation copies distributions from **`configs[0]` only** (`BillAdminResourceMapper`). Treat as UI convenience; assert per-type `configs[]` for truth. |

### 20.4 PUT contracts

**A) Update weights for ONE type** — `PUT /admin/bills/configs/{type}`

Path `{type}` = **UtilityBillType code string** (WATER=`"1"`, ELECTRICITY=`"2"`, GAS=`"3"`, …) — **not** API BillType `4/5/6`.

```json
{
  "inquiryDistributions": [
    { "provider": 1, "weight": 80.0 },
    { "provider": 0, "weight": 20.0 }
  ]
}
```

IT: empty `inquiryDistributions` → **HTTP 422** / `FAILURE`.

**B) Update weights for ALL types** — `PUT /admin/bills/configs`

```json
{
  "inquiryDistributions": [
    { "provider": 1, "weight": 80.0 },
    { "provider": 0, "weight": 20.0 }
  ]
}
```

`BillConfigServiceImpl.updateBillInquiryConfig` sets the **same list on every** `BillInquiryConfig`. Use carefully on shared UAT; restore previous values after test.

**C) Enable / disable bill type (app menu)** — `PUT /admin/bills/configs/{type}`

```json
{ "active": true, "disableMessage": null }
```

```json
{ "active": false, "disableMessage": "این سرویس موقتا غیرفعال است" }
```

- `active: true` → clears badge  
- `active: false` → sets badge message from `disableMessage`  
- Inactive type → inquiry may return `BILL_TYPE_IS_INACTIVE`

You can send **both** `active` and `inquiryDistributions` in one PUT `{type}` body.

### 20.5 How weights are used at runtime

Class: `WeightedRandomBillInquiryProviderSelectionStrategy`

| Inquiry path | Weight source |
|--------------|---------------|
| Default / inquiryId for **non-mobile** (and most billId+payId) | Mongo `BillInquiryConfig` for that `UtilityBillType` → weighted random |
| **Mobile + inquiryId** (MCI/MTN types) | **Properties**, not Mongo: `*.cellNumber.inquiry.provider.weight` |
| Cell-number inquiry `GET /bills/inquiry/{cell}` | Same property-based cellNumber weights by `Operator` |

Default properties (`application.properties` examples):

```properties
mci.enovin.cellNumber.inquiry.provider.weight=100
mci.finnotech.cellNumber.inquiry.provider.weight=0
mtn.ghabzino.cellNumber.inquiry.provider.weight=100
```

So: changing admin UI sliders **does not** change MCI/MTN **cellNumber** provider split unless ops change properties / deploy config.

### 20.6 Settlement provider weights (separate from inquiry)

Wallet **settlement** after pay uses another weighted strategy + properties:

```properties
pod.bill.payment.provider.weight=100.0
enovin.bill.payment.provider.weight=0.0
parsian.bill.payment.provider.weight=0.0
```

Enum: `SettlementProviderName` POD(1) / ENOVIN(0) / PARSIAN(2).  
**Not** exposed on `/admin/bills/configs` — do not confuse with inquiry distribution UI.

### 20.7 Automation scenarios (provider weight)

| # | Scenario | Steps / assert |
|---|----------|----------------|
| W1 | GET configs shape | `result.title=SUCCESS`; each `configs[]` has `type` + non-empty `inquiryDistributions`; providers ∈ {0,1,2}; weights ≥ 0 |
| W2 | UI parity sample | For a type (e.g. ELECTRICITY `type=5`), assert Ghabzino=80 & Finnotech=20 (or current UAT values) |
| W3 | PUT per-type | Save old weights → PUT `configs/2` (ELECTRICITY code) with 100% Ghabzino → GET assert only that type → restore |
| W4 | PUT global | Optional isolated env only: PUT `/admin/bills/configs` → all types same weights → restore all |
| W5 | Empty distributions | PUT `{type}` with `inquiryDistributions: []` → `FAILURE` / 422 |
| W6 | Disable type | PUT `active:false` + message → `GET /bills/config` hides/inactive → inquiry → `BILL_TYPE_IS_INACTIVE` → re-enable |
| W7 | Statistical (optional) | Set 100/0 → N inquiries → provider side-effect / logs / stubs always same provider (flaky if 80/20) |

**Safe pattern on shared UAT:** always GET → clone → PUT change → assert → PUT restore.

### 20.8 NOT bill-mng — dashboard History API

Admin Network tab often shows `/history` next to `/configs`. History payload (`versions`, `clientVersion`, `osName`, `forceUpdate`, `latestVersionsLabels`) is **app release / force-update**, **not** bill provider config. Do **not** add it to the bill-mng Postman collection or bill automation suite.

### 20.9 Source files

| Concern | Path |
|---------|------|
| Admin API | `api/web/bill/BillAdminResource.java` |
| Response mapper (`totalInquiryDistributions`) | `api/web/bill/mapper/BillAdminResourceMapper.java` |
| Config service | `service/bill/config/impl/BillConfigServiceImpl.java` |
| Weighted inquiry select | `service/bill/inquiry/impl/WeightedRandomBillInquiryProviderSelectionStrategy.java` |
| Settlement weights | `service/settlement/impl/WeightedRandomSettlementProviderSelectionStrategy.java` |
| IT | `BillAdminResourceIT.java` |
| DTOs | `BillInquiryConfigResponse`, `BillInquiryConfigDto`, `BillInquiryDistributionDto`, `BillConfigUpdateRequest` |

---

## 21. Test data strategy — fake bills vs real bills (deep dive)

> SDET question: *Do I need real `billId` / `payId` / شناسه قبض for inquiry automation, or can I fake them?*  
> Answer: **it depends which layer you test.** There is no single “fake bill factory” that works for full UAT inquiry+pay against live providers.

### 21.1 What “a bill” means in Platform

Iranian utility identifiers are not random strings. Platform encodes rules in `BillUtils`:

| Concept | Rule in code |
|---------|----------------|
| Length | UI + API: **6–13** digits (`@Size` on DTOs / UI hint) |
| `billId` check digit | Last digit = checksum over previous digits |
| `payId` check digits | Internal check digit + match check with `billId` |
| Amount from `payId` | `fetchAmountFromPayId`: strip last 5 chars, append `000` (Rials) |
| Type from `billId` | Digit before last check digit = utility code (`1` water, `2` elec, … `5` mobile + operator prefix) |
| Mobile from cell | `cellNumberToBillId` / `cellNumberToPaymentId` can **synthesize** checksum-valid IDs |

So there are **three gates** before a happy inquiry succeeds:

```
1) Client/UI length & format
2) Platform BillUtils checksum + type + min amount (10001)
3) External provider (Finnotech / Ghabzino / Enovin) must KNOW the bill and return debt
```

**Checksum-valid ≠ provider-valid.**  
You can generate IDs that pass gate 1–2 and still get `BILL_NOT_FOUND` / provider errors at gate 3.

### 21.2 UI flows ↔ data you need

| UI (Persian) | User enters | API shape | Provider looks up by |
|--------------|-------------|-----------|----------------------|
| پرداخت با شناسه | شناسه قبض + شناسه پرداخت | default inquiry `billId`+`payId` | Combined bill/pay id |
| استعلام بدهی (e.g. قبض آب) | شناسه قبض only | `payMethod:3` + `type` + `inquiryId` | Subscription / bill id |
| Mobile cell inquiry | phone (+ operator) | `GET /bills/inquiry/{cell}?operator=` | Cell → provider |

### 21.3 Option matrix (all options)

| Option | What you use | Passes Platform validation? | Passes live provider? | Good for pay E2E? | Stability | Cost / effort |
|--------|--------------|----------------------------|-----------------------|-------------------|-----------|---------------|
| **A. Synthetic invalid** | Wrong length, empty, bad checksum | Fail on purpose | N/A | No | Excellent | Free |
| **B. Checksum-valid synthetic** | Generate via `BillUtils` rules / custom generator | Yes | Usually **No** | No | Excellent | Low |
| **C. WireMock / IT fixtures** | Fixed IDs from `*IT` + stubbed providers | Yes (in test) | N/A (mocked) | Yes (mocked wallet too) | Excellent | Medium once |
| **D. Staging mock / stub env** | Same as C but shared “test stack” | Yes | Stubbed | Yes in that env | High | Needs platform |
| **E. Curated UAT bill pool** | Real/staging bills from QA/ops | Yes | Yes (until paid/expired) | Yes if unpaid | Medium (rotates) | Needs process |
| **F. Production-like unpaid bills** | Real customer-like data | Yes | Yes | Risky | Low | Avoid |
| **G. Cell-based mobile** | Real/test MSISDNs | Format yes | If operator test lines exist | Special (MTN rules) | Medium | Needs telco data |
| **H. Inquiry-suggestion / history** | User’s past `ORDERED` bills | N/A | Reuses past ids | Re-inquiry may duplicate | Medium | Needs seeded user |
| **I. DB seed only** | Insert `utility_bills` in Mongo | Skips inquiry | Breaks real flow | Partial (pay only) | Low for E2E | Not for full flow |

---

### 21.4 Option A — Synthetic **invalid** data (always do this)

**Goal:** UI + API validation, no provider call needed (or fail before provider).

Examples:
- Length 5 / 14 → UI disabled or `INVALID_UTILITY_BILL` / `INVALID_PARAMETER`
- Empty `payId` on init → `INVALID_PARAMETER`
- Valid-looking length but broken checksum → `INVALID_UTILITY_BILL`
- `type` mismatch vs billId-derived type → `INVALID_UTILITY_BILL`
- Amount encoded in payId &lt; 10001 → `BILL_AMOUNT_INVALID` on init

**Pros:** Free, stable, parallelizable, no secrets.  
**Cons:** Does not prove inquiry/pay happy path.  
**Verdict:** Mandatory baseline suite (~30–40% of bill scenarios).

---

### 21.5 Option B — Checksum-valid **fake** IDs (local Platform only)

**Idea:** Implement a small generator mirroring `BillUtils` (check digit algorithm + amount encoding in payId + type digit).  
`BillUtils.cellNumberToBillId` / `cellNumberToPaymentId` already show Platform can synthesize mobile-style IDs.

**Tool in this pack:** `scripts/bill_mng/fake_bill_generator.py` (see §21.5.1).

**What you can test:**
- Validators accept the payload
- Wrong type detection
- Min amount from payId
- Maybe reach Feign call → provider error mapping (`BILL_NOT_FOUND`, `SERVICE_PROVIDER_EXCEPTION`, …)

**What you cannot reliably test on live UAT:**
- Successful inquiry with real `amount` / mid-term / final-term
- Full pay → ORDERED (provider + settlement need a real debt)

**Pros:** Good for negative provider mapping; no dependency on unpaid bills.  
**Cons:** Easy to confuse with “working fake bills” — they are **not**.  
**Verdict:** Useful for “invalid at provider” and unit/contract of validators; **not** for happy-path UAT.

#### 21.5.1 How Platform “fakes” work (algorithm)

Iranian utility IDs use a **mod-11 style check digit** (implemented in `BillUtils.getUtilityBillCheckDigit`):

```
from right to left, multiply digits by 2,3,4,5,6,7,2,3,... 
sum % 11 → if 0 or 1 then check=0 else check=11-mod
```

**billId structure**

```
[ account digits ][ type code 1 digit ][ check digit 1 ]
```

| Type | type code in billId |
|------|---------------------|
| WATER | `1` |
| ELECTRICITY | `2` |
| GAS | `3` |
| TELEPHONE | `4` |
| mobile | `5` (+ 3-digit operator prefix before it) |
| MUNICIPALITY | `6` |
| TAX | `8` |
| DRIVING_PENALTY | `9` |

Example: `…1` + check → water-typed billId (second-to-last digit is type).

**payId structure** (same idea as `cellNumberToPaymentId`)

```
[ amount_prefix ][ period 3 digits e.g. 011 ][ pay-check ][ match-check ]
```

- Platform recovers amount as: `payId without last 5 chars` + `"000"`  
  e.g. payId `1501180` → amount `15000`
- Last-but-one digit validates payId body; last digit validates `billId+payIdBody` together

**Known valid pairs from unit tests** (`ValidateUtilityBillTest`):

| billId | payId | valid |
|--------|-------|-------|
| 6535478830150 | 109572658 | true |
| 9635001104126 | 86970272 | true |
| 465310600140 | 9070306 | true |
| 9635001104126 | 109572658 | false (mismatch) |

**Generator examples**

```bash
# samples
python3 scripts/bill_mng/fake_bill_generator.py --samples

# one water bill with amount 25000 Rials
python3 scripts/bill_mng/fake_bill_generator.py --type WATER --amount 25000 --account 12345678901

# validate any pair
python3 scripts/bill_mng/fake_bill_generator.py --validate 1234567890117 1501180

# mobile-style from cell
python3 scripts/bill_mng/fake_bill_generator.py --mobile 09121234567 --amount 15000
```

Example output (checksum-valid, **not** a live debt):

```json
{
  "type": "WATER",
  "billId": "1234567890117",
  "payId": "2501194",
  "amountFromPayId": 25000,
  "validForPlatform": true,
  "validForLiveProvider": "UNKNOWN — almost always NO without stub",
  "inquiryBody": { "billId": "1234567890117", "payId": "2501194" }
}
```

#### 21.5.2 What happens if you POST a fake to UAT

```
POST /bills/inquiry { fake billId, fake payId }
  → Platform validation OK
  → Feign to Ghabzino/Finnotech/Enovin (by weight)
  → provider does not know bill
  → typically BILL_NOT_FOUND / INVALID_* / SERVICE_PROVIDER_EXCEPTION / FAILURE
```

So fakes are perfect for:
- “validation passed, provider failed” mapping tests  
- UI enabling the استعلام button (6–13 + maybe client-side checks)  
- Contract tests **with WireMock** returning SUCCESS for that generated pair  

Not for:
- Demo to PO of a real debt amount  
- Pay → ORDERED on real UAT without a stub

#### 21.5.3 Two meanings of “create fake bill”

| Meaning | How | Result |
|---------|-----|--------|
| **1. Fake identifiers** | Generator / `BillUtils` | Platform accepts format |
| **2. Fake provider debt** | WireMock / sandbox stub that returns amount for that id | Full inquiry SUCCESS in test env |
| **3. Fake Mongo bill row** | Insert `utility_bills` PENDING | Skip inquiry; only test later pay steps |

SDETs usually need **(1)+(2)** together for CI happy path — not (1) alone on live UAT.

---

### 21.6 Option C — WireMock / in-repo IT fixtures (best for CI)

**How bill-mng itself tests:** Testcontainers + WireMock mappings under `src/test/resources/{finnotech,ghabzino,...}/mappings/` with **fixed** billId/payId/cell values.

Examples (from §14):
- `2664034900143` / `51450157` — telephone happy
- `4079157230158` / `113802204` — MCI multi-term
- `236047406238` / `35005608` — gas  
- cells `09177171472`, `09037083670`

**Pros:** Deterministic SUCCESS/error; wallet/IPG stubs; no real money; matches DEV tests.  
**Cons:** Not the same as live UAT providers; stubs can drift from real provider contracts.  
**Verdict:** **Primary strategy for automation framework CI.** Port fixtures + stub contracts, or run against a mock gateway.

#### 21.6.1 What is WireMock?

**WireMock** is an HTTP **stub / mock server**. Instead of calling the real Ghabzino / Finnotech / wallet APIs on the internet, your test points Platform’s Feign clients at a local WireMock process that returns **pre-recorded JSON**.

Think of it as a “fake Ghabzino” sitting on `localhost:5053` that only knows the bill IDs you taught it.

| Without WireMock (UAT) | With WireMock (CI / ITs) |
|------------------------|---------------------------|
| bill-mng → real Ghabzino | bill-mng → WireMock |
| Need real unpaid bill | Need matching stub + ID |
| Flaky / paid / outages | Always same response |
| Hard to force errors | Return any error code on demand |

bill-mng enables it in ITs via:

```java
@EnableContainers(images = { ImageType.Mongo, ImageType.Redis, ImageType.Rabbit, ImageType.Wiremock })
```

Stub files live under e.g. `bill-mng/src/test/resources/ghabzino/mappings/*.json`.

#### 21.6.2 Anatomy of one stub (real example)

File: `ghabzino/mappings/webservices_coresvc_waterbillinquiry-….json`

```json
{
  "request": {
    "url": "/WaterBillInquiry",
    "method": "POST",
    "bodyPatterns": [{
      "equalToJson": "{\"Identity\":{...},\"Parameters\":{\"WaterBillID\":\"2029334804610\"}}"
    }]
  },
  "response": {
    "status": 200,
    "body": "{ \"Parameters\": { \"Amount\": 200000, \"BillID\": \"2029334804610\", \"PaymentID\": \"0000020080680\", ... }, \"Status\": { \"Code\": \"G00000\" } }"
  }
}
```

| Part | Meaning |
|------|---------|
| `request.url` | Path Platform Feign calls on the fake host |
| `bodyPatterns` | Only match when inquiry uses this WaterBillID |
| `response.body` | Fake debt Platform will map into `BillInquiryResponse` |
| `Status.Code G00000` | Ghabzino success (other codes → mapped errors in `GhabzinoInterceptorImpl`) |

So this stub says: *“If someone asks about water bill `2029334804610`, answer amount 200000.”*

#### 21.6.3 Full flow: fake bill + WireMock (expanded)

```text
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│ Robot/Postman│────▶│   bill-mng   │────▶│    WireMock     │     │ Real Ghabzino│
│  /bills/inquiry   │  (Feign)     │     │ fake provider   │     │  (NOT called)│
└─────────────┘     └──────────────┘     └─────────────────┘     └──────────────┘
        │                   │                      │
        │  billId/payId     │  POST /WaterBill…    │
        │  (fixture or      │  WaterBillID=…       │  canned JSON
        │   generator+stub) │─────────────────────▶│  Amount=200000
        │                   │◀─────────────────────│
        │  BillInquiryResponse SUCCESS             │
        │◀──────────────────│                      │
```

**Step-by-step (water inquiryId example used in IT stub):**

1. **Prepare data** — use fixture `inquiryId=2029334804610` (or generate checksum-valid ID **and** add a matching WireMock mapping).
2. **Start stack** — Mongo + Redis + Rabbit + WireMock (Testcontainers in ITs; or docker-compose in your framework).
3. **Point Feign** — `platform.client.ghabzino.baseUrl` (etc.) → `http://localhost:<wiremock-port>`.
4. **Call Platform** — `POST /platform/api/bills/inquiry` with your body.
5. **bill-mng** validates checksum/type → picks provider by weight → HTTP to WireMock.
6. **WireMock** matches request → returns fixed Amount / PaymentID / Status.
7. **bill-mng** maps to `billInfos[]` → your test asserts `result.title=SUCCESS` and amount.
8. For **pay**, same idea: stubs under `wallet-mng/`, `wallet-provider/`, `switchpsp/` return wallet/IPG success.

**Pairing with the fake generator:**

```text
A) Use existing stub IDs only          ← easiest (copy from §14 / mappings)
B) Generate new ID + write new stub    ← flexible, more maintenance
C) Record mode (commented in props)    ← capture real traffic once into stubs
```

Example comment in `ghabzino/test.properties`:
`#test.wiremock.record=https://bill.demo-platform.com/ayantech`

#### 21.6.4 What WireMock replaces in bill-mng tests

| Folder under `src/test/resources/` | Fakes |
|------------------------------------|-------|
| `ghabzino/mappings` | Water/Gas/Elec/Phone/MTN inquiry |
| `finnotech/mappings` | Billing inquiry + OAuth token |
| `enovin/mappings` | Bill inquiry / settlement |
| `wallet-mng`, `wallet-provider` | Wallet pay / balance |
| `switchpsp` | IPG/DPG / OTP |
| `uaa`, `user-mng`, `topup-mng` | Auth ticket, user, MTN topup bridge |
| `parsian` | Settlement |

Happy-path CI often needs **several** stubs in one scenario (inquiry + wallet + verify).

#### 21.6.5 WireMock vs your Postman on UAT

| | Postman → `example.com` | IT / Robot → local bill-mng + WireMock |
|--|-------------------------------|----------------------------------------|
| Providers | Real | Fake |
| Need real unpaid bill? | Yes | No (only stubbed IDs) |
| Auth | Gateway token | Often headers only |
| Best for | Smoke / exploratory | Regression CI |

**You cannot “turn on WireMock” inside Postman against UAT** unless ops puts a stub gateway in front. WireMock runs **beside** bill-mng in a test environment.

#### 21.6.6 How SDET frameworks usually adopt this

1. **Reuse bill-mng stubs** — copy `mappings/` JSON into your repo; run WireMock standalone Docker; point a local/staging bill-mng (or a test double) at it.  
2. **Contract tests only** — assert request/response shapes against stubs without full Spring Boot.  
3. **Hybrid** — CI = WireMock; nightly = small UAT pool (Option E).

Standalone WireMock idea:

```bash
# conceptual — ports/paths must match your Feign config
docker run -p 5053:8080 \
  -v $PWD/ghabzino/mappings:/home/wiremock/mappings \
  wiremock/wiremock:3.3.1
```

Then set Ghabzino base URL to `http://localhost:5053` for that test profile.

---

### 21.7 Option D — Shared staging stub / “bill sandbox”

Same idea as C, but ops runs a **persistent mock** (WireMock/Hoverfly/fake Ghabzino) in front of UAT bill-mng, or a special profile where Feign points to stubs.

**Pros:** Whole team shares one fake catalog; Postman + Robot can hit “UAT-like” URLs.  
**Cons:** Needs platform investment; must be maintained when provider APIs change.  
**Verdict:** Ideal mid-term if Platform QA owns a sandbox; ask if one already exists.

---

### 21.8 Option E — Curated **UAT/staging bill pool** (best for real E2E)

**How it works:**
1. QA/ops maintains a spreadsheet/vault of approved test bills per type:

```text
type | mode | billId | payId | inquiryId | cell | notes | lastPaidAt | owner
WATER | default | ... | ... | | | unpaid staging | | @qa
WATER | inquiryId | | | 2029... | | mid-term | |
GAS | default | ... | ... | | | | |
```

2. Automation reads from env/secret manager (not git).
3. After successful **pay**, mark bill as consumed or wait **60 days** / get a new payId (duplicate rules: statuses CONFIRMED/PAID/ORDERED).
4. Prefer bills that stay in **debt** or have refreshable mid-term.

**Pros:** True confidence on provider + Platform integration.  
**Cons:** Flaky if someone pays the bill; amounts change; provider outages.  
**Operational rules:**
- Never use random production customer bills
- One suite mutex / lock per bill id to avoid parallel steal
- Separate “inquiry-only” bills vs “pay-allowed” bills
- Alert when `BILL_DUPLICATE_FOUND` or amount 0

**Verdict:** Required for a small **smoke E2E** set (e.g. 1–2 types), not for hundreds of cases nightly.

---

### 21.9 Option F — Production / real customer bills

**Avoid** for automation:
- Legal/privacy risk
- Paying or locking real debts
- Unstable amounts / already paid

Manual exploratory only with explicit approval — not in CI.

---

### 21.10 Option G — Mobile cell numbers

- Format validated; MCI/MTN/Rightel via `operator` or billId prefix.
- MTN **payment create** blocked; init may go to **topup** when flag enabled.
- CellNumber provider weights come from **properties**, not admin sliders.
- Need **test MSISDNs** from telco/staging — random phones fail like fake bills.

---

### 21.11 Option H — Reuse recommendation / suggestion history

After a user has `ORDERED` bills, `POST /bills/inquiry-suggestion` and recommendations return past identifiers.

**Pros:** Good for “saved bill” UX / recommendation tests.  
**Cons:** Re-inquiry of same billId+payId may hit **duplicate** if still in window; not a source of infinite fresh debts.

---

### 21.12 Option I — Seed Mongo `utility_bills` only

Inserting PENDING bills skips real inquiry. Useful for isolated **pay/verify** unit tests inside bill-mng ITs — **not** for “user enters شناسه and gets debt” E2E.

---

### 21.13 Recommended pyramid for Platform bill automation

```text
                    /\
                   / E2E UAT \     ← few cases, Option E pool (pay optional)
                  /-----------\
                 / Stubbed API \   ← main volume, Option C/D
                /---------------\
               / Validation only \ ← Option A (+ B for checksum)
              /-------------------\
```

| Suite | % of cases | Data |
|-------|------------|------|
| Validation / negative | ~40% | Option A |
| Contract happy + errors | ~45% | Option C/D fixtures |
| UAT smoke inquiry | ~10% | Option E inquiry-only |
| UAT smoke pay | ~5% | Option E pay-allowed + test wallet |

### 21.14 Practical playbook for your Robot framework

1. **Tag tests:** `@validation` `@contract` `@uat-inquiry` `@uat-pay`
2. **Data files:**
   - `data/invalid_bills.yaml` — Option A
   - `data/wiremock_fixtures.yaml` — copy from §14
   - `secrets/uat_bills.yaml` (gitignored) — Option E
3. **Before UAT inquiry:** assert amount &gt; 0 and not duplicate; else skip + alert
4. **After UAT pay:** mark bill consumed; don’t reuse until new payId
5. **Ask DEV/QA once:**
   - Is there a staging provider sandbox?
   - Who owns the bill pool?
   - Can we get water `inquiryId` + default billId/payId pairs that stay unpaid?

### 21.15 Direct answers

| Question | Answer |
|----------|--------|
| Can I create fake bills for testing? | **Yes for validation & mocked providers.** **No for live provider happy-path** (unless sandbox). |
| Do I need real bill info? | For **UAT inquiry SUCCESS** and **pay** — yes, curated staging bills. |
| Can Platform generate IDs? | Checksum-valid yes (`BillUtils`); provider acceptance no. |
| Best default? | **Mock/WireMock fixtures for CI** + **small UAT pool for smoke**. |
| UI 6–13 hint? | Necessary but not sufficient — checksum + provider still apply. |

---

*Generated from deep analysis of the bill-mng codebase for SDET onboarding. Keep this file next to your automation suite and update when contracts change (diff against `bill-mng-spec` + `*Resource.java` + `*IT.java`).*
