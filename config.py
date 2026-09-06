import os
from dataclasses import dataclass

def _load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k not in os.environ:
                        os.environ[k] = v.strip("\"'")

@dataclass
class Config:
    url: str
    did: str
    signing_key: str
    payment_key: str
    mailbox: str
    x25519_priv: str = ""
    x25519_pub: str = ""

    @classmethod
    def from_env(cls) -> "Config":
        _load_env_file()
        url = os.environ.get("TECHNOCORE_URL", "https://technocore.chat").rstrip("/")
        did = os.environ.get("TECHNOCORE_DID", "")
        signing_key = os.environ.get("TECHNOCORE_SIGNING_KEY", "")
        payment_key = os.environ.get("TCLK_PAYMENT_KEY", "")
        mailbox = os.environ.get("TECHNOCORE_MAILBOX", "")
        x25519_priv = os.environ.get("TECHNOCORE_X25519_PRIV", "")
        x25519_pub = os.environ.get("TECHNOCORE_X25519_PUB", "")
        if not did or not signing_key:
            raise ValueError("TECHNOCORE_DID and TECHNOCORE_SIGNING_KEY must be set.")
        return cls(
            url=url,
            did=did,
            signing_key=signing_key,
            payment_key=payment_key,
            mailbox=mailbox,
            x25519_priv=x25519_priv,
            x25519_pub=x25519_pub
        )
