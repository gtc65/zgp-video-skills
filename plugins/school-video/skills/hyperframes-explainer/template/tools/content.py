# -*- coding: utf-8 -*-
# 說明影片的全部台詞與畫面內容（改台詞、改字卡都改這裡）
#
# VOICES：聲音代號 → (edge-tts 聲音, 語速)。台灣腔一律用 zh-TW-* 聲音。
# SCENES：每個場景
#   id      場景代號（英數）
#   layout  版型：title（片名）｜bullets（重點卡片）｜steps（步驟）｜big（超大數字／單字）｜info（資訊表）｜outro（片尾）
#   tag     左上小標（英文或短詞，可省略）　head：場景大標
#   其他欄位依版型：items、rows、value、sub…（見下方範例）
#   lines   旁白。字串＝預設中文聲音，句中「｜」是字幕斷行點；
#           dict 可用：t 字幕文字、v 聲音代號、say 實際念法（修讀音）、gap 這句後停幾秒、nocap True 不出字幕
#   cue     （bullets／steps）第 k 個項目在第幾句、第幾段字幕出現：[[句, 段], ...]；不寫就依序對應每段字幕

TITLE = "校園活動說明影片"
VOICES = {
    "zh": ("zh-TW-HsiaoChenNeural", "-3%"),   # 女聲曉臻；男聲改 zh-TW-YunJheNeural
    "en": ("en-US-AvaNeural", "-5%"),
}

SCENES = [
    {"id": "intro", "layout": "title", "kicker": "本校　2026", "head": "英語日活動", "sub": "活動說明",
     "chips": ["一年級", "二年級", "三年級"],
     "lines": [
        {"t": "English Day!", "v": "en"},
        "各位同學好！｜今天要介紹｜本校的英語日活動。",
     ]},
    {"id": "why", "layout": "bullets", "tag": "WHY", "head": "為什麼要參加？",
     "items": [("開口說英文", "speak"), ("認識節慶文化", "star"), ("和同學一起玩", "people")],
     "lines": [
        "這是練習｜開口說英文、｜認識節慶文化、｜和同學一起玩的好機會！",
     ],
     "cue": [[0, 1], [0, 2], [0, 3]]},
    {"id": "how", "layout": "steps", "tag": "HOW", "head": "怎麼參加？",
     "items": ["準備一句英文", "穿上裝扮", "到舞台走秀"],
     "lines": [
        "第一步，準備一句英文；｜第二步，穿上你的裝扮；｜第三步，到舞台上走秀！",
     ]},
    {"id": "when", "layout": "info", "tag": "WHEN & WHERE", "head": "時間地點",
     "rows": [("日期", "10/28（三）"), ("時間", "早上 8:00"), ("地點", "活動中心")],
     "lines": [
        {"t": "活動在｜十月二十八日星期三｜早上八點，", "say": "活動在，十月二十八號星期三，早上八點，"},
        "地點在活動中心。",
     ],
     "cue": [[0, 1], [0, 2], [1, 0]]},
    {"id": "count", "layout": "big", "tag": "TIP", "head": "準備時間", "value": "3", "sub": "分鐘內上台完成",
     "lines": ["每個人有三分鐘，｜記得把握時間！"]},
    {"id": "outro", "layout": "outro", "head": "我們英語日見！", "sub": "See you on English Day!",
     "note": "旁白為 AI 語音合成，配樂由程式生成",
     "lines": [
        "我們英語日見！",
        {"t": "See you on English Day!", "v": "en"},
     ]},
]
