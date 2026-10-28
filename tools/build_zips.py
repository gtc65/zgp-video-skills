# -*- coding: utf-8 -*-
"""重新打包 dist/*.zip（給 claude.ai／Claude 桌面版上傳用）。改過技能內容後執行：python tools/build_zips.py"""
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK = os.path.join(ROOT, "plugins", "school-video", "skills")
os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
for s in sorted(os.listdir(SK)):
    if not os.path.isfile(os.path.join(SK, s, "SKILL.md")):
        continue
    out = os.path.join(ROOT, "dist", f"{s}.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:      # Python 會為中文檔名設定 UTF-8 旗標
        for root, dirs, files in os.walk(os.path.join(SK, s)):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__")
            for f in sorted(files):
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, SK))
    print("ok", out)
