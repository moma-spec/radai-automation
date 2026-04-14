"""
launcher.py — Rad AI Automation Launcher
=========================================
Downloads the automation script from the private source repo on first run,
caches it locally, and executes it.  Subsequent runs use the local cache
(internet not required if SKIP_UPDATE=1 in your .env).

Setup
-----
1. Create a .env file next to this file with:
       GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
       GITHUB_USER=your-github-username
       GITHUB_REPO=radai-automation-src
       SCRIPT_FILE=v3_dose.py
   (Get a Fine-grained PAT with Read access to Contents on the private repo)

2. pip install -r requirements.txt
3. python launcher.py            # normal start
   python launcher.py -f        # with prior-findings popup
"""

import os
import sys
import urllib.request
import hashlib

# ── Load .env manually (no python-dotenv dependency) ──────────────────────────
_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
_env: dict[str, str] = {}
if os.path.exists(_ENV_FILE):
    with open(_ENV_FILE, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                _env[_k.strip()] = _v.strip().strip('"').strip("'")

GITHUB_TOKEN = _env.get("GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
GITHUB_USER  = _env.get("GITHUB_USER")  or os.environ.get("GITHUB_USER",  "")
GITHUB_REPO  = _env.get("GITHUB_REPO")  or os.environ.get("GITHUB_REPO",  "radai-automation-src")
SCRIPT_FILE  = _env.get("SCRIPT_FILE")  or os.environ.get("SCRIPT_FILE",  "v3_dose.py")
SKIP_UPDATE  = _env.get("SKIP_UPDATE",  "0").lower() in ("1", "true", "yes")

CACHE_DIR    = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
CACHED_SCRIPT = os.path.join(CACHE_DIR, SCRIPT_FILE)

# ── Download helpers ───────────────────────────────────────────────────────────
def _raw_url() -> str:
    return (f"https://raw.githubusercontent.com/"
            f"{GITHUB_USER}/{GITHUB_REPO}/main/{SCRIPT_FILE}")

def _download() -> bytes:
    url = _raw_url()
    req = urllib.request.Request(url)
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"token {GITHUB_TOKEN}")
    req.add_header("User-Agent", "radai-launcher/1.0")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()

def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]

def _cached_hash() -> str:
    if not os.path.exists(CACHED_SCRIPT):
        return ""
    with open(CACHED_SCRIPT, "rb") as f:
        return _hash(f.read())

def update_script() -> bool:
    """Return True if script was updated or already up-to-date."""
    if not GITHUB_TOKEN or not GITHUB_USER:
        if os.path.exists(CACHED_SCRIPT):
            print("[Launcher] No GITHUB_TOKEN set — using cached script.")
            return True
        print("[Launcher] ERROR: GITHUB_TOKEN and GITHUB_USER must be set in .env")
        print("           See README.md → Setup for instructions.")
        return False
    try:
        print("[Launcher] Checking for updates...")
        data = _download()
        os.makedirs(CACHE_DIR, exist_ok=True)
        if _hash(data) != _cached_hash():
            with open(CACHED_SCRIPT, "wb") as f:
                f.write(data)
            print(f"[Launcher] Script updated  ({len(data):,} bytes)")
        else:
            print("[Launcher] Already up to date.")
        return True
    except Exception as e:
        if os.path.exists(CACHED_SCRIPT):
            print(f"[Launcher] Update failed ({e}) — using cached version.")
            return True
        print(f"[Launcher] FATAL: Cannot download script and no cache exists.\n  {e}")
        return False

# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not SKIP_UPDATE:
        ok = update_script()
        if not ok:
            sys.exit(1)
    elif not os.path.exists(CACHED_SCRIPT):
        print("[Launcher] SKIP_UPDATE=1 but no cached script found. Downloading anyway...")
        if not update_script():
            sys.exit(1)

    print(f"[Launcher] Running {SCRIPT_FILE}  (args: {sys.argv[1:]})\n")

    # Run the cached script, forwarding all CLI args (e.g. -f for popup)
    import runpy
    sys.argv = [CACHED_SCRIPT] + sys.argv[1:]
    runpy.run_path(CACHED_SCRIPT, run_name="__main__")
