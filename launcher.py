"""
launcher.py — Rad AI Automation Launcher
=========================================
Downloads the automation script from the secure server and runs it
entirely in memory. The source code is NEVER written to disk.

First-time setup
-----------------
1. Double-click launch.bat  (or: python launcher.py -f)
   - Dependencies are installed automatically on first run
   - On first run it will ask for your name and email
   - Your request goes to the admin for approval
   - Once approved, you'll receive a token — paste it here when prompted
   - After that, runs automatically every time with no extra steps

If you already have a token
----------------------------
Create a .env file next to this file with:
    RADAI_TOKEN=tok_your_token_here
"""

import os, sys, re, hashlib, json, time, threading
import urllib.request, urllib.parse, urllib.error

# ── Python version gate ────────────────────────────────────────────────────────
_PY = sys.version_info[:2]
if _PY < (3, 9):
    print(f"\n[FATAL] Python {_PY[0]}.{_PY[1]} is not supported.")
    print("        Please install Python 3.10 – 3.12 from https://www.python.org/")
    input("Press Enter to exit..."); sys.exit(1)
if _PY >= (3, 13):
    print(f"\n[WARNING] Python {_PY[0]}.{_PY[1]} detected.")
    print("          This app is tested on Python 3.10 – 3.12.")
    print("          Some libraries (PyTorch, pywinauto) may crash on 3.13+.")
    print("          Recommended: install Python 3.11 or 3.12.\n")

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

# Export .env keys to the process environment (without clobbering real env
# vars) so the automation and any child it spawns — e.g. the dictation app's
# server.py, which needs RADAI_TOKEN/RADAI_SERVER for the Gemini broker —
# see the same configuration.
for _k, _v in _env.items():
    os.environ.setdefault(_k, _v)

RADAI_TOKEN = _env.get("RADAI_TOKEN") or os.environ.get("RADAI_TOKEN", "")
SERVER_URL  = _env.get("RADAI_SERVER", "https://siliconhealth-website.vercel.app")
SKIP_UPDATE = _env.get("SKIP_UPDATE", "0").lower() in ("1", "true", "yes")
SCRIPT_FILE = "v3_dose.py"

CACHE_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
LOCAL_REQS  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")

# ── HTTP helpers ───────────────────────────────────────────────────────────────
def _auth_headers(token):
    # Token travels in the Authorization header (not the URL) so it never
    # lands in server/request logs; X-Machine lets the admin page show where
    # each token is being used.
    return {"Authorization": f"Bearer {token}",
            "X-Machine": os.environ.get("COMPUTERNAME", "unknown")}

def _post(path, payload):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(f"{SERVER_URL}{path}", data=data,
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def _get(path, headers=None):
    req = urllib.request.Request(f"{SERVER_URL}{path}", headers=headers or {})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def _get_bytes(path, headers=None):
    req = urllib.request.Request(f"{SERVER_URL}{path}", headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
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

# ── In-memory version extraction ──────────────────────────────────────────────
def _extract_version_from_source(source):
    """Read _VERSION and _BUILD_DATE from script source string."""
    ver, date = "?", "?"
    head = source[:2000]
    m = re.search(r'^_VERSION\s*=\s*["\']([^"\']+)["\']', head, re.M)
    if m: ver = m.group(1)
    m = re.search(r'^_BUILD_DATE\s*=\s*["\']([^"\']+)["\']', head, re.M)
    if m: date = m.group(1)
    return ver, date

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

# ── Download script into memory ────────────────────────────────────────────────
def download_script(token):
    """Download v3_dose.py into memory. Returns (source_bytes, updated)."""
    try:
        print("[Launcher] Checking for updates...")
        os.makedirs(CACHE_DIR, exist_ok=True)
        data = _get_bytes("/api/radai/download", headers=_auth_headers(token))

        # Compare hash with last-known hash (no source on disk — only the hash)
        hash_file = os.path.join(CACHE_DIR, ".script_hash")
        new_hash = _hash(data)
        old_hash = ""
        if os.path.exists(hash_file):
            with open(hash_file, "r") as f:
                old_hash = f.read().strip()

        if new_hash != old_hash:
            with open(hash_file, "w") as f:
                f.write(new_hash)
            print(f"[Launcher] Script updated  ({len(data):,} bytes)")
        else:
            print("[Launcher] Already up to date.")

        return data, True
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("\n[Launcher] ERROR: Token invalid or revoked. Contact the administrator.")
            return None, False
        print(f"[Launcher] Server error {e.code} — cannot start without script.")
        return None, False
    except Exception as e:
        print(f"\n[Launcher] FATAL: {e}")
        return None, False

def download_requirements(token):
    """Download requirements.txt (update local copy if server has newer)."""
    try:
        data = _get_bytes("/api/radai/download?file=requirements.txt",
                          headers=_auth_headers(token))
        old = open(LOCAL_REQS, "rb").read() if os.path.exists(LOCAL_REQS) else b""
        if _hash(data) != _hash(old):
            with open(LOCAL_REQS, "wb") as f:
                f.write(data)
            print("[Launcher] requirements.txt updated from server")
    except Exception:
        pass  # non-critical

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
        # Download NLTK tokenizer data required by sumy + Epic summarizer
        try:
            subprocess.check_call(
                [sys.executable, "-c",
                 "import nltk; nltk.download('punkt', quiet=True); nltk.download('punkt_tab', quiet=True)"],
                stdout=sys.stdout, stderr=sys.stderr
            )
        except Exception:
            print("[Launcher] Note: NLTK data download failed. Summarization may use fallback mode.")
        # Note: sentence-transformers model 'all-MiniLM-L6-v2' (~90MB) auto-downloads on first use
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(sentinel, "w") as f:
            f.write(req_hash)
        print("[Launcher] Dependencies installed successfully.\n")
    except subprocess.CalledProcessError as e:
        print(f"[Launcher] WARNING: pip install failed ({e}). Some features may not work.")

# ── Revocation watchdog ────────────────────────────────────────────────────────
def _start_revocation_watchdog(token, interval_sec=600):
    """Poll /api/radai/validate so a revoked token stops a RUNNING session,
    not just the next launch. Exits ONLY on an explicit 403 / active:false
    from the server — network errors, timeouts, and 5xx are ignored so a
    flaky connection can never kill a live reading session."""
    def _watch():
        while True:
            time.sleep(interval_sec)
            try:
                res = _get("/api/radai/validate", headers=_auth_headers(token))
                if res.get("active") is False:
                    print("\n[Launcher] Access revoked by administrator — exiting.")
                    os._exit(1)
            except urllib.error.HTTPError as e:
                if e.code == 403:
                    print("\n[Launcher] Access revoked by administrator — exiting.")
                    os._exit(1)
                # other HTTP errors: server hiccup, keep running
            except Exception:
                pass  # offline/transient — keep running
    threading.Thread(target=_watch, daemon=True, name="RevocationWatchdog").start()

# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    token = RADAI_TOKEN
    if not token:
        token = request_access()
    # Make token/server visible to the automation and its children (the
    # dictation server uses these to mint short-lived Vertex credentials).
    os.environ["RADAI_TOKEN"] = token
    os.environ.setdefault("RADAI_SERVER", SERVER_URL)

    # Download latest script into memory (never written to disk)
    script_data, ok = download_script(token)
    if not ok or not script_data:
        sys.exit(1)

    # Download requirements.txt (only this is written to disk — it's not sensitive)
    download_requirements(token)

    # Install/update dependencies
    _ensure_deps()

    # Decode source in memory
    source = script_data.decode("utf-8", errors="replace")
    del script_data  # free raw bytes

    # Extract version for display
    ver, date = _extract_version_from_source(source)
    print(f"[Launcher] v3_dose  v{ver}  built {date}  python {sys.version.split()[0]}")
    print(f"[Launcher] Running {SCRIPT_FILE}  (args: {sys.argv[1:]})\n")

    # Mid-session kill switch: admin revocation takes effect within ~10 min
    _start_revocation_watchdog(token)

    # Execute in memory — __file__ points to launcher dir so relative paths work
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.argv = [os.path.join(script_dir, SCRIPT_FILE)] + sys.argv[1:]
    code = compile(source, SCRIPT_FILE, "exec")
    del source  # free source string
    exec(code, {"__name__": "__main__", "__file__": sys.argv[0]})
