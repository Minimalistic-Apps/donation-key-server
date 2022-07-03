from decimal import Decimal
from typing import NewType


LnUrl = NewType("LnUrl", str)
LnUrlToken = NewType("LnUrlToken", str)
DonationTokenClaim = NewType("DonationTokenClaim", str)
AmountSats = NewType("AmountSats", Decimal)
