@echo off
REM =============================================================================
REM build.bat - builds the portable Windows app on your own PC
REM =============================================================================

pip install -r requirements-build.txt || goto :err
python -m unittest discover -s tests || goto :err

REM Verify the modules used by the real application entry point before freezing.
python -c "import app.ui, app.batch_runtime, app.complete_ocr, app.v2_truth, app.ocr_recovery; print('critical app imports OK')" || goto :err

REM Always start from a clean PyInstaller output. This prevents a stale build/spec
REM from producing an EXE that is missing a newly added app module such as app.ui.
if exist build rmdir /S /Q build
if exist dist rmdir /S /Q dist
if exist CharlieMJ-OCR.spec del /F /Q CharlieMJ-OCR.spec

REM Explicit hidden imports make the frozen entry point independent of PyInstaller
REM import-analysis changes. --collect-submodules app remains as the catch-all for
REM the rest of the application package.
pyinstaller --noconfirm --noconsole --onedir --noupx --name CharlieMJ-OCR ^
  --version-file version_info.txt --collect-all customtkinter --collect-submodules app ^
  --hidden-import app.ui --hidden-import app.batch_runtime --hidden-import app.complete_ocr ^
  --hidden-import app.v2_truth --hidden-import app.ocr_recovery --hidden-import app.languages ^
  --hidden-import app.workspace_ui --hidden-import app.menu_bar --hidden-import app.local_agents ^
  --hidden-import app.ai_center --hidden-import app.health_center --hidden-import app.settings_center ^
  --hidden-import app.automation_bot main.py || goto :err

if not exist dist\CharlieMJ-OCR\CharlieMJ-OCR.exe (
  echo ERROR: PyInstaller did not create the expected EXE.
  goto :err
)

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
exit /b 1
