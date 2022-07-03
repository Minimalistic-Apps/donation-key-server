from decimal import Decimal
from typing import Optional

from lnbits import AmountSats, LnBitsCallbackData


def payment_callback_validation(callback_data: LnBitsCallbackData, expected_sats_amount: AmountSats) -> Optional[str]:
    amount = AmountSats(Decimal(callback_data.amount))

    if expected_sats_amount < expected_sats_amount:
        return f"Amount send ${amount} is less then ${expected_sats_amount}, please contact suport for refund"

    return None
