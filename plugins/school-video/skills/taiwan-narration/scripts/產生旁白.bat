@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem 雙擊執行：用 edge-tts 產生台灣腔旁白（需要網路）。tw_tts.py 和 lines.json 要放在同一個資料夾。
set "PY=python"
%PY% --version >nul 2>&1 || set "PY=py"
%PY% --version >nul 2>&1 || (echo 找不到 Python，請先安裝：winget install Python.Python.3.13 & pause & exit /b 1)
%PY% -c "import edge_tts" >nul 2>&1 || %PY% -m pip install edge-tts
echo 正在產生旁白...
%PY% tw_tts.py lines.json %*
if errorlevel 1 (echo. & echo *** 發生錯誤，請把上面的訊息截圖給 Claude ***) else (echo. & echo === 完成！可以關閉這個視窗，回到 Claude 說「旁白好了」 ===)
pause
