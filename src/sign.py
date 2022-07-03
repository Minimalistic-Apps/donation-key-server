import base64
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.PublicKey import RSA


def sign(priv_key_path: str, message: str) -> str:
    with open(priv_key_path, "rb") as src:
        private_key = RSA.importKey(str(src.read()))
        digest = SHA256.new(message.encode("utf-8"))
        signature = pkcs1_15.new(private_key).sign(digest)

        return base64.b64encode(signature).decode("utf-8")
