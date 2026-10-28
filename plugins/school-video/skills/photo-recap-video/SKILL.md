---
name: photo-recap-video
description: 用現場照片做學校活動回顧／成果影片（照片推拉、資訊字卡、台灣腔旁白、字幕、原創配樂、−16 LUFS、LINE 版）。不用 AI 生成畫面，全部程式剪接。使用者要做活動回顧、成果影片、照片影片、幻燈片影片時使用。
---

# 照片回顧影片（活動成果片）

把一個活動的照片做成 1–3 分鐘的回顧片。畫面全部來自真實照片和程式畫的字卡，**不用 AI 生成畫面**；旁白用 `taiwan-narration` 技能（台灣腔）；配樂用程式原創，沒有版權問題。所有回應與介面文字使用繁體中文。

工具都在 `scripts/`（Python 3.9+、ffmpeg、Pillow；字卡另需 Playwright；配樂另需 mido＋fluidsynth）：

| 腳本 | 做什麼 |
|---|---|
| `contact_sheet.py` | 照片資料夾 → 編號縮圖總覽表＋photos.json（EXIF 轉正、依拍攝時間排序） |
| `cards.py` | 資訊字卡 PNG（片名、日期地點、組別、得獎名單…），文字自動縮小、溢出會報錯 |
| `compose_music.py` | 依段落情緒產生原創配樂（mystery／cute／march／spooky／warm／calm） |
| `assemble.py` | edl.json → 成片：照片推拉（Ken Burns）、橫直照模糊底、字卡彈入、定格、疊圖、字幕、旁白、音效、配樂自動壓低、兩段式 −16 LUFS |
| `deliver.py` | 高畫質版＋LINE 版（2-pass 控制在目標 MB 內），列出規格與響度 |

範本在 `templates/`（edl、cards、sections 範例都實測過）。

## 0. 需求確認（用 AskUserQuestion，一次問完）

- 活動名稱、日期、對象（全校／家長／對外宣傳）；活動是否已結束、**有沒有得獎結果**（還沒有就整段不做，不要猜）
- 片長（常見 1–2.5 分鐘）、版式（橫式 1920×1080 或直式 1080×1920）
- 旁白：要不要、男聲或女聲、語氣（活潑／溫馨／正式）；有主持稿就以主持稿為準
- 肖像：學生能不能露臉、字卡**顯示角色名／班級，不顯示學生姓名**（預設）
- 照片在哪個資料夾、成品交付到哪裡

## 1. 素材盤點

```bash
python scripts/contact_sheet.py <照片資料夾> work/sheets      # 先看總覽表，不要一張一張開
```
- 照片是 PDF：先轉圖（`pdftoppm -r 150 -jpeg 檔.pdf out/p`）。
- 剔除：模糊、閉眼、背對、拍到不該出現的個資（名牌、成績單、電腦螢幕）。
- **出版社或他人的著作**（教科書頁面、海報、繪本插圖、商標）不要放進片子。
- 依活動流程分段（開場 → 各組／各關 → 互動 → 合照 → 片尾），每段挑 4–10 張。

## 2. 分段腳本（先給使用者確認再做）

用表格列出：段落、秒數、照片編號、字卡文字、旁白句子。原則：
- 每張照片 2.5–4 秒；同一人／同組多張時用「主照＋互動照」兩張。
- 資訊（日期、地點、組別、名次）一律做成字卡，不要只靠旁白說。
- 旁白句子短、一句一個重點；字幕和旁白一致。
- 片尾一張字卡：「旁白為 AI 語音合成，配樂由程式生成」。

## 3. 旁白（用 taiwan-narration 技能）

寫 `lines.json`，在 Windows 本機產生（Cowork 雲端連不到 edge-tts → 寫 bat 到使用者資料夾請他雙擊）。等待真旁白時先用 `--dry` 的長度排畫面。拿到 `report.json` 後確認每段畫面長度 ≥ 該段旁白 + 0.8 秒。

## 4. 字卡

```bash
python scripts/cards.py work/cards.json work/cards     # 一定要打開 PNG 看一眼，溢出會報錯 → 刪字或拆卡
```
`theme` 依活動換色（萬聖節：深紫＋橘；運動會：藍＋黃；畢業：深藍＋金）。`transparent: true` 可做疊在照片上的透明圖層。

## 5. 配樂

```bash
python scripts/compose_music.py work/sections.json work/bgm.wav    # 段落 start/end 對齊 edl 的段落時間
```
沒有 fluidsynth 的環境（例如 Windows）：在雲端／WSL 跑，或請使用者提供已授權的純音樂。使用者給的歌曲有人聲時，旁白要更大聲或改用純音樂。

## 6. 剪接

寫 `work/edl.json`（照 `templates/edl.example.json`），然後：
```bash
python scripts/assemble.py work/edl.json
```
- 照片：`type: image`，`motion` 用 in／out／left／right／up／down 輪流，**直照在橫式片一律 `fit: blur`**。
- 字卡：`type: card`，`anim: pop`；段與段可用 `transition: 0.4–0.6` 交叉淡化。
- 旁白、字幕寫 `seg`＋`at`（相對該段開頭），段落長度改了時間會自動跟著動。
- 想做更花俏的畫面（照片相框、旋轉、對話泡泡、圖層動畫）：用 PIL 先畫成 PNG 或逐格影片，再當 `image`／`clip`／`overlays` 放進來。

## 7. 驗收（每次都做）

1. 報告裡 LUFS 要 −16±1、峰值 ≤ −1。
2. 每段抽 1 格拼成總覽圖看：字幕沒擋臉、照片沒被裁掉頭、字卡沒截字。
3. 請使用者完整看一次、用耳朵聽一次（旁白讀音、配樂有沒有蓋過旁白）。

## 8. 交付

```bash
python scripts/deliver.py work/cut/film.mp4 --mb 25 --name <片名>
```
- LINE 版（≤25MB）寫回使用者資料夾；Cowork 寫回單檔上限約 30MB，高畫質版超過就只在對話中提供下載。
- 在專案寫一份紀錄：決定、時間軸、旁白句子、照片編號、踩坑。

## 踩坑速查

| 症狀 | 處理 |
|---|---|
| 字卡中文變方塊 | 沒有中文字型：Linux 裝 `fonts-noto-cjk`；Windows 會用微軟正黑體 |
| Playwright 找不到瀏覽器 | `python -m playwright install chromium` |
| 字幕在 Windows 報錯找不到 .ass | 用本版 assemble.py（已改成相對路徑） |
| 配樂比片子短 | 報告會警告；把 sections 最後一段的 end 拉長 |
| 照片橫躺 | contact_sheet／assemble 都會依 EXIF 轉正；仍然歪就是原檔沒有 EXIF，用 PIL 轉好另存 |
| 寫回電腦 HTTP 400 | Cowork：先 SendUserFile 取得 fileUuid 再 commit |
| 成品太大傳不了 LINE | `deliver.py --mb 20` |
