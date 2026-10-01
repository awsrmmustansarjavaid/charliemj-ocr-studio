@echo off
REM =============================================================================
REM build.bat - builds the portable Windows app on your own PC
REM
REM What it does:
REM   1. Installs the pinned Python dependencies (requirements-build.txt)
REM   2. Runs the unit tests (stops if any test fails)
REM   3. Runs PyInstaller -> dist\CharlieMJ-OCR\CharlieMJ-OCR.exe
REM   4. Copies the "tesseract" folder next to the .exe so OCR works offline
REM   5. Writes SHA256SUMS.txt so you (or anyone) can verify the files
REM
REM Before running, create a folder named "tesseract" beside this file that holds:
REM   tesseract\tesseract.exe  (+ all its .dll files)
REM   tesseract\tessdata\eng / tur / urd / ara / fas .traineddata
REM (See docs\INSTALLATION.md for download links and details.)
REM =============================================================================

REM Step 1 - dependencies; jump to the error handler if pip fails
pip install -r requirements-build.txt || goto :err

REM Step 2 - unit tests (pure Python, no OCR engine needed)
python -m unittest discover -s tests || goto :err

REM Step 3 - build a windowed (no console), one-folder app.
REM   --noupx                 never compress with UPX (UPX-packed exes trigger antivirus alarms)
REM   --version-file          embeds publisher/product info shown in the exe's Details tab
REM   --collect-all customtkinter  bundles the theme files the UI needs
pyinstaller --noconfirm --noconsole --onedir --noupx --name CharlieMJ-OCR ^
  --version-file version_info.txt --collect-all customtkinter main.py || goto :err

REM Step 4 - copy Tesseract into the output folder (/E subfolders, /I treat as dir, /Y overwrite)
xcopy /E /I /Y tesseract dist\CharlieMJ-OCR\tesseract

REM Step 5 - checksum of the main exe (PowerShell is built into Windows)
powershell -NoProfile -Command "Get-FileHash dist\CharlieMJ-OCR\CharlieMJ-OCR.exe -Algorithm SHA256 | ForEach-Object { $_.Hash + '  CharlieMJ-OCR.exe' } | Set-Content dist\CharlieMJ-OCR\SHA256SUMS.txt"

echo.
echo Done! Portable app: dist\CharlieMJ-OCR\CharlieMJ-OCR.exe
echo Copy the WHOLE CharlieMJ-OCR folder anywhere (Desktop / USB drive).
pause
exit /b

REM Error handler reached via "goto :err" above
:err
echo Build failed. Read the messages above.
pause
