@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PY=python"
%PY% --version >nul 2>&1 || set "PY=py"
%PY% -c "import fontTools, brotli, numpy" >nul 2>&1 || %PY% -m pip install fonttools brotli numpy
echo [1/4] 準備字型與 GSAP...
%PY% tools\setup_assets.py || goto :err
echo [2/4] 組畫面...
%PY% tools\build.py || goto :err
echo [3/4] 合成配樂...
%PY% tools\music.py || goto :err
echo [4/4] 算圖（約 10-40 分鐘，看片長）...
if not exist "成品" mkdir "成品"
call npx --yes hyperframes@0.8.169 render -q delivery -o "成品\影片_raw.mp4" || goto :err
echo 音量標準化（-16 LUFS）...
ffmpeg -y -loglevel error -i "成品\影片_raw.mp4" -c:v copy -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:a aac -b:a 192k "成品\影片.mp4" || goto :err
echo. & echo === 完成，影片在「成品」資料夾 ===
pause
exit /b 0
:err
echo. & echo *** 發生錯誤，請把上面的訊息截圖給 Claude ***
pause
exit /b 1
