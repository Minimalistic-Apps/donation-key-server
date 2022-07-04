from typing import Dict, Optional

from lnbits import AmountSats, LnBitsPaymentLinkId, LnBitsPayment


def validate_payment_by_hash(
    payment: LnBitsPayment, expected_id: LnBitsPaymentLinkId, expected_amount: AmountSats
) -> Optional[str]:
    if not payment.paid:
        return f"Callback received, but payment not paid."

    payment_link_id = payment.details.extra.link

    if expected_id != payment_link_id:
        return f"PaymentLinkId ({payment_link_id}) is not as expected ({expected_id})"

    if payment.details.amount < expected_amount:
        return f"Amount send ${payment.details.amount} is less then ${expected_amount}"

    return None
