"""
launcher.py — Rad AI Automation Launcher
=========================================
Downloads the automation script from the secure server and runs it.

First-time setup
-----------------
1. pip install -r requirements.txt
2. Double-click launch.bat  (or: python launcher.py -f)
   - On first run it will ask for your name and email
   - Your request goes to the admin for approval
   - Once approved, you'll receive a token — paste it here when prompted
   - After that, runs automatically every time with no extra steps

If you already have a token
----------------------------
Create a .env file next to this file with:
    RADAI_TOKEN=tok_your_token_here
"""

import os
import sys
import hashlib
import urllib.request
import urllib.parse
import json
import time

# ── Load .env ─────────────────────────────────────────────────────────────────
_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
_env: dict[str, str] = {}
if os.path.exists(_ENV_FILE):
    with open(_ENV_FILE, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                _env[_k.strip()] = _v.strip().strip('"').strip("'")

RADAI_TOKEN  = _env.get("RADAI_TOKEN") or os.environ.get("RADAI_TOKEN", "")
SERVER_URL   = _env.get("RADAI_SERVER", "https://siliconhealth-website.vercel.app")
SCRIPT_FILE  = "v3_dose.py"
SKIP_UPDATE  = _env.get("SKIP_UPDATE", "0").lower() in ("1", "true", "yes")

CACHE_DIR     = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
CACHED_SCRIPT = os.path.join(CACHE_DIR, SCRIPT_FILE)
TOKEN_FILE    = _ENV_FILE  # save token back to .env

# ── Helpers ────────────────────────────────────────────────────────────────────
def _post(path: str, payload: dict) -> dict:
    url  = f"{SERVER_URL}{path}"
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def _get(path: str) -> dict:
    url = f"{SERVER_URL}{path}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def _download_raw(path: str) -> bytes:
    url = f"{SERVER_URL}{path}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]

def _save_token(token: str) -> None:
    """Append/update RADAI_TOKEN in the .env file."""
    lines = []
    found = False
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, encoding="utf-8") as f:
            lines = f.readlines()
        for i, l in enumerate(lines):
            if l.startswith("RADAI_TOKEN="):
                lines[i] = f"RADAI_TOKEN={token}\n"
                found = True
                break
    if not found:
        lines.append(f"RADAI_TOKEN={token}\n")
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"[Launcher] Token saved to .env")

# ── Access request flow ────────────────────────────────────────────────────────
def request_access() -> str:
    """Walk user through requesting access. Returns the approved token."""
    print("\n" + "="*60)
    print("  Voxel Helper — Access Required")
    print("="*60)
    print("\nYou don't have an access token yet.")
    print("Enter your details to request a trial:\n")

    name  = input("  Your full name:   ").strip()
    email = input("  Your work email:  ").strip()

    if not name or not email:
        print("\n[Error] Name and email are required.")
        sys.exit(1)

    print("\n[Launcher] Submitting request...")
    try:
        res = _post("/api/radai/request", {"name": name, "email": email, "machine": os.environ.get("COMPUTERNAME", "unknown")})
        request_id = res.get("request_id", "")
    except Exception as e:
        print(f"\n[Error] Could not submit request: {e}")
        print("Check your internet connection and try again.")
        sys.exit(1)

    print("\n✓ Request submitted!")
    print(f"  The admin will review and approve your access.")
    print(f"  Waiting for approval (this window will update automatically)...\n")

    # Poll for approval every 30 seconds (up to 24 hours)
    POLL_INTERVAL = 30
    MAX_POLLS     = 2880  # 24 hours
    for i in range(MAX_POLLS):
        time.sleep(POLL_INTERVAL)
        try:
            status = _get(f"/api/radai/status?id={urllib.parse.quote(request_id)}")
            if status.get("status") == "approved":
                token = status["token"]
                print(f"\n✓ Access approved! Token: {token}")
                _save_token(token)
                return token
            elif status.get("status") == "denied":
                print("\n✗ Your access request was denied.")
                print("  Contact the administrator for more information.")
                sys.exit(1)
            else:
                if (i + 1) % 4 == 0:  # print every 2 minutes
                    print(f"  Still waiting... ({(i+1)*POLL_INTERVAL//60}m elapsed)")
        except Exception:
            pass  # transient network error — keep polling

    print("\n[Error] Timed out waiting for approval.")
    print("  You can restart this launcher later — your request is still pending.")
    sys.exit(1)

# ── Download script ────────────────────────────────────────────────────────────
def download_script(token: str) -> bool:
    """Download v3_dose.py using the token. Returns True on success."""
    try:
        print("[Launcher] Checking for updates...")
        data = _download_raw(f"/api/radai/download?token={urllib.parse.quote(token)}")
        os.makedirs(CACHE_DIR, exist_ok=True)

        cached_hash = ""
        if os.path.exists(CACHED_SCRIPT):
            with open(CACHED_SCRIPT, "rb") as f:
                cached_hash = _hash(f.read())

        if _hash(data) != cached_hash:
            with open(CACHED_SCRIPT, "wb") as f:
                f.write(data)
            print(f"[Launcher] Script updated  ({len(data):,} bytes)")
        else:
            print("[Launcher] Already up to date.")
        return True

    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("\n[Launcher] ERROR: Your access token is invalid or has been revoked.")
            print("  Contact the administrator.")
        else:
            print(f"\n[Launcher] Server error: {e.code}")
            if os.path.exists(CACHED_SCRIPT):
                print("[Launcher] Using cached version.")
                return True
        return False
    except Exception as e:
        if os.path.exists(CACHED_SCRIPT):
            print(f"[Launcher] Update failed ({e}) — using cached version.")
            return True
        print(f"\n[Launcher] FATAL: Cannot download script and no cache exists.\n  {e}")
        return False

# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    token = RADAI_TOKEN

    # No token → request access
    if not token:
        token = request_access()

    # Download (unless skipped)
    if not SKIP_UPDATE:
        ok = download_script(token)
        if not ok:
            sys.exit(1)
    elif not os.path.exists(CACHED_SCRIPT):
        ok = download_script(token)
        if not ok:
            sys.exit(1)

    print(f"[Launcher] Running {SCRIPT_FILE}  (args: {sys.argv[1:]})\n")
    import runpy
    sys.argv = [CACHED_SCRIPT] + sys.argv[1:]
    runpy.run_path(CACHED_SCRIPT, run_name="__main__")
