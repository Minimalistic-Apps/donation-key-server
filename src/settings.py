from decimal import Decimal
from get_env import get_env
from lnbits import AmountSats, LnBitsApiKey

URL_CLAIM = "/donation/api/key/claim"
URL_PAYMENT_SUCCESS_CALLBACK = "/donation/api/key/payment-success-callback"

PRIVATE_KEY = get_env("PRIVATE_KEY")
DOMAIN = get_env("DOMAIN")
LN_BITS_API_KEY = LnBitsApiKey(get_env("LN_BITS_API_KEY"))
LN_BITS_URL = LnBitsApiKey(get_env("LN_BITS_URL"))
SATS_AMOUNT = AmountSats(Decimal(get_env("SATS_AMOUNT")))
PORT = int(get_env("PORT"))
