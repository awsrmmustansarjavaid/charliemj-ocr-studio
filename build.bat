@echo off
REM =============================================================================
REM build.bat - builds the portable Windows app on your own PC
REM
REM What it does:
REM   1. Installs the Python dependencies from requirements.txt
REM   2. Runs PyInstaller to create dist\CharlieMJ-OCR\CharlieMJ-OCR.exe
REM   3. Copies the "tesseract" folder next to the .exe so OCR works offline
REM
REM Before running, create a folder named "tesseract" beside this file that holds:
REM   tesseract\tesseract.exe  (+ all its .dll files)
REM   tesseract\tessdata\eng / tur / urd / ara / fas .traineddata
REM (See docs\INSTALLATION.md for download links and details.)
REM =============================================================================

REM Step 1 - install dependencies; jump to the error handler if pip fails
pip install -r requirements.txt || goto :err

REM Step 2 - build a windowed (no console) one-folder app.
REM --collect-all customtkinter bundles the theme/asset files the UI needs.
pyinstaller --noconsole --onedir --name CharlieMJ-OCR --collect-all customtkinter main.py || goto :err

REM Step 3 - copy Tesseract into the output folder (/E subfolders, /I treat as dir, /Y overwrite)
xcopy /E /I /Y tesseract dist\CharlieMJ-OCR\tesseract

echo.
echo Done! Portable app: dist\CharlieMJ-OCR\CharlieMJ-OCR.exe
echo Copy the WHOLE CharlieMJ-OCR folder anywhere (Desktop / USB drive).
pause
exit /b

REM Error handler reached via "goto :err" above
:err
echo Build failed. Read the messages above.
pause
