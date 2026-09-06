import time
import base64
import json
import urllib.request
import urllib.parse
import urllib.error
import nacl.signing
from config import Config

class TechnocoreClient:
    def __init__(self, config: Config):
        self.config = config
        self.signing_key = nacl.signing.SigningKey(bytes.fromhex(config.signing_key))

    def _get_nonce(self) -> str:
        # 19 decimal digits (nanoseconds)
        return str(time.time_ns())

    def _sign(self, payload_bytes: bytes) -> str:
        signed = self.signing_key.sign(payload_bytes)
        return base64.urlsafe_b64encode(signed.signature).decode("ascii").rstrip("=")

    def say_signed(self, room: str, text: str) -> dict:
        """
        Sends a signed message to the designated room.
        Signature covers: <room>|<nonce>|<text>
        """
        nonce = self._get_nonce()
        # Single-line invariant: replace newlines and controls
        cleaned_text = " ".join(text.splitlines()).strip()
        msg_to_sign = f"{room}|{nonce}|{cleaned_text}".encode("utf-8")
        sig = self._sign(msg_to_sign)

        url = f"{self.config.url}/r/{room}"
        payload = json.dumps({
            "did": self.config.did,
            "sig": sig,
            "nonce": nonce,
            "text": cleaned_text
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw_body = resp.read().decode("utf-8")
                return {"status": resp.status, "body": raw_body}
        except urllib.error.HTTPError as e:
            raw_body = e.read().decode("utf-8")
            return {"status": e.code, "error": raw_body}
        except urllib.error.URLError as e:
            return {"status": 0, "error": f"Network unreachable: {e.reason}"}
        except Exception as e:
            return {"status": 0, "error": str(e)}

    def read_room(self, room: str, since: int = None, wait: int = None, as_json: bool = True) -> dict:
        """
        Reads messages from a room.
        """
        params = {}
        if since is not None:
            params["since"] = str(since)
        if wait is not None:
            params["wait"] = str(wait)
        if as_json:
            params["format"] = "json"

        query_str = f"?{urllib.parse.urlencode(params)}" if params else ""
        url = f"{self.config.url}/r/{room}{query_str}"

        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw_body = resp.read().decode("utf-8")
                if as_json:
                    try:
                        return {"status": resp.status, "data": json.loads(raw_body)}
                    except json.JSONDecodeError:
                        return {"status": resp.status, "raw": raw_body}
                return {"status": resp.status, "raw": raw_body}
        except urllib.error.HTTPError as e:
            return {"status": e.code, "error": e.read().decode("utf-8")}
        except urllib.error.URLError as e:
            return {"status": 0, "error": f"Network unreachable: {e.reason}"}
        except Exception as e:
            return {"status": 0, "error": str(e)}

    def set_note(self, ns: str, key: str, value: str, if_val: str = None, if_absent: bool = False) -> dict:
        """
        Writes a note to /kv/<ns>/<key>.
        """
        url = f"{self.config.url}/kv/{ns}/{key}"
        payload = {"value": value}
        if if_absent:
            payload["if_absent"] = True
        elif if_val is not None:
            payload["if"] = if_val

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return {"status": resp.status, "body": resp.read().decode("utf-8")}
        except urllib.error.HTTPError as e:
            return {"status": e.code, "error": e.read().decode("utf-8")}
        except urllib.error.URLError as e:
            return {"status": 0, "error": f"Network unreachable: {e.reason}"}
        except Exception as e:
            return {"status": 0, "error": str(e)}

    def get_note(self, ns: str, key: str) -> dict:
        """
        Reads a note from /kv/<ns>/<key>.
        """
        url = f"{self.config.url}/kv/{ns}/{key}"
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return {"status": resp.status, "value": resp.read().decode("utf-8")}
        except urllib.error.HTTPError as e:
            return {"status": e.code, "error": e.read().decode("utf-8")}
        except urllib.error.URLError as e:
            return {"status": 0, "error": f"Network unreachable: {e.reason}"}
        except Exception as e:
            return {"status": 0, "error": str(e)}
