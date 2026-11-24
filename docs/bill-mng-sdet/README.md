# SDET pack for Platform bill-mng

## What to copy into your automation framework

| File | Use |
|------|-----|
| [`BILLS_TESTING_STRATEGY.md`](./BILLS_TESTING_STRATEGY.md) | **Start here for AI agents** — fake/real bills, WireMock, options, rules, decision tree |
| [`BILL_AUTOMATION_GUIDANCE_BOOK.md`](./BILL_AUTOMATION_GUIDANCE_BOOK.md) | Full API contracts, enums, status machine, Postman, provider weights |
| [`scripts/bill_mng/fake_bill_generator.py`](../../scripts/bill_mng/fake_bill_generator.py) | Generate Platform-checksum-valid fake billId/payId |
| [`postman/Bill-MNG-API.postman_collection.json`](./postman/Bill-MNG-API.postman_collection.json) | Import into Postman |
| [`postman/Bill-MNG-Local.postman_environment.json`](./postman/Bill-MNG-Local.postman_environment.json) | Postman environment variables |

## Quick start

1. Copy this entire `docs/sdet/` folder into your automation repo (e.g. `docs/bill-mng/`).
2. Import both Postman JSON files (re-import collection after updates).
3. Set `baseUrl` (and `authToken` if via gateway).
4. Run collection folder **01 Happy Path — Wallet Pay**.
5. For admin provider weights (Finnotech/Ghabzino sliders), see guide **§20** and Postman folder **06 Admin**.
6. Point your AI agent at **`BILLS_TESTING_STRATEGY.md`** for test data / layers, and `BILL_AUTOMATION_GUIDANCE_BOOK.md` for API contracts (§19 prompt there).

## Cursor canvas

If you use Cursor IDE on the bill-mng clone, open the companion canvas:

`~/.cursor/projects/Users-mohammadjavad-Projects-bill-mng/canvases/bill-mng-sdet-guide.canvas.tsx`
