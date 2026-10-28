# 校園影片製作技能（Claude Skills）

給 Claude（Claude Code、Claude 桌面版 Cowork、claude.ai）使用的三個影片製作技能，專為台灣學校的說明影片、活動回顧片設計。旁白一律台灣腔，畫面不用 AI 生成，配樂由程式原創，沒有版權疑慮。

| 技能 | 用途 | 你可以這樣跟 Claude 說 |
|---|---|---|
| **taiwan-narration** 台灣腔旁白 | edge-tts 曉臻／曉雨／雲哲，中英混用、讀音修正、逐句字幕時間軸 | 「幫這段稿子配台灣腔旁白」 |
| **photo-recap-video** 照片回顧片 | 活動照片 → 推拉運鏡、資訊字卡、字幕、旁白、配樂、−16 LUFS、LINE 版 | 「用這個資料夾的照片做運動會回顧影片」 |
| **hyperframes-explainer** 動畫說明片 | HTML＋GSAP 動畫算成影片：圖示卡片、步驟、資訊表、字幕、旁白，雙擊 bat 產生 | 「把這份比賽計畫做成三分鐘說明影片」 |

## 安裝

### A. Claude Code（建議：用外掛市集，之後一行更新）

在 Claude Code 裡輸入：

```
/plugin marketplace add gtc65/zgp-video-skills
/plugin install school-video@zgp-video-skills
```

之後要更新：`/plugin marketplace update zgp-video-skills`。

### B. Claude Code（直接複製成個人技能＋自動裝 Python 套件）

Windows PowerShell：

```powershell
irm https://raw.githubusercontent.com/gtc65/zgp-video-skills/main/install/install.ps1 | iex
```

macOS／Linux／WSL：

```bash
curl -fsSL https://raw.githubusercontent.com/gtc65/zgp-video-skills/main/install/install.sh | bash
```

技能會放在 `~/.claude/skills/`（Windows：`%USERPROFILE%\.claude\skills\`）。A 和 B 擇一即可，兩個都裝會出現重複的技能。

### C. Claude 桌面版（Cowork）／claude.ai

1. 下載三個 zip（每個技能一個）：
   [taiwan-narration.zip](https://github.com/gtc65/zgp-video-skills/raw/main/dist/taiwan-narration.zip)、
   [photo-recap-video.zip](https://github.com/gtc65/zgp-video-skills/raw/main/dist/photo-recap-video.zip)、
   [hyperframes-explainer.zip](https://github.com/gtc65/zgp-video-skills/raw/main/dist/hyperframes-explainer.zip)
2. claude.ai → 設定 → Capabilities（功能）→ Skills → 上傳 zip。
3. 技能存在帳號裡，同一個帳號的每台電腦都能用，不用每台裝。

## 每台電腦需要的軟體（Windows）

```powershell
winget install Python.Python.3.13
winget install Gyan.FFmpeg
winget install OpenJS.NodeJS.LTS        # 只有動畫說明片需要
python -m pip install edge-tts pillow fonttools brotli numpy mido playwright
python -m playwright install chromium
```

裝完重開 PowerShell。`python` 如果打開微軟商店：設定 → 應用程式 → 進階應用程式設定 → 應用程式執行別名，關掉 python。

## 重要限制

- **edge-tts 要連 `speech.platform.bing.com`**。Cowork 的雲端工作區連不到，所以在 Cowork 裡，Claude 會把 `產生旁白.bat` 寫進你的資料夾，請你在 Windows 雙擊產生旁白，再繼續剪接。Claude Code 在自己電腦上跑則可直接產生。
- 旁白是 AI 語音合成，片尾請保留註明。edge-tts 呼叫 Microsoft 線上服務，學校教學使用沒問題；商業使用前請自行確認服務條款。
- 學生肖像與姓名：預設不顯示學生姓名；露臉與否依學校規定，開工時 Claude 會先問。
- 照片回顧片的配樂需要 FluidSynth＋GM 音色庫（Linux／雲端 `apt-get install fluidsynth fluid-soundfont-gm`）；Windows 上建議交給雲端或 WSL 產生。

## 目錄

```
.claude-plugin/marketplace.json       外掛市集
plugins/school-video/
  .claude-plugin/plugin.json
  skills/
    taiwan-narration/                 SKILL.md、scripts/tw_tts.py、產生旁白.bat、templates/lines.json
    photo-recap-video/                SKILL.md、scripts/（contact_sheet、cards、compose_music、assemble、deliver）、templates/
    hyperframes-explainer/            SKILL.md、template/（整個可複製的專案範本＋兩個 bat）
install/                              install.ps1、install.sh
dist/                                 三個技能的 zip（上傳 claude.ai 用；改內容後跑 python tools/build_zips.py）
```

## 授權

MIT（見 [LICENSE](LICENSE)）。第三方軟體、字型與模型不包含在本 repo，見 [NOTICE.md](NOTICE.md)。
