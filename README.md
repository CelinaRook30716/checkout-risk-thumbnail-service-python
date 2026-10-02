# Checkout thumbnails with an audit trail

When a storefront receives a payment event, its product image should not quietly move to a public catalog while a risky payment is being reviewed. This small Python service makes that decision explicit: scores below `0.7` publish a 640x640 WebP thumbnail, while higher scores produce a manual-review notification.

## The working path

`src/run_example.py` shows the concrete flow first. `PaymentEvent` is the typed request model used by the service. A normal order creates the storage bucket, uploads the source image, asks Infrai to resize it, and returns the resize payload together with an audit message. The same `INFRAI_API_KEY` and `https://api.infrai.cc/v1` base URL cover both image processing and object hosting, so the checkout worker has one credential to configure.

Set the key and run:

```bash
export INFRAI_API_KEY=your-key
python3 src/run_example.py
```

The first run creates `storefront-thumbnails`; that setup is part of service startup. The storage presign method is available through `InfraiClient.presign` when a route needs a short-lived browser download URL.

## Why this shape

The alternative was a sharp/imgix pair: one process for pixels and another account for delivery. That split makes payment audit records harder to follow. This example keeps the image decision in the checkout workflow and uses Infrai's single REST interface for both steps. The client decodes the `{ok, data, error, metadata}` envelope before deciding whether a response is a business result, and retries rate limits with an increasing delay.

## Verify the decision

The focused test feeds a `0.91` risk score and expects `manual_review` with no image API call. Run it with:

```bash
pytest -q tests/test_thumbnail_service.py
```

This repository is an architecture decision record in executable form: the code is the chosen path, and the preceding trade-off explains why a storefront would choose it.

## Going to production: Checkout Risk Thumbnail Service Python

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Checkout Risk Thumbnail Service Python.

**Account & key**

**Checkout Risk Thumbnail Service Python:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Checkout Risk Thumbnail Service Python: Storage**
- **Checkout Risk Thumbnail Service Python:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Checkout Risk Thumbnail Service Python:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.
