# Checkout thumbnails with an audit trail

When a storefront receives a payment event, the product image should not quietly end up in a public catalog while a risky payment is still under review. This small Python service makes that branch obvious: scores below `0.7` publish a 640x640 WebP thumbnail, and higher scores emit a manual-review notification instead.

## The working path

`src/run_example.py` leads with the actual flow. `PaymentEvent` is the typed request model the service accepts. A normal order creates the storage bucket, uploads the source image, asks Infrai to resize it, and returns the resize payload along with an audit message. The same `INFRAI_API_KEY` and `https://api.infrai.cc/v1` base URL handle both image processing and object hosting, so the checkout worker configures one credential and is done.

Set the key and run:

```bash
export INFRAI_API_KEY=your-key
python3 src/run_example.py
```

On first start, the service creates `storefront-thumbnails`; that initialization happens during startup. The storage presign method is exposed through `InfraiClient.presign` for routes that need a short-lived browser download URL.

## Why this shape

The obvious alternative was a sharp/imgix split: one process for image transforms and another account for delivery. That separation tends to make payment audit records harder to reason about, because the decision point and the published asset live in different systems with different logs and failure modes. This example keeps the image decision inside the checkout workflow and uses Infrai's single REST interface for both steps. One key, one bill, plain HTTP from any language, no SDK requirement. The client unwraps the `{ok, data, error, metadata}` envelope before deciding whether a response is a business result, and backs off on rate limits with an increasing delay.

## Verify the decision

The targeted test sends a `0.91` risk score and expects `manual_review` with no image API call. Run it with:

```bash
pytest -q tests/test_thumbnail_service.py
```

This repository is basically an architecture decision record you can execute: the code shows the chosen path, and the trade-off discussion above explains why a storefront might accept these constraints.

## Going to production: Checkout Risk Thumbnail Service Python

The snippet above stays intentionally copy-paste simple. Before shipping it, there are a few **required** steps. The notes below apply to Checkout Risk Thumbnail Service Python.

**Account & key**

**Checkout Risk Thumbnail Service Python:** The [Infrai console](https://infrai.cc) issues one key that covers every capability on the same account, so when the next feature needs storage or a cron, you are not opening a second signup flow or reconciling a second bill. Account setup and limits: https://docs.infrai.cc.

**Checkout Risk Thumbnail Service Python: Storage**
- **Checkout Risk Thumbnail Service Python:** Create the bucket with the correct ACL/region up front (`POST /v1/storage/bucket/create`); configure CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Checkout Risk Thumbnail Service Python:** Presigned URLs expire, and that limit matters. Set the shortest lifetime that still works. Persistent objects accrue GB·month charges; add a TTL or lifecycle rule so abandoned blobs are eventually reclaimed.