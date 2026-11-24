# اولویت‌بندی مهاجرت لایه Services به Playwright + پلن مهاجرت LMS و LOS

> تهیه‌شده بر اساس تحلیل استاتیک وابستگی‌های import در ۳۱۷ فایل پایتون زیر `tests/` (پروژه
> `playwright-e2e-automation`) به‌علاوه بررسی اسناد موجود پروژه:
> `AGENTS.md`، `docs/framework/STATUS.md`، `docs/framework/migration-status.md`،
> `docs/framework/migration-inventory.md`، `.cursor/skills/pytest-migration/SKILL.md`.
> تاریخ تهیه: ۱۴۰۵/۰۶/۰۲ (2026-08-24)

---

## ۰. یک نکتهٔ مهم دربارهٔ ساختار پروژه (قبل از هر چیز)

در مسیر متصل‌شده (`playwright-e2e-automation`) پوشه‌ای به نام `src/services` وجود ندارد.
با بررسی مستندات پروژه مشخص شد:

- فریمورک **روبوت واقعی** یک ریپازیتوری **جدا** به نام **`api-robot-automated-test`** است که
  در این سشن متصل نیست (طبق `.cursor/rules/migration-core.mdc`: *"Robot source now lives in a
  separate repo... Never write to that repo as part of a port — it's read-only reference"*).
  لایهٔ `src/services/backend/*.resource`، `src/services/db/*.resource`،
  `src/services/frontend/*.resource` و `src/library/*.py` همگی در **آن ریپو** هستند، نه اینجا.
- پروژهٔ `playwright-e2e-automation` که الان به آن دسترسی دارم، **مقصد نهایی مهاجرت** است
  (pytest + pytest-bdd + httpx + Playwright). طبق `STATUS.md`: *"Foundation migration is
  complete... this is now the steady-state framework, not an in-flight migration."*
- هر فایل داخل `tests/services/` در docstring خودش دقیقاً می‌گوید از کدام فایل `.resource` یا
  `.py` روبوت پورت شده (مثلاً `services/auth.py` → *"Port of
  src/services/backend/auth-service.resource"*، یا `services/db/mongo_client.py` → *"Port of
  src/library/mongo_db.py + config from src/services/db/mongo-db-service.resource"*).

**نتیجه:** چون به کد خام ریپوی روبوت دسترسی مستقیم ندارم، تحلیل وابستگی را روی **معادل
پورت‌شدهٔ همان سرویس‌ها در `tests/services/`** انجام دادم — که چون پورت «رفتار-محور» بوده
(نه بازنویسی از صفر)، ساختار وابستگی‌اش به‌طور معقولی همان اولویت‌های لایهٔ روبوت را منعکس
می‌کند. جدول‌های زیر هرجا که مستندات پروژه (`migration-inventory.md`) صراحتاً منبع روبوت را
اسم برده، آن را هم آورده‌ام تا رهگیری به فایل اصلی روبوت هم ممکن باشد.

اگر منظور واقعی شما پوشهٔ `src/services` در ریپوی جدای `api-robot-automated-test` بوده (نه این
پروژه)، آن ریپو باید جداگانه به‌عنوان یک پوشهٔ دیگر به سشن متصل شود تا بتوانم مستقیماً رویش
تحلیل انجام دهم؛ فعلاً تحلیل زیر بر مبنای معادل پورت‌شده و مستندات موجود است.

---

## ۱. روش تحلیل

- شمارش **۳۱۷ فایل `.py`** زیر `tests/` (بدون `__pycache__`) با `ast` پایتون، استخراج همهٔ
  `import` / `from ... import ...` و ساخت گراف وابستگی بین ماژول‌ها.
- برای هر ماژول زیر `services/` دو عدد محاسبه شد:
  - **fan-in بیرونی (ext)** = چند ماژول در لایه‌های بعدی (`bdd/steps`, `ui`, `api`, `unit`,
    `conftest`) مستقیماً از آن import می‌کنند.
  - **fan-in داخلی (internal)** = چند ماژول *دیگر* در خود `services/` به آن وابسته‌اند
    (سرویس‌های زیرساختی که خودِ سرویس‌های دیگر روی آن‌ها ساخته شده‌اند).
  - **امتیاز ترکیبی (combined) = ext + internal** → معیار اولویت مهاجرت: هرچه بالاتر، شکستن یا
    ناقص‌بودن آن ماژول اثر گسترده‌تری روی بقیهٔ لایه‌ها دارد.

---

## ۲. اولویت‌بندی سرویس‌ها (Tier بندی بر اساس امتیاز وابستگی)

### Tier 1 — زیرساخت مشترک (باید همیشه اول کامل/پایدار باشد)

این‌ها «سرویس روی سرویس» نیستند، بلکه ابزارهایی هستند که تقریباً همهٔ دامنه‌ها (debit، kyc،
wallet، bill) رویشان سوار می‌شوند.

| ماژول | combined | ext | internal | نقش | وضعیت مهاجرت (طبق migration-inventory.md) |
|---|---:|---:|---:|---|---|
| `services/assert_report.py` | **40** | 8 | 32 | موتور مرکزی assertion + گزارش Allure (PASS/FAIL/ERROR) | ابزار جدید فریمورک (معادل مستقیم روبوت ندارد) — پایه‌ای و کامل |
| `services/api_assert.py` | 12 | 0 | 12 | `ensure_status`/`ensure_ok` برای خطاهای setup/teardown | ابزار جدید فریمورک — پایه‌ای و کامل |
| `services/tracking.py` | 11 | 9 | 2 | تولید کد رهگیری تراکنش | کوچک، پایه‌ای، کامل |
| `services/db/mongo_client.py` | 11 | 6 | 5 | کلاینت Mongo | پورت `mongo-db-service.resource` (۲۸KB) — **انجام‌شده** (۲۰۲۶-۰۷-۳۱)، aggregate/indexes باقی مانده |
| `services/factories.py` | 6 | 4 | 2 | `BusinessFactory` / `UserFactory` | پورت `fresh-business-initializer` + `fresh-user-initializer` — **انجام‌شده** |
| `services/db/mysql_client.py` | 6 | 4 | 2 | کلاینت MySQL | پورت `mysql-db-service.resource` — **انجام‌شده**، table/describe/count پورت نشده |
| `services/db/redis_client.py` | 6 | 4 | 2 | کلاینت Redis (OTP) | پورت `redis-db-service.resource` — **جزئی**؛ sentinel/cluster/TLS پورت نشده |
| `services/auth.py` | 3 | 2 | 1 | `login_business` / `login_to_app` | پورت `auth-service.resource` — **در حال انجام**؛ Login To Dashboard هنوز شروع نشده |

**پیامد عملی:** اگر یک قطعه از این هشت مورد ناقص یا شکننده بماند، اثرش روی *همهٔ* دامنه‌ها پخش
می‌شود. مهم‌ترین گپ باز همین لایه: **Redis sentinel/cluster/TLS** و **Login To Dashboard**
(auth) — هر دو در `migration-inventory.md` صراحتاً «not started» علامت خورده‌اند و چون
Tier 1 هستند، تکمیل‌شان باید قبل از هر کار دامنه‌ای جدید (از جمله LMS/LOS) در اولویت باشد.

### Tier 2 — هاب دامنهٔ Debit (بیشترین وزن تکی در کل پروژه)

| ماژول | combined | ext | internal | توضیح |
|---|---:|---:|---:|---|
| `services/debit/bank_transfer.py` | **32** | 11 | 21 | هاب مرکزی همهٔ زیرجریان‌های bank-transfer (direct/manual/dsh/peers/routing) |
| `services/debit/bank_transfer_routing.py` | 13 | 3 | 10 | مسیریابی تراکنش بین بانک‌ها |
| `services/debit/nemo_secrets.py` | 10 | 2 | 8 | مدیریت secret/credential نمو |
| `services/debit/bank_transfer_secrets.py` | 9 | 3 | 6 | secret مربوط به bank-transfer |
| `services/debit/nemo_cash_out.py` | 9 | 3 | 6 | جریان اصلی cash-out نمو |
| `services/debit/nemo_wallet_db.py` | 6 | 2 | 4 | دسترسی DB کیف‌پول نمو |
| `services/debit/bank_transfer_asserts.py` | 6 | 4 | 2 | assertهای اختصاصی bank-transfer |

دامنهٔ debit در مجموع بالاترین امتیاز تجمعی را در کل `services/` دارد (۱۴۴ از مجموع ext+internal
روی ۳۴ ماژول) — یعنی هرچه از این دامنه ناقص/شکننده بماند، ریسکش از همهٔ دامنه‌های دیگر بیشتر
است. طبق `migration-status.md` وضعیت debit همین الان «in progress — 167 SET-T (live/secret
gated)» است؛ یعنی این تیر واقعاً محل کار فعلی تیم است، نه یک مورد فراموش‌شده.

### Tier 3 — دامنهٔ KYC (زیرساخت احراز هویت — برای LOS حیاتی، پایین‌تر توضیح داده می‌شود)

| ماژول | combined | ext | internal | توضیح |
|---|---:|---:|---:|---|
| `services/kyc/promissory_note.py` | 4 | 2 | 2 | سفتهٔ الکترونیک |
| `services/kyc/shahkar.py` | 3 | 1 | 2 | تطبیق شماره موبایل ↔ کدملی |
| `services/kyc/digital_signature.py` | 3 | 1 | 2 | امضای دیجیتال |
| `services/kyc/registration_inquiry.py` | 3 | 1 | 2 | استعلام ثبت‌احوال |
| `services/kyc/postal_code.py` | 3 | 1 | 2 | استعلام کدپستی/آدرس |

طبق `migration-status.md`، دامنهٔ kyc از نظر پورت **پیشرفته‌ترین دامنه بعد از debit** است:
digital signature، promissory (۳۷ سناریو)، shahkar، postal-code و registration-inquiry همه
حداقل یک اسلایس زندهٔ پورت‌شده دارند. این نکته مستقیماً به پلن LOS در بخش ۴ مرتبط است.

### Tier 4 — برگ‌ها (fan-in پایین، آخرین اولویت)

اکثر فایل‌های `*_gherkin.py` (تولید دادهٔ سناریو برای یک feature خاص) و فایل‌های assert
تک‌مصرفی amount≈۱، مثل `services/debit/manual_gherkin.py`، `services/kyc/postal_code_gherkin.py`
و مشابه — این‌ها فقط توسط یک یا دو فایل step استفاده می‌شوند، پس شکستن‌شان شعاع اثر کمی دارد و
باید آخرین اولویت باشند.

---

## ۳. جمع‌بندی سطح دامنه

| دامنه | امتیاز تجمعی | ext | internal | تعداد ماژول | وضعیت پورت (migration-status.md) |
|---|---:|---:|---:|---:|---|
| debit | 144 | 61 | 83 | 34 | in progress — 167 SET-T (live/secret gated) |
| core-root (assert/db/auth/factories/...) | 132 | 65 | 67 | 33 | زیرساخت — بیشتر «done»، Redis و dashboard-login باز |
| kyc | 47 | 25 | 22 | 21 | پیشرفته — ۵ زیرحوزه هرکدام حداقل یک اسلایس زنده |
| db (mongo/mysql/redis) | 23 | 14 | 9 | 3 | mongo/mysql done، redis جزئی |
| super_app (internet/…) | 5 | 5 | 0 | 4 | ابتدایی |

---

## ۴. پلن مهاجرت LMS (Loan Management System)

### وضعیت فعلی
طبق `migration-status.md`: ردیف `lms` → مسیر روبوت `features/lms/`، مسیر pytest **«—»**،
وضعیت **deferred**. در `migration-inventory.md` همهٔ موارد وابسته به LMS صراحتاً
«deferred — LMS domain deferred» علامت خورده‌اند:

| مورد در روبوت | نقش | چرا سنگین است |
|---|---|---|
| `import-allocation.resource` | orchestration تخصیص وام (loan-allocation) | به `allocate_utils.py` و قالب‌های Excel وابسته است |
| `library/allocate_utils.py`, `library/change_excel.py` | تولید قالب import در Excel برای تخصیص LMS | منطق فایل/فرمت اکسل، معادل پایتونی ندارد هنوز |
| `library/installment_date_utils.py` | محاسبهٔ تاریخ اقساط با تقویم جلالی (`jdatetime`) | منطق تقویمی خاص، پرخطا برای rounding/تاریخ |
| `LMS/credit-core/*.resource`, `LMS/installment/*.resource` | منطق عمیق یکپارچه‌سازی بانکی (Saderat/Mellat/Tejarat payload models) | چند مدل payload بانکی جدا، حجم زیاد |

### چرا این پلن بر اساس وابستگی سرویس‌ها اولویت‌بندی شده
LMS به‌طور طبیعی روی زیرساخت **پرداخت/کسر از کیف‌پول** و **تراکنش بانکی** می‌نشیند (وصول قسط از
کیف‌پول یا حساب بانکی مشتری) — یعنی دقیقاً همان Tier 1 (`db/*`, `auth`, `assert_report`,
`api_assert`) و بخشی از Tier 2 (`debit/bank_transfer*`, `wallet_initializer`, `transfer_service`)
که در بخش ۲ تحلیل شد. تا وقتی این‌ها کامل/پایدار نباشند، شروع LMS یعنی ساختن روی یک پایهٔ نیمه‌کاره.

### فازبندی پیشنهادی

1. **فاز صفر — پیش‌نیاز مشترک (نه اختصاصی LMS):**
   تکمیل گپ‌های باز Tier 1 که LMS مستقیم به آن‌ها متکی است:
   Redis sentinel/cluster (اگر LMS از قفل/صف توزیع‌شده استفاده می‌کند)، تکمیل
   `services/db/postgres_client.py` برای هندلرهای collateral/treasury (طبق
   migration-inventory §3 همین الان «done 2026-07-31 — collateral + treasury handlers» است، پس
   این بخش آماده است) و پایدارسازی `services/debit/bank_transfer*` (Tier 2، در حال انجام).

2. **فاز ۱ — primitive های API (طبق «Code Generation Order» خودِ پروژه در `AGENTS.md`):**
   ساخت `tests/api/lms/*.py` (کلاینت‌های HTTP نازک) برای endpointهای اصلی LMS — این فولدر همین
   الان به‌صورت خالی در پروژه وجود دارد (`tests/api/lms/`) یعنی جایگاهش scaffold شده ولی محتوایی
   ندارد.

3. **فاز ۲ — سرویس‌های تخصصی LMS (`tests/services/lms/`، ساخته نشده):**
   - معادل `installment_date_utils.py` → یک ماژول تاریخ جلالی مستقل (بالاترین اولویت داخل خود
     LMS، چون هر محاسبهٔ قسط به آن وابسته است — دقیقاً مثل الگوی Tier 1 در بخش ۲: یک سرویس کوچک
     با fan-in داخلی بالا).
   - معادل `allocate_utils.py` / `change_excel.py` → یا معادل پایتونی (openpyxl) یا تصمیم آگاهانه
     که آزمون تخصیص Excel از محدودهٔ API/UI خودکار خارج بماند (نیاز به تصمیم تیم، طبق سند اصلی
     «TBD»).
   - مدل‌های payload بانکی (Saderat/Mellat/Tejarat) → با الگوی موجود `bank_transfer_*` (Tier 2)
     هم‌راستا کنید، نه بازطراحی از صفر.

4. **فاز ۳ — BDD + UI:** طبق ترتیب استاندارد پروژه (feature → steps → ui)، بعد از تثبیت فاز ۲.

5. **فاز ۴ — به‌روزرسانی مستندات:** `migration-status.md` ردیف lms و `migration-inventory.md`
   موارد §1/§2 مرتبط، طبق قرارداد خودِ پروژه («Update migration-status.md's domain/parity row»).

---

## ۵. پلن مهاجرت LOS (Loan Origination System)

### وضعیت فعلی — شفاف‌سازی مهم
برخلاف LMS، دامنهٔ **LOS اصلاً در `migration-status.md` ردیف مستقلی ندارد** — تنها اشاره به آن،
در `migration-inventory.md` §5 است: در فهرست پوشه‌های `src/data/` (دادهٔ روبوت) کلمهٔ `los` در
کنار `wallet, lms, kyc, gl, settlement, merchant-credit, wealth, pcm, tms, smc, ...` آمده، یعنی
داده وجود دارد ولی **حتی envelope اولیهٔ پیگیری هم برایش باز نشده**. در پروژهٔ pytest سه پوشهٔ
placeholder خالی برایش scaffold شده: `tests/api/los/`، `tests/bdd/features/los/`،
`tests/bdd/steps/los/` — یعنی جایگاه در نظر گرفته شده ولی هیچ کاری روی آن انجام نشده. این باید
به‌عنوان یک گپ مستندسازی هم گزارش شود، نه فقط یک آیتم بک‌لاگ.

### چرا اولویت وابستگی برای LOS واقعاً خبر خوبی است
LOS (بررسی/تأیید اعتبار مشتری قبل از اعطای وام) طبیعتاً روی **همان KYC** می‌نشیند که در بخش ۲
(Tier 3) دیدیم **پیشرفته‌ترین دامنهٔ پورت‌شده بعد از debit** است:

| نیاز معمول LOS | سرویس موجود | وضعیت |
|---|---|---|
| احراز هویت پایه (تطبیق موبایل/کدملی) | `services/kyc/shahkar.py` | پورت‌شده، سناریوی زنده دارد |
| استعلام ثبت‌احوال | `services/kyc/registration_inquiry.py` | پورت‌شده، سناریوی زنده دارد |
| استعلام آدرس/کدپستی | `services/kyc/postal_code.py` | پورت‌شده |
| امضای قرارداد وام | `services/kyc/digital_signature.py` | پورت‌شده |
| سفتهٔ اعتباری (وثیقهٔ وام) | `services/kyc/promissory_note.py` | پورت‌شده، ۳۷ سناریو |
| احراز هویت کاربر/بیزینس (لاگین) | `services/auth.py`, `services/factories.py` | پورت‌شده (Tier 1) |

یعنی برخلاف LMS که پیش‌نیازهایش (تاریخ جلالی، Excel، payload بانکی) عملاً از صفر است، **زیرساخت
اصلی موردنیاز LOS تقریباً کامل پورت شده** — فقط باید orchestration مخصوص «فرآیند اعطای وام» روی
همین سرویس‌های موجود سوار شود، نه بازسازی از پایه.

### فازبندی پیشنهادی

1. **فاز صفر — رفع گپ مستندسازی (پیش از هر کد):**
   چون LOS حتی یک ردیف در `migration-status.md` ندارد، اولین قدم — طبق قاعدهٔ خودِ پروژه
   («Plan → approval → implement»، `.cursor/rules/review-before-implement.mdc») — باید یک
   بررسی کوتاه روی ریپوی `api-robot-automated-test` (که این سشن به آن دسترسی ندارد) برای پیدا
   کردن دقیق مسیر `features/los/` و `src/services/.../los*` باشد، و افزودن یک ردیف رسمی `los`
   به جدول Domains در `migration-status.md` (مثل الگوی ردیف lms).

2. **فاز ۱ — استفادهٔ مجدد، نه بازسازی:**
   بر اساس جدول بالا، مستقیماً از سرویس‌های KYC موجود (Tier 3) به‌عنوان building block استفاده
   شود. کار جدید فقط لازم است روی:
   - `tests/api/los/*.py` (endpointهای اختصاصی امتیازدهی/تصمیم اعتباری وام) — فولدر placeholder
     از قبل هست.
   - یک سرویس orchestration جدید (مثلاً `tests/services/los/credit_decision.py`) که روی
     KYC-های موجود + یک endpoint امتیازدهی اعتباری (که باید طبق migration-inventory بررسی شود
     آیا معادلش در روبوت اصلاً پورت شده یا نه) سوار شود.

3. **فاز ۲ — BDD + UI:** طبق همان الگوی بخش ۴.

4. **فاز ۳ — ثبت رسمی در مستندات:** افزودن ردیف `los` به `migration-status.md` (Owner، Robot
   path، pytest path، Status، Parity) و به‌روزرسانی `migration-inventory.md` اگر سرویس
   orchestration جدیدی ساخته شد.

---

## ۶. نقشهٔ راه ترکیبی پیشنهادی (LMS + LOS + تکمیل زیرساخت)

بر اساس اولویت وابستگی محاسبه‌شده در بخش ۲/۳، ترتیب پیشنهادی کار:

1. **رفع گپ‌های باز Tier 1** (Redis sentinel/cluster، auth dashboard-login) — اثر روی همهٔ
   دامنه‌ها از جمله LMS/LOS آینده.
2. **شروع LOS زودتر از LMS** — چون پیش‌نیازهایش (KYC) تقریباً آماده است و فقط orchestration
   جدید لازم دارد؛ ریسک/حجم کار کمتر، بازگشت سریع‌تر.
3. **موازی یا بلافاصله بعد — تثبیت باقیماندهٔ debit (Tier 2)** چون LMS به‌طور مستقیم برای وصول
   قسط از `bank_transfer*` استفاده خواهد کرد.
4. **شروع LMS بعد از آماده‌شدن پیش‌نیازهای اختصاصی‌اش** (تاریخ جلالی، تصمیم دربارهٔ Excel
   allocation، مدل‌های payload بانکی) — سنگین‌ترین و کم‌اشتراک‌ترین دامنه با زیرساخت فعلی، پس
   منطقی است آخر از همه شروع شود.
5. در هر مرحله، به‌روزرسانی `migration-status.md` و `migration-inventory.md` طبق قرارداد خودِ
   پروژه، تا این تحلیل هم برای چرخهٔ بعدی معتبر بماند.

---

## پیوست — روش راستی‌آزمایی

- شمارش فایل‌ها: `find tests -name "*.py" | wc -l` → ۳۱۷ (بدون `__pycache__`)
- گراف وابستگی: AST پایتون روی هر ۳۱۷ فایل، بدون خطای parse
- اعداد fan-in به‌صورت خودکار محاسبه شده‌اند، نه حدسی — قابل بازتولید با اسکریپت مشابه در هر زمان
  که کد تغییر کند.
