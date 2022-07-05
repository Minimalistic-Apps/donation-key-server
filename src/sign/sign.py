import base64
from typing import cast
import rsa

from claim.donation_key import DonationKey


def sign(priv_key_path: str, message: str) -> DonationKey:
    with open(priv_key_path, "rb") as p:
        privateKey = rsa.PrivateKey.load_pkcs1(p.read())
        signature = rsa.sign(message.encode("utf-8"), cast(rsa.PrivateKey, privateKey), "SHA-1")

        return DonationKey(base64.b64encode(signature).decode("utf-8"))
