# Rad AI Automation

Automation tool that monitors Epic (Hyperspace), pre-fetches prior study data from Clario, extracts CT radiation dose values via OCR from PACS popup windows, and pastes everything into the Rad AI Reporting comparison field.

## Prerequisites

- **Windows 10/11** (uses Win32 / UIA APIs)
- **Python 3.10+** — [python.org](https://www.python.org/downloads/)
- **Tesseract OCR** — see [setup_tesseract.md](setup_tesseract.md)
- **Google Chrome** launched with `--remote-debugging-port=9222` (for Clario prior extraction)

## Setup

### 1. Clone this repo
```
git clone https://github.com/YOUR_USERNAME/radai-automation.git
cd radai-automation
```

### 2. Install Python dependencies
```
pip install -r requirements.txt
```

### 3. Create your `.env` file
Copy the example and fill in your credentials:
```
copy .env.example .env
```
Edit `.env`:
```
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx   # PAT with read access to source repo (provided separately)
GITHUB_USER=moma-spec                   # GitHub username of the source repo owner
GITHUB_REPO=radai-automation-src        # Name of the private source repo
SCRIPT_FILE=v3_dose.py
```

> The `.env` file is in `.gitignore` — it never gets committed.

### 4. Run
Double-click `launch.bat`, or from terminal:
```
python launcher.py          # without prior popup
python launcher.py -f       # with Clario prior findings popup (recommended)
```

## Hotkeys

| Key | Action |
|-----|--------|
| `F10` | Toggle the Clario prior findings popup |
| `F12` | Restart the automation (fresh state) |

## Chrome Setup (for Clario prior extraction)

Add `--remote-debugging-port=9222` to Chrome's shortcut target:
```
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```
Then open Chrome and navigate to Clario normally.

## Updating

The launcher checks for updates every launch automatically.  
To skip the update check: set `SKIP_UPDATE=1` in your `.env`.

## Troubleshooting

- **No Clario priors extracted**: Ensure Chrome is running with `--remote-debugging-port=9222` and the Clario tab is open.
- **Dose not pasting**: Open the PACS dose popup (Quick Window / Patient Protocol) while a CT study is loaded in Rad AI.
- **Rad AI window not found**: Ensure Rad AI Reporting is open and visible (not minimized behind a fullscreen PACS viewer).
