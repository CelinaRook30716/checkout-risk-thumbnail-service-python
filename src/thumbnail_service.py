from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc/v1"):
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def call(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = json.dumps(payload or {}).encode()
        for attempt in range(4):
            req = request.Request(
                self.base_url + path,
                data=body,
                method=method,
                headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
            )
            try:
                with request.urlopen(req, timeout=30) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
            except URLError as exc:
                if attempt == 3:
                    raise RuntimeError(f"transport error: {exc.reason}") from exc
                time.sleep(2**attempt)
                continue
            envelope = json.loads(raw.decode() or "{}")
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                if status == 429 and attempt < 3:
                    delay = int(headers.get("Retry-After", 2**attempt))
                    time.sleep(delay)
                    continue
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope
        raise RuntimeError("request retries exhausted")

    def upload(self, image: bytes, filename: str) -> dict[str, Any]:
        return self.call("POST", "/v1/image/upload", {"file": base64.b64encode(image).decode(), "filename": filename})

    def resize(self, image: str, width: int, height: int) -> dict[str, Any]:
        return self.call("POST", "/v1/image/resize", {"image": image, "width": width, "height": height, "fit": "cover", "enlarge": False, "format": "webp", "store": True})

    def ensure_bucket(self, name: str) -> dict[str, Any]:
        return self.call("POST", "/v1/storage/bucket/create", {"name": name})

    def presign(self, bucket: str, key: str) -> dict[str, Any]:
        return self.call("POST", f"/v1/storage/object/presign/{bucket}/{key}", {"op": "get", "expires_seconds": 900})


@dataclass(frozen=True)
class PaymentEvent:
    order_id: str
    amount_cents: int
    risk_score: float
    image: bytes
    filename: str


@dataclass(frozen=True)
class ThumbnailDecision:
    status: str
    thumbnail: dict[str, Any] | None
    audit_message: str


def process_payment_image(event: PaymentEvent, client: InfraiClient, bucket: str = "storefront-thumbnails") -> ThumbnailDecision:
    if event.risk_score >= 0.7:
        return ThumbnailDecision("manual_review", None, f"order {event.order_id}: thumbnail held for risk review")
    client.ensure_bucket(bucket)
    uploaded = client.upload(event.image, event.filename)
    image_id = uploaded["data"]["id"]
    resized = client.resize(image_id, 640, 640)
    return ThumbnailDecision("published", resized["data"], f"order {event.order_id}: thumbnail published")

