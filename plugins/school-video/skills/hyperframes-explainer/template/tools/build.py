# -*- coding: utf-8 -*-
"""依 cues.json＋content.py 組出 HyperFrames 的 index.html（版面、GSAP 動畫、字幕、旁白、配樂）。
用法：python tools/build.py
內建版型：title｜bullets｜steps｜big｜info｜outro。要更特別的畫面：在 CUSTOM 裡為該場景 id 寫一個函式（見檔尾範例）。
"""
import html
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
from content import SCENES, TITLE  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cues = json.load(open(os.path.join(ROOT, "cues.json"), encoding="utf-8"))
TOTAL = cues["total"]
S = {c["id"]: c for c in cues["scenes"]}
W, H = 1920, 1080
COLORS = ["#2f7fd8", "#20a77c", "#f0644f", "#ffb020", "#8a5cf6"]


def e(s):
    return html.escape(str(s))


# ---------------------------------------------------------------- 時間（全片秒數）
def L(sid, i):            # 第 i 句開口
    return S[sid]["lines"][i]["start"]


def LE(sid, i):           # 第 i 句結束
    return S[sid]["lines"][i]["end"]


def C(sid, i, j):         # 第 i 句第 j 段字幕開始
    caps = S[sid]["lines"][i]["caps"]
    return caps[min(j, len(caps) - 1)]["start"] if caps else L(sid, i)


def CS(sid):
    return S[sid]["clip_start"]


def CE(sid):
    return S[sid]["clip_end"]


# ---------------------------------------------------------------- GSAP 小工具
js = []


def add(s):
    js.append(s)


def f(t):
    return f"{max(t, 0):.3f}"


def appear(sel, t, y=40, x=0, dur=0.6, ease="power3.out"):
    add(f'tl.fromTo("{sel}",{{opacity:0,x:{x},y:{y}}},{{opacity:1,x:0,y:0,duration:{dur},ease:"{ease}",immediateRender:true}},{f(t)});')


def pop(sel, t, dur=0.55, s0=0.3):
    add(f'tl.fromTo("{sel}",{{opacity:0,scale:{s0}}},{{opacity:1,scale:1,duration:{dur},ease:"back.out(1.9)",transformOrigin:"50% 50%",immediateRender:true}},{f(t)});')


def grow(sel, t, dur=0.7, axis="scaleX", origin="0% 50%"):
    add(f'tl.fromTo("{sel}",{{{axis}:0}},{{{axis}:1,duration:{dur},ease:"power2.inOut",transformOrigin:"{origin}",immediateRender:true}},{f(t)});')


def stamp(sel, t, rot=-8):
    add(f'tl.fromTo("{sel}",{{opacity:0,scale:2.4,rotation:{rot - 14}}},{{opacity:1,scale:1,rotation:{rot},duration:0.45,ease:"power4.in",transformOrigin:"50% 50%",immediateRender:true}},{f(t)});')


def pulse(sel, t, s=1.08):
    add(f'tl.fromTo("{sel}",{{scale:1}},{{scale:{s},duration:0.25,yoyo:true,repeat:1,ease:"sine.inOut",transformOrigin:"50% 50%"}},{f(t)});')


# ---------------------------------------------------------------- 圖示（自繪 SVG，不用 emoji、不用商標）
I = {
    "speak": '<svg viewBox="-50 -50 100 100"><path d="M-38 -30 H38 Q44 -30 44 -24 V14 Q44 20 38 20 H-6 L-24 38 V20 H-38 Q-44 20 -44 14 V-24 Q-44 -30 -38 -30Z" fill="currentColor"/></svg>',
    "star": '<svg viewBox="-50 -50 100 100"><path d="M0 -44 L13 -14 L44 -12 L20 9 L28 40 L0 23 L-28 40 L-20 9 L-44 -12 L-13 -14Z" fill="currentColor"/></svg>',
    "people": '<svg viewBox="-50 -50 100 100"><circle cx="-18" cy="-18" r="14" fill="currentColor"/><circle cx="20" cy="-18" r="14" fill="currentColor"/><path d="M-44 36 Q-44 2 -18 2 Q8 2 8 36Z M-6 36 Q-6 2 20 2 Q46 2 46 36Z" fill="currentColor"/></svg>',
    "check": '<svg viewBox="-50 -50 100 100"><path d="M-30 2 L-8 24 L32 -24" fill="none" stroke="currentColor" stroke-width="13" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "clock": '<svg viewBox="-50 -50 100 100"><circle r="40" fill="none" stroke="currentColor" stroke-width="9"/><path d="M0 -24 V0 H18" stroke="currentColor" stroke-width="9" stroke-linecap="round" fill="none"/></svg>',
    "pin": '<svg viewBox="-50 -50 100 100"><path d="M0 44 C-6 30 -32 6 -32 -14 A32 32 0 0 1 32 -14 C32 6 6 30 0 44Z" fill="currentColor"/><circle cy="-14" r="12" fill="#fff"/></svg>',
    "flag": '<svg viewBox="-50 -50 100 100"><path d="M-28 42 V-40" stroke="currentColor" stroke-width="9" stroke-linecap="round"/><path d="M-24 -40 H34 L22 -20 L34 0 H-24Z" fill="currentColor"/></svg>',
    "target": '<svg viewBox="-50 -50 100 100"><circle r="40" fill="none" stroke="currentColor" stroke-width="9"/><circle r="22" fill="none" stroke="currentColor" stroke-width="9"/><circle r="7" fill="currentColor"/></svg>',
    "book": '<svg viewBox="-50 -50 100 100"><path d="M-44 -32 Q-22 -42 0 -30 Q22 -42 44 -32 V36 Q22 26 0 38 Q-22 26 -44 36Z" fill="none" stroke="currentColor" stroke-width="8" stroke-linejoin="round"/><path d="M0 -30 V38" stroke="currentColor" stroke-width="7"/></svg>',
    "trophy": '<svg viewBox="-60 -60 120 120"><path d="M-30 -46 H30 V-14 Q30 16 0 20 Q-30 16 -30 -14Z" fill="currentColor"/><path d="M-30 -36 Q-52 -36 -50 -18 Q-48 0 -26 2 M30 -36 Q52 -36 50 -18 Q48 0 26 2" fill="none" stroke="currentColor" stroke-width="7"/><rect x="-8" y="18" width="16" height="16" fill="currentColor"/><rect x="-26" y="34" width="52" height="14" rx="4" fill="currentColor"/></svg>',
    "date": '<svg viewBox="-50 -50 100 100"><rect x="-40" y="-32" width="80" height="72" rx="10" fill="none" stroke="currentColor" stroke-width="8"/><path d="M-40 -10 H40 M-20 -44 V-24 M20 -44 V-24" stroke="currentColor" stroke-width="8" stroke-linecap="round"/></svg>',
}
ROW_ICON = {"日期": "date", "時間": "clock", "地點": "pin"}

# ---------------------------------------------------------------- 場景
sections = []


def scene(sid, inner, sc):
    st, en = CS(sid), CE(sid)
    head = ""
    if sc.get("tag"):
        head += f'        <div class="tag" id="{sid}-tag" style="left:120px;top:62px">{e(sc["tag"])}</div>\n'
    if sc.get("head") and sc["layout"] not in ("title", "outro"):
        head += f'        <div class="stitle" id="{sid}-title" style="left:120px;top:100px">{e(sc["head"])}</div>\n'
    sections.append(f'''
      <section id="sc-{sid}" class="clip scene" data-start="{st:.3f}" data-duration="{en - st:.3f}" data-track-index="1">
{head}{inner}
      </section>''')
    if st > 0:
        add(f'tl.fromTo("#sc-{sid}",{{opacity:0}},{{opacity:1,duration:0.4,ease:"sine.out",immediateRender:true}},{f(st)});')
    if en < TOTAL:
        add(f'tl.to("#sc-{sid}",{{opacity:0,duration:0.38,ease:"sine.in"}},{f(en - 0.4)});')
    if sc.get("tag"):
        appear(f"#{sid}-tag", st + 0.1, x=-30, y=0, dur=0.5)
    if sc.get("head") and sc["layout"] not in ("title", "outro"):
        appear(f"#{sid}-title", st + 0.2, y=26, dur=0.6)


def cue_times(sid, sc, n):
    """第 k 個項目出現的時間：content.py 的 cue，或依序對應每段字幕。"""
    if sc.get("cue"):
        return [C(sid, i, j) for i, j in sc["cue"]][:n] + [LE(sid, len(S[sid]["lines"]) - 1)] * max(0, n - len(sc["cue"]))
    caps = [cp["start"] for ln in S[sid]["lines"] for cp in ln["caps"]] or [L(sid, 0)]
    return [caps[min(k, len(caps) - 1)] + (0 if k < len(caps) else 0.3 * (k - len(caps) + 1)) for k in range(n)]


def lay_title(sid, sc):
    h = []
    if sc.get("kicker"):
        h.append(f'        <div class="pill" id="{sid}-k" style="left:0;width:{W}px;top:190px;text-align:center"><span>{e(sc["kicker"])}</span></div>')
    h.append(f'        <div class="mega" id="{sid}-h" style="left:0;width:{W}px;top:340px">{e(sc["head"])}</div>')
    if sc.get("sub"):
        h.append(f'        <div class="sub" id="{sid}-s" style="left:0;width:{W}px;top:600px">{e(sc["sub"])}</div>')
    chips = sc.get("chips", [])
    x0 = W / 2 - len(chips) * 250 / 2
    for i, c in enumerate(chips):
        h.append(f'        <div class="gchip" id="{sid}-c{i}" style="left:{x0 + i * 250 + 15:.0f}px;top:740px;background:{COLORS[i % 5]}">{e(c)}</div>')
    scene(sid, "\n".join(h), sc)
    t0 = CS(sid) + 0.3
    if sc.get("kicker"):
        appear(f"#{sid}-k", t0, y=-30)
    pop(f"#{sid}-h", t0 + 0.3, dur=0.8, s0=0.6)
    if sc.get("sub"):
        appear(f"#{sid}-s", t0 + 0.9, y=30)
    for i in range(len(chips)):
        pop(f"#{sid}-c{i}", t0 + 1.3 + i * 0.25)


def lay_bullets(sid, sc):
    items = sc["items"]; n = len(items); cw = min(500, (W - 240 - (n - 1) * 40) // n)
    x0 = (W - (n * cw + (n - 1) * 40)) / 2
    h = []
    for i, it in enumerate(items):
        t, icn = (it, "check") if isinstance(it, str) else it
        h.append(f'''        <div class="wcard" id="{sid}-c{i}" style="left:{x0 + i * (cw + 40):.0f}px;top:330px;width:{cw}px;--c:{COLORS[i % 5]}">
          <div class="wic">{I.get(icn, I["check"])}</div><div class="wt">{e(t)}</div></div>''')
    scene(sid, "\n".join(h), sc)
    for i, t in enumerate(cue_times(sid, sc, n)):
        pop(f"#{sid}-c{i}", t - 0.05)


def lay_steps(sid, sc):
    items = sc["items"]; n = len(items)
    h = []
    for i, t in enumerate(items):
        h.append(f'        <div class="row" id="{sid}-r{i}" style="left:300px;top:{280 + i * 170}px;--c:{COLORS[i % 5]}"><div class="ric">{i + 1}</div><div class="rt">{e(t)}</div></div>')
    scene(sid, "\n".join(h), sc)
    for i, t in enumerate(cue_times(sid, sc, n)):
        appear(f"#{sid}-r{i}", t - 0.05, x=60, y=0)


def lay_info(sid, sc):
    h = []
    for i, (k, v) in enumerate(sc["rows"]):
        icn = I.get(ROW_ICON.get(k, ""), I["star"])
        h.append(f'        <div class="irow" id="{sid}-r{i}" style="left:300px;top:{280 + i * 180}px;--c:{COLORS[i % 5]}"><div class="iic">{icn}</div><div class="ik">{e(k)}</div><div class="iv">{e(v)}</div></div>')
    scene(sid, "\n".join(h), sc)
    for i, t in enumerate(cue_times(sid, sc, len(sc["rows"]))):
        appear(f"#{sid}-r{i}", t - 0.05, x=60, y=0)
        pulse(f"#{sid}-r{i} .iv", t + 0.7, 1.06)


def lay_big(sid, sc):
    h = [f'        <div class="bignum" id="{sid}-v" style="left:0;width:{W}px;top:230px">{e(sc["value"])}</div>']
    if sc.get("sub"):
        h.append(f'        <div class="sub" id="{sid}-s" style="left:0;width:{W}px;top:720px">{e(sc["sub"])}</div>')
    scene(sid, "\n".join(h), sc)
    stamp(f"#{sid}-v", L(sid, 0) + 0.1, rot=0)
    if sc.get("sub"):
        appear(f"#{sid}-s", L(sid, 0) + 0.7, y=30)


def lay_outro(sid, sc):
    h = [f'        <div class="mega" id="{sid}-h" style="left:0;width:{W}px;top:340px">{e(sc["head"])}</div>']
    if sc.get("sub"):
        h.append(f'        <div class="sub" id="{sid}-s" style="left:0;width:{W}px;top:600px">{e(sc["sub"])}</div>')
    if sc.get("note"):
        h.append(f'        <div class="note" id="{sid}-n" style="left:0;width:{W}px;top:960px">{e(sc["note"])}</div>')
    scene(sid, "\n".join(h), sc)
    pop(f"#{sid}-h", CS(sid) + 0.4, dur=0.8, s0=0.6)
    if sc.get("sub"):
        appear(f"#{sid}-s", L(sid, len(S[sid]["lines"]) - 1) - 0.1, y=30)
    if sc.get("note"):
        appear(f"#{sid}-n", CS(sid) + 1.0, y=10)
    add(f'tl.to(".fadeout",{{opacity:1,duration:1.2,ease:"sine.in"}},{f(TOTAL - 1.3)});')


LAYOUT = {"title": lay_title, "bullets": lay_bullets, "steps": lay_steps, "info": lay_info, "big": lay_big, "outro": lay_outro}

# 自訂場景：CUSTOM["場景id"] = 函式(sid, sc)。函式內用 scene() 產生畫面，再用 appear／pop／grow／stamp／pulse 依 L()／C() 的時間加動畫。
CUSTOM = {}

for sc in SCENES:
    if sc["id"] not in S:
        sys.exit(f"cues.json 沒有場景 {sc['id']}：請先重跑 tools/tts.py")
    fn = CUSTOM.get(sc["id"]) or LAYOUT.get(sc.get("layout", "bullets"))
    if not fn:
        sys.exit(f"不認得的 layout：{sc.get('layout')}")
    fn(sc["id"], sc)

# ---------------------------------------------------------------- 字幕
caps_html, ci = [], 0
for sc in cues["scenes"]:
    for ln in sc["lines"]:
        en = " en" if ln.get("v", "zh") != "zh" else ""
        for k, cp in enumerate(ln["caps"]):
            caps_html.append(f'<div class="cap{en}" id="cap{ci}"><span>{e(cp["text"])}</span></div>')
            end = cp["end"] if k < len(ln["caps"]) - 1 else cp["end"] + 0.25
            add(f'tl.set("#cap{ci}",{{opacity:1}},{f(cp["start"])});tl.set("#cap{ci}",{{opacity:0}},{f(end)});')
            ci += 1

# ---------------------------------------------------------------- 背景（漂浮色塊）
rnd = random.Random(7)
bgt = []
for i in range(14):
    x, y, sz = rnd.uniform(-40, 1860), rnd.uniform(-100, 1000), rnd.uniform(40, 86)
    bgt.append(f'<div class="ftile" id="ft{i}" style="left:{x:.0f}px;top:{y:.0f}px;width:{sz:.0f}px;height:{sz:.0f}px;background:{rnd.choice(COLORS)}"></div>')
    add(f'tl.fromTo("#ft{i}",{{x:0,y:0,rotation:{rnd.uniform(-20, 20):.0f}}},{{x:{rnd.uniform(-160, 160):.0f},y:{rnd.uniform(-420, -180):.0f},rotation:{rnd.uniform(-40, 40):.0f},duration:{TOTAL:.2f},ease:"none",immediateRender:true}},0);')
add(f'tl.to("#blob1",{{x:180,y:90,duration:{TOTAL:.2f},ease:"sine.inOut"}},0);')
add(f'tl.to("#blob2",{{x:-160,y:-70,duration:{TOTAL:.2f},ease:"sine.inOut"}},0);')

CSS = open(os.path.join(ROOT, "tools", "style.css"), encoding="utf-8").read()
nl = "\n"
page = f'''<!doctype html>
<html lang="zh-Hant">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>{e(TITLE)}</title>
    <script src="assets/gsap.min.js"></script>
    <style>
{CSS}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="{W}" data-height="{H}">
      <section id="bg" class="clip" data-start="0" data-duration="{TOTAL}" data-track-index="0">
        <div class="grid"></div><div class="blob" id="blob1"></div><div class="blob" id="blob2"></div>
        {"".join(bgt)}
      </section>
{"".join(sections)}
      <section id="caps" class="clip" data-start="0" data-duration="{TOTAL}" data-track-index="3">
        {"".join(caps_html)}
        <div class="fadeout"></div>
      </section>
      <audio id="vo" src="assets/voice/narration.wav" data-start="0" data-duration="{TOTAL}" data-track-index="5" data-volume="1"></audio>
      <audio id="bgm" src="assets/audio/bgm.wav" data-start="0" data-duration="{TOTAL}" data-track-index="6" data-volume="0.5"></audio>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines = window.__timelines || {{}};
      {nl.join("      " + s for s in js).strip()}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
'''
with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as fp:
    fp.write(page)
print("index.html ok, total", TOTAL, "tweens", len(js))
