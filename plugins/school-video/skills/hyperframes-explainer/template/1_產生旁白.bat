@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PY=python"
%PY% --version >nul 2>&1 || set "PY=py"
%PY% -c "import edge_tts" >nul 2>&1 || %PY% -m pip install edge-tts
echo 正在產生台灣腔旁白（需要網路）...
%PY% tools\tts.py
if errorlevel 1 (echo. & echo *** 發生錯誤，請把上面的訊息截圖給 Claude ***) else (echo. & echo === 完成！回到 Claude 說「旁白好了」，或接著雙擊 2_組畫面並算圖.bat ===)
pause
