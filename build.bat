@echo off
REM =============================================================================
REM build.bat - builds the portable Windows app on your own PC
REM =============================================================================

pip install -r requirements-build.txt || goto :err
python -m unittest discover -s tests || goto :err

REM Explicitly collect the whole app package so runtime imports such as
REM app.selector cannot be omitted from the frozen EXE.
python -c "import app.selector; print('app.selector import OK')" || goto :err
pyinstaller --noconfirm --noconsole --onedir --noupx --name CharlieMJ-OCR ^
  --version-file version_info.txt --collect-all customtkinter --collect-submodules app main.py || goto :err

xcopy /E /I /Y tesseract dist\CharlieMJ-OCR\tesseract
powershell -NoProfile -Command "Get-FileHash dist\CharlieMJ-OCR\CharlieMJ-OCR.exe -Algorithm SHA256 | ForEach-Object { $_.Hash + '  CharlieMJ-OCR.exe' } | Set-Content dist\CharlieMJ-OCR\SHA256SUMS.txt"

echo.
echo Done! Portable app: dist\CharlieMJ-OCR\CharlieMJ-OCR.exe
echo Copy the WHOLE CharlieMJ-OCR folder anywhere (Desktop / USB drive).
pause
exit /b

:err
echo Build failed. Read the messages above.
pause
