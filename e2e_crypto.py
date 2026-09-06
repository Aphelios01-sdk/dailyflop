#!/data/data/com.termux/files/usr/bin/python3
"""
End-to-End Encryption (E2EE / e2e/1) for Technocore Chat (Pattern 4).
Uses X25519 key exchange, HKDF-SHA256 key derivation, and AES-GCM authenticated encryption.
"""

import os
import base64
from typing import Optional, Tuple
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from config import Config

def b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")

def b64url_decode(s: str) -> bytes:
    pad = (4 - len(s) % 4) % 4
    return base64.urlsafe_b64decode(s + "=" * pad)

class E2EEEngine:
    def __init__(self, config: Config):
        self.config = config
        if config.x25519_priv:
            priv_bytes = b64url_decode(config.x25519_priv)
            self.static_priv = x25519.X25519PrivateKey.from_private_bytes(priv_bytes)
            self.static_pub = self.static_priv.public_key()
            pub_bytes = self.static_pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
            self.static_pub_b64 = b64url_encode(pub_bytes)
        else:
            self.static_priv = None
            self.static_pub = None
            self.static_pub_b64 = ""

    def is_e2e_frame(self, text: str) -> bool:
        return text.strip().startswith("e2e1 ")

    def decrypt_frame(self, frame_text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Decrypts an incoming e2e1 frame:
        'e2e1 <eph_pub_b64url> <nonce12_b64url> <sealed_b64url>'
        Returns: (plaintext_str, sender_eph_pub_b64) or (None, None)
        """
        if not self.static_priv:
            return None, None

        parts = frame_text.strip().split(" ")
        if len(parts) < 4 or parts[0] != "e2e1":
            return None, None

        try:
            eph_pub_bytes = b64url_decode(parts[1])
            nonce = b64url_decode(parts[2])
            sealed = b64url_decode(parts[3])

            eph_pub = x25519.X25519PublicKey.from_public_bytes(eph_pub_bytes)
            shared_secret = self.static_priv.exchange(eph_pub)

            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b"technocore-e2e-v1"
            )
            key = hkdf.derive(shared_secret)

            aesgcm = AESGCM(key)
            plaintext_bytes = aesgcm.decrypt(nonce, sealed, None)
            return plaintext_bytes.decode("utf-8"), parts[1]
        except Exception as e:
            print(f"[E2EE] Decryption error: {e}")
            return None, None

    def encrypt_message(self, recipient_pub_b64: str, plaintext: str) -> Optional[str]:
        """
        Encrypts a plaintext string to an e2e1 frame destined for recipient_pub_b64:
        'e2e1 <eph_pub_b64url> <nonce12_b64url> <sealed_b64url>'
        """
        try:
            recip_pub_bytes = b64url_decode(recipient_pub_b64)
            recip_pub = x25519.X25519PublicKey.from_public_bytes(recip_pub_bytes)

            eph_priv = x25519.X25519PrivateKey.generate()
            eph_pub = eph_priv.public_key()
            eph_pub_bytes = eph_pub.public_bytes(Encoding.Raw, PublicFormat.Raw)

            shared_secret = eph_priv.exchange(recip_pub)
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b"technocore-e2e-v1"
            )
            key = hkdf.derive(shared_secret)

            nonce = os.urandom(12)
            aesgcm = AESGCM(key)
            sealed = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

            return f"e2e1 {b64url_encode(eph_pub_bytes)} {b64url_encode(nonce)} {b64url_encode(sealed)}"
        except Exception as e:
            print(f"[E2EE] Encryption error: {e}")
            return None

if __name__ == "__main__":
    cfg = Config.from_env()
    engine = E2EEEngine(cfg)
    print(f"E2EE Engine Initialized!")
    print(f"Static X25519 Public Key: {engine.static_pub_b64}")
