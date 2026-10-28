# -*- coding: utf-8 -*-
"""快速預覽：在指定秒數截圖（不經 HyperFrames，只檢查版面）。
用法：python tools/snap.py 1.5,8,20 review/     （需要 python -m pip install playwright && python -m playwright install chromium）"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
times = [float(x) for x in sys.argv[1].split(",")]
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "review")
os.makedirs(OUT, exist_ok=True)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=os.environ.get("SNAP_CHROMIUM") or None)
        pg = await b.new_page(viewport={"width": 1920, "height": 1080})
        await pg.goto("file:///" + os.path.join(ROOT, "index.html").replace("\\", "/").lstrip("/"))
        await pg.wait_for_timeout(1000)
        for t in times:
            await pg.evaluate('''t=>{document.querySelectorAll('section[data-start]').forEach(e=>{const s=+e.dataset.start,d=+e.dataset.duration;
              e.style.visibility=(t>=s&&t<s+d)?'visible':'hidden'});window.__timelines.main.seek(t)}''', t)
            await pg.wait_for_timeout(80)
            await pg.screenshot(path=os.path.join(OUT, f"f{t:06.2f}.png"))
        await b.close()
    print("截圖完成：", OUT)

asyncio.run(main())
