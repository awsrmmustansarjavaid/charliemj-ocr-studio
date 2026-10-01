"""
local_ai.py - OPTIONAL local AI through Ollama (https://ollama.com).

Why Ollama?
  * Runs the model on YOUR PC - no cloud, no API key, no account.
  * It is a separate program, so this app stays small (no model is bundled).
  * Uses only the Python standard library (urllib): fewer dependencies.

Security: only localhost addresses are accepted, so text and images can never
be sent to a remote server by accident.
"""
import base64
import io
import json
import urllib.error
import urllib.parse
import urllib.request

_LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")


def _base(url: str) -> str:
    """Validate that the URL points to this computer and return it without a trailing slash."""
    host = urllib.parse.urlparse(url).hostname
    if host not in _LOCAL_HOSTS:
        raise RuntimeError("For your privacy only a local Ollama address (localhost / 127.0.0.1) is allowed.")
    return url.rstrip("/")


def status(url: str):
    """Check the server. Returns (ok, [installed model names], message)."""
    try:
        with urllib.request.urlopen(_base(url) + "/api/tags", timeout=4) as r:
            models = [m["name"] for m in json.load(r).get("models", [])]
        if models:
            return True, models, f"Ollama is running · {len(models)} model(s) installed"
        return True, [], "Ollama is running but has no models. Run:  ollama pull gemma3:4b"
    except RuntimeError as e:
        return False, [], str(e)
    except Exception:
        return False, [], "Ollama is not running. Install it from ollama.com, then run:  ollama pull gemma3:4b"


def generate(url: str, model: str, prompt: str, image=None, timeout: int = 300) -> str:
    """Ask the local model. Pass a PIL image to use a vision-capable model (e.g. gemma3)."""
    payload = {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.2}}
    if image is not None:
        buf = io.BytesIO()
        image.convert("RGB").save(buf, "JPEG", quality=90)
        payload["images"] = [base64.b64encode(buf.getvalue()).decode()]
    req = urllib.request.Request(_base(url) + "/api/generate", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)["response"].strip()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(f"Model '{model}' is not installed. Run:  ollama pull {model}") from None
        raise RuntimeError(f"Ollama error {e.code}") from None
    except urllib.error.URLError:
        raise RuntimeError("Ollama is not running. Start it, then try again.") from None
