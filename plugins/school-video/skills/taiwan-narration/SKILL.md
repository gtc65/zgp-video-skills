---
name: taiwan-narration
description: 幫影片、簡報或教學素材產生台灣腔中文旁白（edge-tts 曉臻／曉雨／雲哲，可中英混用），含讀音修正、時間軸 cues.json 和整條 narration.wav。使用者要旁白、配音、TTS、「台灣腔」「不要大陸腔」時使用。
---

# 台灣腔旁白（edge-tts）

用 Microsoft edge-tts 的台灣聲音產生旁白。一句一個檔，改一句只重做那一句。所有回應與介面文字使用繁體中文。

| 聲音代號 | voice | 適合 |
|---|---|---|
| `zh`（預設） | zh-TW-HsiaoChenNeural 曉臻 | 女聲，親切，說明片、活動回顧 |
| `zh2` | zh-TW-HsiaoYuNeural 曉雨 | 女聲，較年輕 |
| `male` | zh-TW-YunJheNeural 雲哲 | 男聲，沉穩，宣導片 |
| `en` | en-US-AvaNeural | 中英混用時的英文句 |
| `word` | en-US-AvaNeural −20% | 英文單字慢速示範 |

**不要用**：Kokoro、普通話腔的開源模型、或沒指定 zh-TW 的聲音。那些都是大陸腔，使用者會要求重做。

## 1. 先判斷在哪裡跑

edge-tts 要連 `speech.platform.bing.com`。**Cowork 雲端工作區和 Cowork 的裝置 VM 都連不到**（實測被擋），所以：

- **Claude Code 在使用者的 Windows 電腦上跑**：直接執行 `python scripts/tw_tts.py lines.json`。
- **Cowork（雲端）**：把 `scripts/tw_tts.py`、`scripts/產生旁白.bat` 和你寫好的 `lines.json` 寫進使用者連接的資料夾（例如 `<專案>\旁白製作\`），請使用者在 Windows **雙擊「產生旁白.bat」**，跑完回來說「旁白好了」，再把 `旁白\*.wav`（或 mp3）stage 回雲端使用。
- 先排畫面、還沒有真旁白時：`python tw_tts.py lines.json --dry` 用估計長度產生靜音檔與 `dry_cues.json`（檔名都是 `dry_` 開頭，不會蓋到真旁白），雲端也能跑。

## 2. 寫 lines.json

```json
{
 "out": "旁白",
 "voices": {"zh": {"voice": "zh-TW-HsiaoChenNeural", "rate": "+6%", "pitch": "+8Hz"}},
 "default": "zh",
 "lines": [
  {"id": "N1", "text": "南瓜燈亮起，｜搗蛋鬼登場！"},
  {"id": "N2", "text": "報名到 11/6 截止", "say": "報名到十一月六號截止"},
  {"id": "E1", "text": "Happy Halloween!", "v": "en", "gap": 1.0},
  {"id": "G3", "text": "注意！前方高能預警！", "rate": "-4%"}
 ],
 "timeline": {"lead": 1.2, "gap_line": 0.5, "tail": 3.0}
}
```

- `text` 是字幕原文，`｜` 是字幕斷行點（不會念出來）；`say` 是實際念法，只在要修讀音時寫。
- `rate`／`pitch` 可整個聲音設，也可單句覆寫。活潑的回顧片常用 `+6%`、`+8Hz`；國小低年級說明片用 `-3%` 到 `-6%`。
- `id` 用短代號（N1、G2…），之後剪接、字幕都靠它對應。

## 3. 產生

```bash
python scripts/tw_tts.py lines.json            # 每句 mp3；有 ffmpeg 時另存去頭尾靜音的 48k wav，並寫 report.json（每句長度）
python scripts/tw_tts.py lines.json --concat   # 再依 timeline 串成 narration.wav，輸出 cues.json（每句與每段字幕的起訖秒數）
python scripts/tw_tts.py lines.json --only N3  # 只重做 N3
python scripts/tw_tts.py --list zh-TW          # 列出聲音
```

需要：Python 3.9+、`python -m pip install edge-tts`、ffmpeg（`winget install Gyan.FFmpeg`；沒有 ffmpeg 只會產生 mp3）。重跑時只會重做文字或設定有改的句子。

固定時間軸的片子（每句一定要在某秒開口）：不要用 `--concat`，改由剪接工具依 `report.json` 的長度擺放，超時就縮短句子，真的不行才用 ffmpeg `atempo` 加速，上限 1.25 倍。

## 4. 驗收（每次都做）

1. 看 `report.json` 的每句長度，確認放得進畫面。
2. **聽寫比對**：能跑 ASR 時（雲端可用 sherpa-onnx + SenseVoice，模型從 GitHub releases 下載），把每句轉文字跟 `say` 比，列出不一樣的字給使用者。ASR 只用來找可疑處，口音和語氣交給使用者用耳朵判斷。
3. 請使用者至少完整聽一次，尤其是人名、地名、英文專有名詞。

## 5. 念錯的修法（改 `say`，字幕維持原文）

| 問題 | 改法 |
|---|---|
| 數字、日期、時間念怪 | 寫成國字：「11/6」→「十一月六號」、「08:00」→「早上八點」、「2026」→「二零二六」 |
| 教室編號、代碼 | 「中306」→「中三零六」 |
| 破音字念錯（例：「行」「重」「長」「和」） | `say` 裡換成讀音正確的同音字，或換一個說法避開那個字 |
| 英文縮寫被拼字或念成中文 | 「Level 1」→「Level one」；中英分開成兩句，英文那句用 `v: "en"` |
| 斷句不自然、太趕 | 在 `say` 加逗號，或拆成兩句並用 `gap` 控制停頓 |
| 一個字讀音怪但整句不想重錄 | 只重做那一句（`--only`）；真的要修單字，可用另一聲音念那個字後用 ffmpeg 剪接，做完一定要請使用者試聽 |

## 6. 交給剪接

- 有 `--concat`：直接用 `narration.wav`＋`cues.json`（`lines[].start/end`、`lines[].caps[]` 可直接做字幕）。
- 沒有：用每句 `旁白/<id>.wav` 自己擺；字幕長度依 `report.json`。
- 配樂要在旁白時壓低（sidechain ducking），整片最後統一 −16 LUFS、峰值 ≤ −1.5 dBTP。
- 片尾註明「旁白為 AI 語音合成」。

## 7. 進階選項（使用者要求才提）

- **離線、可以複製特定聲音**：BreezyVoice（MediaTek Research，台灣華語 TTS，github.com/mtkresearch/BreezyVoice，權重在 Hugging Face `MediaTek-Research/BreezyVoice`）。需要 NVIDIA GPU，依官方 README 安裝；**使用前先請使用者讀過官方授權**。
- **用文字設計聲音、精細控制情緒**：Breeze TTS 2（權重與產生的聲音限研究與非商業用途），需 NVIDIA 12GB 以上 VRAM。
- edge-tts 是呼叫 Microsoft 線上服務，學校教學用途沒問題；要商業使用前請使用者自行確認服務條款。

## 踩坑速查

| 症狀 | 處理 |
|---|---|
| `Cannot connect to host speech.platform.bing.com` | 這台機器被擋網路 → 改在 Windows 本機雙擊 bat |
| Windows 印出亂碼、json 存成 cp950 | 腳本已強制 UTF-8；自己寫的檔一律 `encoding="utf-8"` |
| `python` 打開微軟商店 | 設定 → 應用程式 → 進階應用程式設定 → 應用程式執行別名，關掉 python；bat 會改試 `py` |
| `pip` 啟動器錯誤 | 一律用 `python -m pip` |
| 有些句子回空檔 | 腳本會自動重試 4 次；仍失敗就稍後重跑（只會補做失敗的句子） |
