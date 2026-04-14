# Tesseract OCR — Windows Setup

The automation uses Tesseract to read CT radiation dose values from PACS screen captures.

## Install

1. Download the Windows installer from:  
   **https://github.com/UB-Mannheim/tesseract/wiki**  
   (Choose the latest `tesseract-ocr-w64-setup-*.exe`)

2. Run the installer. Default install path:  
   `C:\Program Files\Tesseract-OCR\`

3. Add Tesseract to your system PATH, **or** set the path explicitly in Python (not needed if PATH is set):
   ```python
   import pytesseract
   pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
   ```

4. Verify it works:
   ```
   tesseract --version
   ```

## Notes

- Only the **English** language pack is needed (installed by default).
- No special configuration is required — the automation handles OCR settings internally.
