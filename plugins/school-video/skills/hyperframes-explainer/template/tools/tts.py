# -*- coding: utf-8 -*-
"""產生旁白：content.py 每句 → edge-tts（台灣腔）→ 量長度 → 串成 assets/voice/narration.wav，輸出 cues.json
用法：python tools/tts.py          （需要網路，Windows 本機執行；Cowork 雲端連不到 edge-tts）
      python tools/tts.py --dry    （不連網，用估計長度產生靜音旁白，只供先排畫面）
"""
import asyncio
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from content import SCENES, VOICES  # noqa: E402

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DRY = "--dry" in sys.argv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "voice-cache")
SR = 48000
LEAD = 1.2        # 片頭靜音
GAP_LINE = 0.5    # 句與句之間
GAP_SCENE = 1.3   # 場景之間
TAIL = 4.0        # 片尾


def norm(x):
    x = {"t": x} if isinstance(x, str) else dict(x)
    x.setdefault("v", "zh")
    x.setdefault("say", x["t"].replace("｜", ""))
    return x


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).decode().strip())


def ff(*a):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, a)], check=True)


async def synth(text, vk):
    voice, rate = VOICES[vk]
    h = hashlib.md5(f"{voice}{rate}{text}".encode("utf-8")).hexdigest()[:12]
    if DRY:
        wav = os.path.join(CACHE, "dry_" + h + ".wav")   # 估計用的靜音檔，與真旁白分開
        if not os.path.exists(wav):
            pun = sum(1 for c in text if c in "，。、；：！？「」")
            zh = sum(1 for c in text if ord(c) > 0x2E80) - pun
            en = sum(1 for c in text if c.isascii() and c.isalnum())
            ff("-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=mono", "-t", f"{zh * 0.21 + pun * 0.12 + en * 0.07 + 0.3:.3f}", wav)
        return wav
    mp3, wav = os.path.join(CACHE, h + ".mp3"), os.path.join(CACHE, h + ".wav")
    if not os.path.exists(wav) or os.path.getsize(wav) < 2000:
        import edge_tts
        for k in range(4):
            try:
                await edge_tts.Communicate(text, voice, rate=rate).save(mp3)
                break
            except Exception as e:
                print("  重試", k + 1, e)
                await asyncio.sleep(2 + k * 2)
        else:
            sys.exit(f"失敗：{text}（這台電腦連不到 speech.platform.bing.com？）")
        ff("-i", mp3, "-af", "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
           "silenceremove=start_periods=1:start_threshold=-50dB,areverse", "-ar", SR, "-ac", 1, wav)
    return wav


async def main():
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(os.path.join(ROOT, "assets", "voice"), exist_ok=True)
    t, parts, cues = LEAD, [], []
    for si, sc in enumerate(SCENES):
        if si:
            t += GAP_SCENE
        s_start, lines, prev_gap = t, [], None
        for li, raw in enumerate(sc["lines"]):
            ln = norm(raw)
            if li:
                t += prev_gap if prev_gap is not None else GAP_LINE
            wav = await synth(ln["say"], ln["v"])
            d = dur(wav)
            print(f"  {sc['id']:9s} {d:5.2f}s  {ln['say']}")
            parts.append((t, wav))
            caps = []
            if not ln.get("nocap"):
                chunks = [c for c in ln["t"].split("｜") if c]
                w = [max(len(c), 2) for c in chunks]
                ct = t
                for c, wc in zip(chunks, w):
                    cd = d * wc / sum(w)
                    caps.append({"text": c, "start": round(ct, 3), "end": round(ct + cd, 3)})
                    ct += cd
            lines.append({"text": ln["t"].replace("｜", ""), "v": ln["v"], "start": round(t, 3), "end": round(t + d, 3), "caps": caps})
            t += d
            prev_gap = ln.get("gap")
        if prev_gap:
            t += max(prev_gap - GAP_SCENE, 0)
        cues.append({"id": sc["id"], "start": round(s_start, 3), "vo_end": round(t, 3), "lines": lines})
    total = round(t + TAIL, 2)
    for i, c in enumerate(cues):
        c["clip_start"] = 0.0 if i == 0 else round(c["start"] - 0.5, 3)
    for i, c in enumerate(cues):
        c["clip_end"] = total if i == len(cues) - 1 else cues[i + 1]["clip_start"]
    out = os.path.join(ROOT, "assets", "voice", "narration.wav")
    inputs, filt = [], []
    for i, (st, w) in enumerate(parts):
        inputs += ["-i", w]
        ms = int(st * 1000)
        filt.append(f"[{i}]adelay={ms}|{ms}[a{i}]")
    filt.append("".join(f"[a{i}]" for i in range(len(parts))) + f"amix=inputs={len(parts)}:normalize=0,apad=whole_dur={total}[out]")
    script = os.path.join(CACHE, "mix.txt")
    with open(script, "w", encoding="utf-8") as fp:
        fp.write(";".join(filt))
    ff(*inputs, "-filter_complex_script", script, "-map", "[out]", "-ar", SR, "-ac", 2, "-t", total, out)
    with open(os.path.join(ROOT, "cues.json"), "w", encoding="utf-8") as fp:
        json.dump({"total": total, "dry": DRY, "scenes": cues}, fp, ensure_ascii=False, indent=1)
    print("total", total, "秒", "（估計值，只供排畫面）" if DRY else "")


asyncio.run(main())
