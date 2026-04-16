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

import os, sys, hashlib, json, time
import urllib.request, urllib.parse, urllib.error

# ── Load .env ─────────────────────────────────────────────────────────────────
_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
_env: dict = {}
if os.path.exists(_ENV_FILE):
    with open(_ENV_FILE, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                _env[_k.strip()] = _v.strip().strip('"').strip("'")

RADAI_TOKEN = _env.get("RADAI_TOKEN") or os.environ.get("RADAI_TOKEN", "")
SERVER_URL  = _env.get("RADAI_SERVER", "https://siliconhealth-website.vercel.app")
SKIP_UPDATE = _env.get("SKIP_UPDATE", "0").lower() in ("1", "true", "yes")
SCRIPT_FILE = "v3_dose.py"

CACHE_DIR     = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
CACHED_SCRIPT = os.path.join(CACHE_DIR, SCRIPT_FILE)

# ── HTTP helpers ───────────────────────────────────────────────────────────────
def _post(path, payload):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(f"{SERVER_URL}{path}", data=data,
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def _get(path):
    with urllib.request.urlopen(f"{SERVER_URL}{path}", timeout=15) as r:
        return json.loads(r.read())

def _get_bytes(path):
    with urllib.request.urlopen(f"{SERVER_URL}{path}", timeout=30) as r:
        return r.read()

def _hash(data):
    return hashlib.sha256(data).hexdigest()[:16]

def _save_token(token):
    lines, found = [], False
    if os.path.exists(_ENV_FILE):
        with open(_ENV_FILE, encoding="utf-8") as f:
            lines = f.readlines()
        for i, l in enumerate(lines):
            if l.startswith("RADAI_TOKEN="):
                lines[i] = f"RADAI_TOKEN={token}\n"; found = True; break
    if not found:
        lines.append(f"RADAI_TOKEN={token}\n")
    with open(_ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("[Launcher] Token saved to .env")

# ── Access request flow ────────────────────────────────────────────────────────
def request_access():
    print("\n" + "="*60)
    print("  Voxel Helper — Access Required")
    print("="*60)
    print("\nYou don't have an access token yet.")
    print("Enter your details to request a trial:\n")
    name  = input("  Your full name:   ").strip()
    email = input("  Your work email:  ").strip()
    if not name or not email:
        print("\n[Error] Name and email are required."); sys.exit(1)

    print("\n[Launcher] Submitting request...")
    try:
        res = _post("/api/radai/request", {
            "name": name, "email": email,
            "machine": os.environ.get("COMPUTERNAME", "unknown")
        })
        request_id = res.get("request_id", "")
    except Exception as e:
        print(f"\n[Error] Could not reach server: {e}"); sys.exit(1)

    print("\n✓ Request submitted!")
    print("  Waiting for admin approval (checks every 30 seconds)...\n")

    for i in range(2880):  # poll up to 24 hours
        time.sleep(30)
        try:
            s = _get(f"/api/radai/status?id={urllib.parse.quote(request_id)}")
            if s.get("status") == "approved":
                token = s["token"]
                print(f"\n✓ Approved! Saving token...")
                _save_token(token)
                return token
            elif s.get("status") == "denied":
                print("\n✗ Access request was denied."); sys.exit(1)
            elif (i + 1) % 4 == 0:
                print(f"  Still waiting... ({(i+1)*30//60}m elapsed)")
        except Exception:
            pass
    print("\n[Error] Timed out. Restart launcher later — request is still pending.")
    sys.exit(1)

# ── Download script ────────────────────────────────────────────────────────────
def download_script(token):
    try:
        print("[Launcher] Checking for updates...")
        data = _get_bytes(f"/api/radai/download?token={urllib.parse.quote(token)}")
        os.makedirs(CACHE_DIR, exist_ok=True)
        old = open(CACHED_SCRIPT, "rb").read() if os.path.exists(CACHED_SCRIPT) else b""
        if _hash(data) != _hash(old):
            open(CACHED_SCRIPT, "wb").write(data)
            print(f"[Launcher] Script updated  ({len(data):,} bytes)")
        else:
            print("[Launcher] Already up to date.")
        return True
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("\n[Launcher] ERROR: Token invalid or revoked. Contact the administrator.")
            return False
        if os.path.exists(CACHED_SCRIPT):
            print(f"[Launcher] Server error {e.code} — using cached version."); return True
        return False
    except Exception as e:
        if os.path.exists(CACHED_SCRIPT):
            print(f"[Launcher] Update failed — using cached version."); return True
        print(f"\n[Launcher] FATAL: {e}"); return False

# ── Auto-install dependencies ──────────────────────────────────────────────────
def _ensure_deps():
    """Install pip requirements on first run (or when requirements.txt changes)."""
    req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    sentinel = os.path.join(CACHE_DIR, ".deps_installed")
    if not os.path.exists(req_file):
        return  # nothing to install

    # Hash requirements.txt to detect changes
    with open(req_file, "rb") as f:
        req_hash = _hash(f.read())

    # Skip if already installed with same hash
    if os.path.exists(sentinel):
        with open(sentinel, "r") as f:
            if f.read().strip() == req_hash:
                return

    print("[Launcher] Installing Python dependencies...")
    import subprocess
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", req_file],
            stdout=sys.stdout, stderr=sys.stderr
        )
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(sentinel, "w") as f:
            f.write(req_hash)
        print("[Launcher] Dependencies installed successfully.\n")
    except subprocess.CalledProcessError as e:
        print(f"[Launcher] WARNING: pip install failed ({e}). Some features may not work.")

# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    token = RADAI_TOKEN
    if not token:
        token = request_access()

    # Auto-install dependencies before first run
    _ensure_deps()

    if not SKIP_UPDATE:
        if not download_script(token):
            sys.exit(1)
    elif not os.path.exists(CACHED_SCRIPT):
        if not download_script(token):
            sys.exit(1)

    print(f"[Launcher] Running {SCRIPT_FILE}  (args: {sys.argv[1:]})\n")
    import runpy
    sys.argv = [CACHED_SCRIPT] + sys.argv[1:]
    runpy.run_path(CACHED_SCRIPT, run_name="__main__")
