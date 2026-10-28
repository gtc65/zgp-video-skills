---
name: hyperframes-explainer
description: 用 HyperFrames（HTML＋GSAP 動畫算成影片）做校園說明／宣導／比賽規則影片：台灣腔旁白、字幕、圖示卡片、資訊表、原創配樂，一鍵 bat 產生。使用者要做說明影片、宣導影片、規則介紹、動畫簡報影片時使用。
---

# HyperFrames 說明影片（動畫字卡＋台灣腔旁白）

適合「把一份計畫、規則、宣導內容講清楚」的 1–4 分鐘 16:9 影片：畫面是程式畫的卡片、圖示、資訊表，配台灣腔旁白和逐句字幕。所有回應與介面文字使用繁體中文。

流程（範本在 `template/`，實測可算圖）：

```
tools/content.py（台詞＋畫面內容）
  → 1_產生旁白.bat（tools/tts.py：edge-tts 台灣腔 → assets/voice/narration.wav＋cues.json）
  → 2_組畫面並算圖.bat（setup_assets 字型/GSAP → build.py 產生 index.html → music.py 配樂 → hyperframes render → loudnorm −16 LUFS）
  → 成品/影片.mp4
```

## 0. 需要的軟體（Windows，PowerShell）

```powershell
winget install OpenJS.NodeJS.LTS      # Node 22 以上
winget install Gyan.FFmpeg
winget install Python.Python.3.13
python -m pip install edge-tts fonttools brotli numpy playwright
```
- HyperFrames 不用先裝：bat 用 `npx --yes hyperframes@0.8.169`（鎖版本；升級前先用短片測試）。
- 中文字型：建議安裝 Noto Sans TC；沒有時會退回微軟正黑體（只在本機算圖用，不要把 assets/fonts 公開散布）。
- 出現「已停用指令碼執行」：`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`。

## 1. 需求確認（用 AskUserQuestion，一次問完）

- 主題與原始資料（計畫書、公文、簡報）；對象年級；片長
- 旁白聲音（女聲曉臻／男聲雲哲）、要不要中英混用
- 主色（學校或活動代表色）；要放的照片（人物照解析度太低會糊，先問有沒有高解析版）
- 交付資料夾

## 2. 開專案、寫內容

1. 把 `template/` 整個複製到使用者的專案資料夾（例如 `<資料夾>\<片名>\`）。
2. 改 `tools/content.py`：
   - `SCENES` 每個場景選一個 `layout`：`title`（片名）、`bullets`（2–4 張圖示卡）、`steps`（步驟）、`info`（日期時間地點表）、`big`（超大數字）、`outro`（片尾）。
   - 旁白一句一個重點；「｜」切字幕；數字、教室編號、日期在 `say` 寫成國字念法（細節見 `taiwan-narration` 技能）。
   - `cue` 指定卡片在第幾句第幾段字幕出現，畫面才會「說到才出現」。
   - 片尾 `note` 保留「旁白為 AI 語音合成，配樂由程式生成」。
   - 範例內容（日期、地點）是示意，**一律換成使用者給的資料**，沒有的資訊不要編。
3. 先給使用者看「場景表」（場景、畫面、旁白）確認，再產生旁白。

## 3. 旁白

- Windows 本機：雙擊 `1_產生旁白.bat`。
- Cowork 雲端連不到 edge-tts：請使用者在 Windows 雙擊 bat；等待時可以先 `python tools/tts.py --dry` 用估計長度排畫面（真旁白產生後要重跑 build）。

## 4. 畫面與預覽

```bash
python tools/setup_assets.py      # 字型子集＋GSAP（台詞有新字就要重跑）
python tools/build.py             # → index.html
python tools/snap.py 2,10,25 review   # 指定秒數截圖，看版面
```
- 內建版型不夠用時，在 `build.py` 的 `CUSTOM` 為該場景寫函式：用 `scene()` 放 HTML，再用 `appear／pop／grow／stamp／pulse` 搭配 `L(場景,句)`、`C(場景,句,段)` 的時間加動畫。
- 圖示用自繪 SVG（`I` 字典），不要用 emoji 或別人的商標。
- 換主題色：改 `style.css` 的 `:root` 與 `build.py` 的 `COLORS`。三色原則：主色、強調色、淡背景。

## 5. 算圖

- Windows：雙擊 `2_組畫面並算圖.bat`（約 1 分鐘片長 10–20 分鐘，看電腦）。
- Cowork 雲端（Linux）：
  ```bash
  export HYPERFRAMES_BROWSER_PATH=$(ls /opt/pw-browsers/chromium_headless_shell-*/*/chrome-headless-shell | head -1)
  python tools/build.py && python tools/music.py
  npx --yes hyperframes@0.8.169 render -q delivery -o 成品/影片_raw.mp4
  ffmpeg -y -i 成品/影片_raw.mp4 -c:v copy -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:a aac -b:a 192k 成品/影片.mp4
  ```
  雲端約 3–5 fps（43 秒片約 7 分鐘）。雲端下載 GSAP 時 cdnjs 會被擋，setup_assets.py 會自動改用 npm registry。

## 6. 驗收（每次都做）

1. 抽 6–10 格看：字沒截斷、卡片沒蓋到字幕、場景切換沒有殘影。
2. 成品響度 −16±1 LUFS（`ffmpeg -i 影片.mp4 -af ebur128 -f null -`）。
3. 請使用者完整看一次、聽一次。
4. 在專案寫紀錄：場景表、改過的台詞、踩坑。

## 踩坑速查

| 症狀 | 處理 |
|---|---|
| 新加的字變成別的字型 | 重跑 `tools/setup_assets.py`（字型是子集） |
| 動畫抖動、lint 報錯 | 不要用 GSAP 動 `letterSpacing`；只動 opacity／x／y／scale／rotation |
| Windows 寫 json 變亂碼 | 一律 `encoding="utf-8"`（範本已處理） |
| 算圖後音量很小 | bat 最後的 loudnorm 已處理；自己 render 要記得做 |
| 照片放大後很糊 | 原圖太小；請使用者提供高解析版，或縮小顯示尺寸 |
| `npx` 找不到 | Node 沒裝好或沒重開視窗；`node -v` 要 v22 以上 |
| 卡片太早出現 | 在 content.py 寫 `cue` |
