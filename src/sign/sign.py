import base64
import rsa


def sign(priv_key_path: str, message: str) -> str:
    with open(priv_key_path, "rb") as p:
        privateKey = rsa.PrivateKey.load_pkcs1(p.read())
        signature = rsa.sign(message.encode("utf-8"), privateKey, "SHA-1")

        return base64.b64encode(signature).decode("utf-8")
