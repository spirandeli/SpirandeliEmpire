import base64
import hashlib
import hmac
import json
import os
from typing import Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding


def parse_app_key(app_key: str) -> bytes:
    if app_key.startswith("base64:"):
        return base64.b64decode(app_key[7:])
    return app_key.encode("utf-8")


def decrypt_string(payload_b64: str, app_key: str) -> str:
    """
    Descriptografa payload produzido pelo Illuminate\\Support\\Facades\\Crypt
    (AES-256-CBC com HMAC-SHA256 e PKCS7 padding).
    """
    key = parse_app_key(app_key)
    raw_json = base64.b64decode(payload_b64).decode("utf-8")
    payload = json.loads(raw_json)

    iv_str = payload["iv"]
    val_str = payload["value"]
    mac_str = payload["mac"]

    # Validação do MAC (HMAC-SHA256 de iv_b64 + val_b64)
    expected_mac = hmac.new(key, (iv_str + val_str).encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_mac, mac_str):
        raise ValueError("MAC inválido ao descriptografar dado do Laravel.")

    iv = base64.b64decode(iv_str)
    encrypted_bytes = base64.b64decode(val_str)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(encrypted_bytes) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    decrypted_bytes = unpadder.update(padded_data) + unpadder.finalize()

    return decrypted_bytes.decode("utf-8")


def encrypt_string(value: str, app_key: str) -> str:
    """
    Criptografa string gerando payload 100% legível pelo Laravel Crypt::decryptString.
    """
    key = parse_app_key(app_key)
    iv = os.urandom(16)

    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(value.encode("utf-8")) + padder.finalize()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    encrypted_bytes = encryptor.update(padded_data) + encryptor.finalize()

    iv_b64 = base64.b64encode(iv).decode("utf-8")
    val_b64 = base64.b64encode(encrypted_bytes).decode("utf-8")
    mac = hmac.new(key, (iv_b64 + val_b64).encode("utf-8"), hashlib.sha256).hexdigest()

    payload_dict = {
        "iv": iv_b64,
        "value": val_b64,
        "mac": mac,
        "tag": "",
    }
    json_bytes = json.dumps(payload_dict, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(json_bytes).decode("utf-8")

