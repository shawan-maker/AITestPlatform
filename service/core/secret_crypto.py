import base64
import hashlib

from service.core.settings import JWT_SECRET_KEY


def _key() -> bytes:
    return hashlib.sha256(JWT_SECRET_KEY.encode("utf-8")).digest()


def encrypt_secret(plain: str) -> str:
    data = plain.encode("utf-8")
    key = _key()
    xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return base64.urlsafe_b64encode(xored).decode("utf-8")


def decrypt_secret(cipher: str) -> str:
    xored = base64.urlsafe_b64decode(cipher.encode("utf-8"))
    key = _key()
    data = bytes(b ^ key[i % len(key)] for i, b in enumerate(xored))
    return data.decode("utf-8")
