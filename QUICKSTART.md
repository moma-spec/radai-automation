# Voxel Helper — Quick Start Guide

> **Time to set up: ~10 minutes**
> Everything you need to get the Rad AI automation running on your workstation.

---

## Step 1: Install Python (one-time)

1. Go to **https://www.python.org/downloads/**
2. Download **Python 3.11** or newer (click the big yellow button)
3. **IMPORTANT**: On the installer's first screen, check ✅ **"Add Python to PATH"**
4. Click "Install Now" and wait for it to finish

**Verify it works** — open Command Prompt and type:
```
python --version
```
You should see `Python 3.11.x` or similar.

---

## Step 2: Install Tesseract OCR (one-time)

Tesseract reads CT dose values from the PACS dose popup.

1. Go to **https://github.com/UB-Mannheim/tesseract/wiki**
2. Download the latest **64-bit** installer (`tesseract-ocr-w64-setup-*.exe`)
3. Run the installer — keep the default install path:
   ```
   C:\Program Files\Tesseract-OCR\
   ```
4. On the "Select Components" screen, only **English** is needed (already checked by default)

**Verify it works** — open a new Command Prompt and type:
```
tesseract --version
```

> **Note:** If `tesseract` is not recognized, add `C:\Program Files\Tesseract-OCR` to your system PATH, or simply restart your computer.

---

## Step 3: Set Up Chrome for Clario (one-time)

The automation reads prior study data from the Clario tab in Chrome. For this to work, Chrome must be launched with a special debugging flag.

### Option A — Modify your Chrome shortcut (recommended)

1. Right-click your **Google Chrome** shortcut → **Properties**
2. In the **Target** field, add this to the end (after the closing quote):
   ```
   --remote-debugging-port=9222
   ```
   So the full target looks like:
   ```
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
   ```
3. Click **OK**
4. **Close all Chrome windows completely**, then reopen Chrome from this shortcut

### Option B — Create a separate shortcut

1. Right-click Desktop → **New** → **Shortcut**
2. Paste this as the location:
   ```
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
   ```
3. Name it **"Chrome (Clario)"**
4. Use this shortcut whenever you need Clario + automation

### Verify it works

With Chrome open (using the modified shortcut), open a new tab and go to:
```
http://localhost:9222/json
```
If you see JSON text (a list of tabs), it's working.

---

## Step 4: Download the Launcher

1. Go to **https://github.com/moma-spec/radai-automation/archive/refs/heads/main.zip**
   *(Your admin will share this link or send you the zip directly)*
2. Extract the zip to any folder, e.g.:
   ```
   C:\RadAI\
   ```
   You should see these files inside:
   ```
   launch.bat
   launcher.py
   requirements.txt
   .env.example
   README.md
   setup_tesseract.md
   ```

---

## Step 5: First Run

1. **Double-click `launch.bat`**
2. On the first run, the launcher will:
   - ✅ Automatically install all Python dependencies (takes ~1 minute)
   - 🔑 Ask for your **name** and **work email** to request access
3. After submitting, **leave the window open** — it will poll every 30 seconds until an admin approves your request
4. Once approved, your token is saved automatically — you won't need to do this again

**That's it!** From now on, just double-click `launch.bat` each morning.

---

## Daily Workflow

1. Open **Chrome** (using the shortcut with the debugging flag)
2. Log into **Clario** in Chrome
3. Open **Epic** (Hyperspace) and **Rad AI Reporting**
4. **Double-click `launch.bat`** — the automation starts monitoring
5. Start reading!

### Hotkeys

| Key | Action |
|-----|--------|
| **F10** | Toggle the Clario prior findings popup on/off |
| **F12** | Restart the automation (fresh state) |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **"python is not recognized"** | Re-install Python and make sure **"Add to PATH"** is checked |
| **No Clario priors showing** | Make sure Chrome was opened with `--remote-debugging-port=9222` and Clario tab is open |
| **Dose not pasting** | Open the PACS dose popup (Quick Window / Patient Protocol) while a CT is loaded in Rad AI |
| **Rad AI window not found** | Make sure Rad AI Reporting is open and visible (not minimized) |
| **Token expired / revoked** | Delete the `.env` file and re-run `launch.bat` to request a new token |

---

## Need Help?

Contact your admin or email **support@siliconhealth.ai**
