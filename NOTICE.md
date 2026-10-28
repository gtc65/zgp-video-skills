# 第三方說明

本 repo 只包含自己寫的腳本與說明，**不包含**下列第三方軟體、模型或字型；使用者自行安裝，並遵守各自授權。

| 相依 | 用途 | 授權／注意 |
|---|---|---|
| [edge-tts](https://github.com/rany2/edge-tts) | 台灣腔旁白 | GPL-3.0 的 Python 套件，呼叫 Microsoft 線上語音服務；商業使用前請自行確認服務條款 |
| [HyperFrames](https://github.com/heygen-com/hyperframes) | HTML 動畫算成影片 | Apache-2.0（HeyGen） |
| [GSAP](https://gsap.com) | 動畫 | 由 setup_assets.py 下載，依 GSAP 授權使用 |
| Noto Sans TC／Noto Sans CJK | 字型 | SIL Open Font License 1.1 |
| 微軟正黑體 | 沒有 Noto 時的退回字型 | Windows 內建字型，只在本機算圖使用，不要散布字型檔 |
| [FluidSynth](https://www.fluidsynth.org)＋FluidR3_GM.sf2 | 照片回顧片配樂 | LGPL-2.1／MIT |
| FFmpeg、Pillow、Playwright、mido、numpy、fontTools | 影音與影像處理 | 各自授權 |
| BreezyVoice、Breeze TTS 2（選用） | 離線台灣華語 TTS | 依官方授權；Breeze TTS 2 權重與產生的聲音限研究與非商業用途 |

HyperFrames 的使用流程參考自 [claude-motion-explainer](https://github.com/mathruffian-dot/claude-motion-explainer)（MIT）。
