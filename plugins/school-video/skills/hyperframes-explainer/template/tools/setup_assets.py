# -*- coding: utf-8 -*-
"""準備素材：下載 GSAP（固定版本）、把台詞用到的字從中文字型抽成小字型檔（woff2）。
用法：python tools/setup_assets.py [字型檔 Bold] [字型檔 Black]
  台詞有新字就要重跑（否則新字會變成系統字型）。
字型自動尋找順序：Noto Sans CJK TC（Linux）→ Noto Sans TC（Windows 自行安裝的 VF）→ 微軟正黑體（只作本機算圖用）。
需要：python -m pip install fonttools brotli
"""
import io
import os
import subprocess
import sys
import tarfile
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GSAP_URLS = ["https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js",
             "https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js",
             "https://registry.npmjs.org/gsap/-/gsap-3.12.5.tgz"]     # 依序嘗試（有些網路擋 CDN）
LOCAL = os.environ.get("LOCALAPPDATA", "")
CANDIDATES = [
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc", 3),
    ("C:/Windows/Fonts/NotoSansTC-VF.ttf", "C:/Windows/Fonts/NotoSansTC-VF.ttf", None),
    (f"{LOCAL}/Microsoft/Windows/Fonts/NotoSansTC-VF.ttf", f"{LOCAL}/Microsoft/Windows/Fonts/NotoSansTC-VF.ttf", None),
    ("C:/Windows/Fonts/msjhbd.ttc", "C:/Windows/Fonts/msjhbd.ttc", 0),
]

os.makedirs(os.path.join(ROOT, "assets", "fonts"), exist_ok=True)
g = os.path.join(ROOT, "assets", "gsap.min.js")
if not os.path.exists(g):
    for u in GSAP_URLS:
        try:
            data = urllib.request.urlopen(u, timeout=30).read()
            if u.endswith(".tgz"):
                data = tarfile.open(fileobj=io.BytesIO(data)).extractfile("package/dist/gsap.min.js").read()
            open(g, "wb").write(data)
            print("gsap ok：", u)
            break
        except Exception as ex:
            print("  下載失敗，換下一個：", u, ex)
    else:
        sys.exit("GSAP 下載失敗：請手動把 gsap.min.js（3.12.5）放到 assets/")

if len(sys.argv) >= 2:
    bold = sys.argv[1]; black = sys.argv[2] if len(sys.argv) > 2 else bold
    num = 3 if bold.endswith(".ttc") and "CJK" in bold else (0 if bold.endswith(".ttc") else None)
else:
    found = next((c for c in CANDIDATES if os.path.exists(c[0])), None)
    if not found:
        sys.exit("找不到中文字型。請安裝 Noto Sans TC（fonts.google.com/noto/specimen/Noto+Sans+TC），或指定字型檔路徑。")
    bold, black, num = found
if "msjh" in bold:
    print("⚠ 用的是微軟正黑體：只在本機算圖，不要把 assets/fonts 公開散布。")

text = set()
for p in ["tools/content.py", "tools/build.py", "tools/style.css", "index.html"]:
    fp = os.path.join(ROOT, p)
    if os.path.exists(fp):
        text |= set(open(fp, encoding="utf-8").read())
text |= set(chr(c) for c in range(0x20, 0x7F)) | set("　，。、；：！？「」（）～→›…‧・※★▲♪")
chars = "".join(sorted(c for c in text if c >= " "))
tf = os.path.join(ROOT, "tools", "_chars.txt")
with open(tf, "w", encoding="utf-8") as fp:
    fp.write(chars)
for src, name in [(bold, "TC-Bold"), (black, "TC-Black")]:
    args = [sys.executable, "-m", "fontTools.subset", src, f"--text-file={tf}", "--flavor=woff2",
            f"--output-file={os.path.join(ROOT, 'assets', 'fonts', name + '.woff2')}", "--layout-features=*"]
    if num is not None and src.endswith(".ttc"):
        args.append(f"--font-number={num}")
    subprocess.run(args, check=True)
print("fonts ok,", len(chars), "chars")
