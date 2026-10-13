@echo off
REM Mitra Mobile Repair Assistant - EXE builder (Windows)
cd /d "%~dp0"
if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat
python -m pip install -r requirements.txt
for /f "delims=" %%i in ('python -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))"') do set CTK=%%i
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name MitraMobileRepairAssistant ^
  --add-data "%CTK%;customtkinter" ^
  app.py
echo.
echo Build complete: dist\MitraMobileRepairAssistant.exe
echo NOTE: platform-tools folder ko EXE ke bagal me rakhein (dist\platform-tools\adb.exe).
pause
