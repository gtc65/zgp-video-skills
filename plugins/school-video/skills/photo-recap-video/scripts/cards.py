"""資訊字卡（日期、地點、分數、規則…一律用這個，不讓 AI 寫字）。HTML → PNG（Playwright／Chromium），Noto Sans CJK TC（Windows 退回微軟正黑體）。
安裝：python -m pip install playwright && python -m playwright install chromium
用法：python cards.py cards.json outdir/
cards.json：
{
 "size": [1080, 1920],                       # 直式；橫式 [1920, 1080]
 "theme": {"bg": "#FFF4E0", "bg2": "#FFD9A8", "accent": "#E8552D", "text": "#2A2A2A", "card": "#FFFFFF"},
 "transparent": false,                       # true＝透明底（疊在影片上用，只畫卡片本身）
 "cards": [
  {"id": "T1", "style": "title", "kicker": "本校", "title": "英語日活動", "subtitle": "精彩回顧"},
  {"id": "C1", "kicker": "Level 1", "title": "考試資訊", "rows": [["日期", "11/5（三）"], ["地點", "英語教室"], ["時間", "30 分鐘"]],
   "note": "75 分就通過！", "badge": "重大消息！"},
  {"id": "C2", "style": "big", "title": "3", "subtitle": "倒數"}
 ]
}
style：card（預設，標題＋表格＋備註）｜title（片名）｜big（超大單字／數字）。每張輸出 <id>.png。
文字會自動縮小以塞進畫面；輸出後一定要看一眼 PNG 確認沒有截斷。"""
import html
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:%(w)dpx;height:%(h)dpx;overflow:hidden;font-family:'Noto Sans CJK TC','Noto Sans TC','Microsoft JhengHei',sans-serif;color:%(text)s;
 background:%(pagebg)s}
.wrap{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:%(pad)dpx}
.card{width:100%%;background:%(card)s;border-radius:%(r)dpx;padding:%(cp)dpx;box-shadow:0 %(s1)dpx %(s2)dpx rgba(0,0,0,.18);
 border-top:%(bt)dpx solid %(accent)s;position:relative}
.kicker{font-weight:700;color:%(accent)s;font-size:%(fk)dpx;letter-spacing:.06em}
.title{font-weight:900;font-size:%(ft)dpx;line-height:1.15;margin:.15em 0 .35em}
.sub{font-weight:700;font-size:%(fs)dpx;opacity:.8}
table{width:100%%;border-collapse:separate;border-spacing:0 %(gap)dpx;font-size:%(fr)dpx}
td{padding:.35em .5em;background:%(bg)s;font-weight:700}
td.k{color:%(accent)s;white-space:nowrap;width:1%%;border-radius:%(rr)dpx 0 0 %(rr)dpx;padding-left:.7em}
td.v{font-weight:900;border-radius:0 %(rr)dpx %(rr)dpx 0}
.note{margin-top:.6em;font-size:%(fn)dpx;font-weight:900;color:#fff;background:%(accent)s;border-radius:%(rr)dpx;padding:.35em .6em;text-align:center}
.badge{position:absolute;top:-.9em;right:.6em;transform:rotate(6deg);background:#D7263D;color:#fff;font-weight:900;font-size:%(fb)dpx;
 padding:.25em .7em;border-radius:.4em;box-shadow:0 6px 0 rgba(0,0,0,.2)}
.t-wrap{text-align:center}
.t-wrap .title{font-size:%(ftt)dpx}
.big{font-size:%(fbig)dpx;font-weight:900;line-height:1;color:%(accent)s;text-align:center}
"""


def page(c, size, th, transparent):
    w, h = size; u = min(w, h) / 1080
    pagebg = "transparent" if transparent else f"linear-gradient(160deg,{th['bg']} 0%,{th['bg2']} 100%)"
    v = dict(w=w, h=h, text=th["text"], pagebg=pagebg, pad=int(70 * u), card=th["card"], r=int(40 * u), cp=int(64 * u), s1=int(14 * u),
             s2=int(40 * u), bt=int(18 * u), accent=th["accent"], fk=int(46 * u), ft=int(104 * u), fs=int(52 * u), gap=int(14 * u),
             fr=int(56 * u), bg=th["bg"], rr=int(18 * u), fn=int(54 * u), fb=int(48 * u), ftt=int(132 * u), fbig=int(420 * u))
    e = lambda s: html.escape(str(s))
    st = c.get("style", "card")
    if st == "big":
        body = f'<div class="wrap"><div class="t-wrap"><div class="big">{e(c["title"])}</div>' + \
               (f'<div class="sub" style="text-align:center">{e(c["subtitle"])}</div>' if c.get("subtitle") else "") + "</div></div>"
    elif st == "title":
        body = '<div class="wrap"><div class="card t-wrap">' + (f'<div class="kicker">{e(c["kicker"])}</div>' if c.get("kicker") else "") + \
               f'<div class="title">{e(c["title"])}</div>' + (f'<div class="sub">{e(c["subtitle"])}</div>' if c.get("subtitle") else "") + "</div></div>"
    else:
        rows = "".join(f'<tr><td class="k">{e(k)}</td><td class="v">{e(v_)}</td></tr>' for k, v_ in c.get("rows", []))
        body = '<div class="wrap"><div class="card">' + (f'<div class="badge">{e(c["badge"])}</div>' if c.get("badge") else "") + \
               (f'<div class="kicker">{e(c["kicker"])}</div>' if c.get("kicker") else "") + f'<div class="title">{e(c.get("title", ""))}</div>' + \
               (f"<table>{rows}</table>" if rows else "") + (f'<div class="sub">{e(c["subtitle"])}</div>' if c.get("subtitle") else "") + \
               (f'<div class="note">{e(c["note"])}</div>' if c.get("note") else "") + "</div></div>"
    fit = """<script>
const W=%d,H=%d;function over(){const el=document.querySelector('.card')||document.querySelector('.t-wrap');const r=el.getBoundingClientRect();
return r.top<0||r.bottom>H||el.scrollWidth>el.clientWidth+2||[...document.querySelectorAll('td,.title,.big,.note,.sub')].some(n=>n.scrollWidth>n.clientWidth+2)}
let z=1;while(over()&&z>0.4){z-=0.04;document.querySelector('.wrap').style.fontSize='';document.querySelectorAll('.wrap *').forEach(n=>{
const f=parseFloat(getComputedStyle(n).fontSize);n.style.fontSize=(f*0.96)+'px'})}
document.title=over()?'OVERFLOW':'OK';</script>""" % (w, h)
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS % v}</style></head><body>{body}{fit}</body></html>"


def main():
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    size = spec.get("size", [1080, 1920])
    th = {"bg": "#FFF4E0", "bg2": "#FFD9A8", "accent": "#E8552D", "text": "#2A2A2A", "card": "#FFFFFF"} | spec.get("theme", {})
    tr = spec.get("transparent", False); bad = []
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": size[0], "height": size[1]})
        for c in spec["cards"]:
            pg.set_content(page(c, size, th, tr)); pg.wait_for_timeout(150)
            pg.screenshot(path=str(out / f"{c['id']}.png"), omit_background=tr)
            if pg.title() == "OVERFLOW":
                bad.append(c["id"])
            print(f"{c['id']}.png{'  ⚠ 文字太多，縮到下限仍超出' if pg.title() == 'OVERFLOW' else ''}")
        b.close()
    if bad:
        sys.exit(f"這幾張要刪字或拆卡：{bad}")


if __name__ == "__main__":
    main()
