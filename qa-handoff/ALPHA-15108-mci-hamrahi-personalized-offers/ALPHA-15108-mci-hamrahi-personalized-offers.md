---
ticket: ALPHA-15108
branch: n/a — manual feature-scope run
last_updated: 2026-09-06
last_commit_range: n/a — manual feature-scope search
last_scope_definition: keywords: none; paths: the 29 files changed on feat/ALPHA-15108-hamrahi-client-implementation versus origin/staging
touched_files:
  - topup-mng/src/main/java/com/platform/topupmng/api/web/bundle/BundleResource.java
  - topup-mng/src/main/java/com/platform/topupmng/api/web/bundle/mapper/BundleResourceMapper.java
  - topup-mng/src/main/java/com/platform/topupmng/client/behsa/BehsaClient.java
  - topup-mng/src/main/java/com/platform/topupmng/client/behsa/model/constant/BehsaBizType.java
  - topup-mng/src/main/java/com/platform/topupmng/client/behsa/model/constant/BehsaIsFree.java
  - topup-mng/src/main/java/com/platform/topupmng/client/behsa/model/request/BehsaGetHamrahiPackageInfoV1Request.java
  - topup-mng/src/main/java/com/platform/topupmng/client/behsa/model/response/BehsaBaseResponse.java
  - topup-mng/src/main/java/com/platform/topupmng/client/behsa/model/response/BehsaHamrahiPackageListResponse.java
  - topup-mng/src/main/java/com/platform/topupmng/config/CacheConfig.java
  - topup-mng/src/main/java/com/platform/topupmng/config/provider/BehsaProperties.java
  - topup-mng/src/main/java/com/platform/topupmng/mapper/behsa/BehsaBundleMapper.java
  - topup-mng/src/main/java/com/platform/topupmng/model/topupinfo/OperatorInfo.java
  - topup-mng/src/main/java/com/platform/topupmng/service/switchbay/SwitchService.java
  - topup-mng/src/main/java/com/platform/topupmng/service/switchbay/impl/SwitchServiceImpl.java
  - topup-mng/src/main/java/com/platform/topupmng/service/switchbay/mapper/SwitchMapper.java
  - topup-mng/src/main/java/com/platform/topupmng/service/topup/OperatorServiceProvider.java
  - topup-mng/src/main/java/com/platform/topupmng/service/topup/TopUpService.java
  - topup-mng/src/main/java/com/platform/topupmng/service/topup/impl/TopUpServiceImpl.java
  - topup-mng/src/main/java/com/platform/topupmng/service/topup/impl/gateway/behsa/BehsaServiceProvider.java
  - topup-mng/src/main/java/com/platform/topupmng/service/topup/impl/model/dto/InternetPackageModel.java
  - topup-mng/src/main/java/com/platform/topupmng/service/topup/impl/model/request/PersonalizedOfferListRequest.java
  - topup-mng/src/main/java/com/platform/topupmng/service/topup/impl/model/response/BundleListResult.java
  - topup-mng/src/main/resources/labels.properties
  - topup-mng/src/test/java/com/platform/topupmng/api/web/bundle/BundleResourceIT.java
  - topup-mng/src/test/java/com/platform/topupmng/client/behsa/BehsaClientTest.java
  - topup-mng/src/test/java/com/platform/topupmng/service/topup/impl/TopUpServiceImplTest.java
  - topup-mng/src/test/java/com/platform/topupmng/service/topup/impl/gateway/behsa/BehsaServiceProviderTest.java
  - topup-mng/src/test/resources/application-test.properties
  - topup-mng/src/test/resources/behsa/mappings/api_topup_gethamrahipackagesinfov1-e0f69328-b271-41e5-a5d6-45bcd68d29cb.json
---

# QA Handoff — ALPHA-15108: MCI Hamrahi personalized offers

## Update log

- 2026-09-06 — manual feature-scope search (no diff); paths = files on feat/ALPHA-15108-hamrahi-client-implementation vs origin/staging — documented current Hamrahi / personalized-offer behavior on the MCI bundle list

## Task overview (Farsi / خلاصه فارسی)

این قابلیت بسته‌های اینترنت «همراهی» همراه اول را روی لیست بسته‌ها نشان می‌دهد. کلاینت همان API موجود لیست بسته را صدا می‌زند (`POST /platform/api/bundles/{operatorId}` با شماره موبایل و نوع سیم‌کارت). اگر اپراتور MCI باشد، ارائه‌دهنده Behsa برای اینترنت انتخاب شده باشد، و در سند `operator_info` لیست شناسه بسته‌های همراهی عمومی پر شده باشد، سرویس از Behsa می‌پرسد این شماره کدام پیشنهادهای همراهی را دارد. پیشنهادهای منطبق هم در یک دسته جدا با عنوان «همراهی» برمی‌گردند و هم داخل دسته‌های مدت‌دار معمولی ادغام می‌شوند. همان بسته‌های همراهی عمومی از لیست عادی و از علاقه‌مندی‌ها کنار گذاشته می‌شوند. اگر آن لیست عمومی خالی باشد، دسته «همراهی» ساخته نمی‌شود و بسته‌ها فقط در دسته‌های معمولی می‌مانند. خرید جداگانه‌ای برای همراهی اضافه نشده است.

## Task identity

- Ticket: ALPHA-15108
- Branch: n/a — manual feature-scope run
- Commit range covered (all runs to date): n/a — documented via manual feature-scope search
- Feature scope searched: keywords: none; paths: the 29 files changed on `feat/ALPHA-15108-hamrahi-client-implementation` versus `origin/staging`

## Related tasks

No related tasks declared or detected for this run.

## Scope of change

- Public API: `POST /platform/api/bundles/{operatorId}` (bundle list) now also loads a personalized Hamrahi list and folds it into `bundleCategories`. `GET /platform/api/bundles/{operatorId}` (deprecated) does not. `POST /platform/api/bundles/{operatorId}/favorites` still returns favorites only, with Hamrahi general IDs dropped from that list.
- Provider: only Behsa reports support for personalized offers. Behsa calls `POST /Api/Topup/GetHamrahiPackagesInfoV1` for MCI numbers and maps the `offers` array to catalog packages by `offerCode`.
- Data: Mongo `operator_info.personalizedOffer` holds the general Hamrahi product bundle IDs used to strip those packages from the normal list and from favorites.
- Cache: Redis cache `personalized_offer`, TTL 6 hours, key is operator + cell number.
- Config: `behsa.personalized-offer-title` (in `labels.properties`) is the category title shown to the client; current value is همراهی.
- No UI in this service.

## Contract deltas

No new Platform HTTP endpoint and no change to the request body of the existing bundle-list POST (`cellNumber`, `cellNumberType`; optional user-id and agent headers). Path `operatorId` `1` is MCI.

Response is still `BundleListResponse.bundleCategories`. When personalized offers exist, that list contains:

1. Duration categories (daily / weekly / monthly / other, etc.), with matching Hamrahi packages merged into the duration they belong to (same `bundleId` is not duplicated inside a type).
2. The existing favorites category, without packages whose `bundleId` is in `operator_info.personalizedOffer`.
3. An extra category whose `title` is `behsa.personalized-offer-title` (همراهی), with those same Hamrahi packages grouped by duration.

Public package DTOs still expose `bundleId`, amount, duration, description, images, approval fields, and `pid` (provider). `offerCode` is used internally to match Behsa offers to catalog rows and is not on the public package DTO.

Upstream Behsa request (not a Platform public API): JSON body `TelNum`, `BizType` 108, `IsFree` 1, `channel` `"Topup"`, `gateway` `"Topup"`. Upstream response includes `offers` (string codes) and `prices`; only `offers` is used. `responseType` / `ResponseType` `0` is treated as success.

## Behavior & error semantics

- Personalized offers are attempted only when all of these hold: a non-blank cell number, Behsa as the chosen internet provider (`hasSupportPersonalizedOffer` is true only there), and a non-empty `operator_info.personalizedOffer` list for that operator.
- If any of those is missing, the dedicated همراهی category is omitted. Packages that would have been Hamrahi still appear in normal duration categories when the general ID list is empty.
- For Behsa, a non-MCI operator returns an empty offer list and does not call GetHamrahiPackagesInfoV1.
- User-specific offer codes from Behsa are matched to catalog packages by `offerCode`. General Hamrahi products are removed from the main list and from favorites by `bundleId`.
- Cell-number type filtering (pre-paid vs post-paid) is applied to both the main list and the personalized list.
- Redis caches the Behsa offer-code list per operator + cell number for 6 hours.
- If GetHamrahiPackagesInfoV1 returns a missing body, the personalized list is empty (no dedicated category).
- If Behsa returns a non-success `responseType` / `resultCode`, the Behsa client layer raises a provider exception. That call sits on the same bundle-list POST, so the bundle list request itself fails rather than returning packages without همراهی.
- A Behsa HTTP 401 refreshes the Behsa token and retries (existing Behsa client behavior). Timeouts surface as an endpoint-timeout client exception.
- Buying a Hamrahi package uses the existing bundle purchase flow and catalog `bundleId`; this feature does not add a purchase endpoint.

## Known defects

No changes observed in this category for this commit range.

## Disabled / skipped tests

No changes observed in this category for this commit range.

## Unimplemented / out of scope

- Deprecated `GET /platform/api/bundles/{operatorId}` does not load or return a personalized category.
- Behsa Hamrahi `prices` are parsed on the client DTO and then unused; displayed amounts come from the existing catalog, not from that array.
- Providers other than Behsa do not implement personalized offers (`hasSupportPersonalizedOffer` defaults to false).
- No new public field exposes `offerCode` to the client.

## Data & environment constraints

- MCI internet must be enabled on the Behsa provider in settings (weighted provider selection).
- Mongo `operator_info` for MCI must include `personalizedOffer`: the general Hamrahi catalog `bundleId`s. Without that list, Behsa is not queried for offers and no همراهی category is built.
- Catalog products must carry `offerCode` values that match Behsa `offers` (example from the recorded Behsa stub: offers `502557`, `502558`, `504574` mapped onto catalog ids such as `9987765` / `9987766` in the IT).
- Redis must be available for `personalized_offer` (6-hour TTL). A cached empty or stale offer list is reused until expiry.
- A cell number Behsa actually returns offers for is required to see the dedicated category (the recorded stub is wired to `09152608928`).
- Category title comes from `behsa.personalized-offer-title` (loaded via `labels.properties`).

## Non-goals

No changes observed in this category for this commit range.
