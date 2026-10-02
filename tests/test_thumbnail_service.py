import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from thumbnail_service import PaymentEvent, ThumbnailDecision, process_payment_image


class NoCallClient:
    def ensure_bucket(self, name):
        raise AssertionError("high-risk events must stop before image calls")


def test_high_risk_payment_requires_review():
    event = PaymentEvent("order-7", 5000, 0.91, b"image", "item.jpg")
    result = process_payment_image(event, NoCallClient())
    assert result == ThumbnailDecision("manual_review", None, "order order-7: thumbnail held for risk review")
