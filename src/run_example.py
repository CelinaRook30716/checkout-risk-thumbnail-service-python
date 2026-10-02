from thumbnail_service import InfraiClient, PaymentEvent, process_payment_image


def main() -> None:
    event = PaymentEvent("order-1042", 1299, 0.12, b"demo-image-bytes", "shoe.jpg")
    result = process_payment_image(event, InfraiClient())
    print(result.status, result.audit_message)


if __name__ == "__main__":
    main()

