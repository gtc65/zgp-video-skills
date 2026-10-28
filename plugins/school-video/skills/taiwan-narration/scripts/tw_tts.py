# -*- coding: utf-8 -*-
"""台灣腔旁白產生器（edge-tts：曉臻／曉雨／雲哲）。每句一個檔，可選擇串成整條旁白＋時間軸。

用法（Windows 本機或任何連得到 speech.platform.bing.com 的電腦）：
  python tw_tts.py lines.json                 # 產生每句的 mp3（有 ffmpeg 時另存去頭尾靜音的 wav）
  python tw_tts.py lines.json --concat        # 再依 timeline 串成 narration.wav，輸出 cues.json
  python tw_tts.py lines.json --dry           # 不連網：用估計長度產生靜音檔，只供先排畫面
  python tw_tts.py --list zh-TW               # 列出可用聲音
  python tw_tts.py lines.json --only N3 N5    # 只重做這幾句

lines.json：
{
 "out": "旁白",                                    # 輸出資料夾（相對 lines.json），預設「旁白」
 "voices": {                                       # 聲音代號 → 設定
   "zh": {"voice": "zh-TW-HsiaoChenNeural", "rate": "+0%", "pitch": "+0Hz"},
   "en": {"voice": "en-US-AvaNeural", "rate": "-5%"}
 },
 "default": "zh",
 "lines": [
   {"id": "N1", "text": "歡迎來到｜本校運動會！"},                       # ｜＝字幕斷行點（不念）
   {"id": "N2", "text": "十一月六日截止", "say": "十一月六號截止"},       # say＝實際念法（修讀音用）
   {"id": "E1", "text": "Good luck!", "v": "en", "gap": 1.5},           # gap＝這句後多停幾秒（--concat 用）
   {"id": "N3", "text": "注意！", "rate": "-4%", "pitch": "+8Hz", "nocap": true}   # 單句覆寫語速音高；nocap＝不出字幕
 ],
 "timeline": {"lead": 1.2, "gap_line": 0.5, "tail": 3.0}            # --concat 用：片頭、句距、片尾（秒）
}
也可以給 .txt：每行「N1: 句子」或只寫句子（自動編號 L01、L02…），全部用預設聲音。

重跑時只會重做「文字或聲音設定有改」的句子（.tts_cache.json 記錄）。要強制重做某句：刪掉它的 mp3 或用 --only。
"""
import argparse
import asyncio
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_VOICES = {
    "zh": {"voice": "zh-TW-HsiaoChenNeural", "rate": "+0%", "pitch": "+0Hz"},   # 女聲，親切（預設）
    "zh2": {"voice": "zh-TW-HsiaoYuNeural", "rate": "+0%", "pitch": "+0Hz"},    # 女聲，較年輕
    "male": {"voice": "zh-TW-YunJheNeural", "rate": "+0%", "pitch": "+0Hz"},    # 男聲，沉穩
    "en": {"voice": "en-US-AvaNeural", "rate": "-5%", "pitch": "+0Hz"},         # 英文女聲
    "word": {"voice": "en-US-AvaNeural", "rate": "-20%", "pitch": "+0Hz"},      # 英文慢速（聽力示範）
}
SR = 48000
HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

if sys.platform == "win32":                       # Windows 主控台預設 cp950，印中文會壞
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def load(path):
    p = Path(path)
    if p.suffix.lower() == ".txt":
        lines = []
        for i, raw in enumerate([x.strip() for x in p.read_text(encoding="utf-8-sig").splitlines() if x.strip()]):
            m = re.match(r"^([A-Za-z]\w{0,15})\s*[:：]\s*(.+)$", raw)
            lines.append({"id": m.group(1), "text": m.group(2)} if m else {"id": f"L{i + 1:02d}", "text": raw})
        return {"lines": lines}
    return json.loads(p.read_text(encoding="utf-8-sig"))


def norm(cfg):
    voices = {k: dict(v) for k, v in DEFAULT_VOICES.items()}
    for k, v in cfg.get("voices", {}).items():
        voices[k] = {**voices.get(k, {"rate": "+0%", "pitch": "+0Hz"}), **v}
    default = cfg.get("default", "zh")
    out, seen = [], set()
    for i, ln in enumerate(cfg["lines"]):
        ln = {"text": ln} if isinstance(ln, str) else dict(ln)
        ln.setdefault("id", f"L{i + 1:02d}")
        if ln["id"] in seen:
            sys.exit(f"id 重複：{ln['id']}")
        seen.add(ln["id"])
        v = voices.get(ln.get("v", default))
        if not v:
            sys.exit(f"{ln['id']} 的聲音代號「{ln.get('v')}」沒有定義在 voices")
        ln["_voice"] = ln.get("voice", v["voice"])
        ln["_rate"] = ln.get("rate", v.get("rate", "+0%"))
        ln["_pitch"] = ln.get("pitch", v.get("pitch", "+0Hz"))
        ln["_say"] = ln.get("say", ln["text"]).replace("｜", "").replace("|", "")
        out.append(ln)
    return out


def key(ln):
    return hashlib.md5(f"{ln['_voice']}|{ln['_rate']}|{ln['_pitch']}|{ln['_say']}".encode("utf-8")).hexdigest()[:12]


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, args)], check=True)


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]).decode().strip())


def estimate(text):
    pun = sum(1 for c in text if c in "，。、；：！？「」,.!?")
    zh = sum(1 for c in text if ord(c) > 0x2E80) - pun
    en = sum(1 for c in text if c.isascii() and c.isalnum())
    return zh * 0.21 + pun * 0.12 + en * 0.07 + 0.3


async def synth(ln, mp3):
    import edge_tts
    last = None
    for k in range(4):
        try:
            await edge_tts.Communicate(ln["_say"], ln["_voice"], rate=ln["_rate"], pitch=ln["_pitch"]).save(str(mp3))
            if mp3.exists() and mp3.stat().st_size > 1000:
                return
            last = "檔案是空的"
        except Exception as e:
            last = e
        print(f"  重試 {ln['id']}（{k + 1}）：{last}")
        await asyncio.sleep(2 + k * 2)
    sys.exit(f"失敗：{ln['id']}，最後的錯誤：{last}\n→ 確認這台電腦連得到網路（speech.platform.bing.com），或稍後再試。")


def to_wav(mp3, wav):
    # 去頭尾靜音、統一 48k 單聲道
    ff("-i", mp3, "-af", "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
       "silenceremove=start_periods=1:start_threshold=-50dB,areverse", "-ar", SR, "-ac", 1, wav)


async def main():
    ap = argparse.ArgumentParser(description="台灣腔旁白產生器（edge-tts）")
    ap.add_argument("lines", nargs="?")
    ap.add_argument("--concat", action="store_true", help="串成 narration.wav 並輸出 cues.json")
    ap.add_argument("--dry", action="store_true", help="不連網，用估計長度產生靜音檔")
    ap.add_argument("--only", nargs="*", help="只重做這些 id")
    ap.add_argument("--list", metavar="LOCALE", help="列出聲音，例如 zh-TW")
    a = ap.parse_args()

    if a.list:
        import edge_tts
        for v in await edge_tts.list_voices():
            if v["Locale"].lower().startswith(a.list.lower()):
                print(f'{v["ShortName"]:28} {v["Gender"]}')
        return
    if not a.lines:
        ap.error("請給 lines.json 或 lines.txt")

    src = Path(a.lines).resolve()
    cfg = load(src)
    lines = norm(cfg)
    out = (src.parent / cfg.get("out", "旁白")).resolve()
    out.mkdir(parents=True, exist_ok=True)
    cache_p = out / ".tts_cache.json"
    try:
        cache = json.loads(cache_p.read_text(encoding="utf-8"))
    except Exception:
        cache = {}
    if not a.dry:
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            sys.exit("缺少 edge-tts：請先執行  python -m pip install edge-tts")
    if (a.dry or a.concat) and not HAS_FFMPEG:
        sys.exit("--dry／--concat 需要 ffmpeg（Windows：winget install Gyan.FFmpeg，裝完重開視窗）")

    report = []
    for ln in lines:
        k = key(ln)
        stem = ("dry_" if a.dry else "") + ln["id"]
        mp3, wav = out / f"{stem}.mp3", out / f"{stem}.wav"
        force = a.only is not None and ln["id"] in a.only
        skip = a.only is not None and not force
        if a.dry:
            if force or not wav.exists() or cache.get(stem) != k:
                ff("-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=mono", "-t", f"{estimate(ln['_say']):.3f}", wav)
                cache[stem] = k
        elif not skip and (force or not mp3.exists() or cache.get(stem) != k):
            await synth(ln, mp3)
            cache[stem] = k
            if wav.exists():
                wav.unlink()
            print(f"OK  {ln['id']:6s} {ln['_voice']} {ln['_rate']} {ln['_pitch']}  {ln['_say']}")
        if not a.dry and HAS_FFMPEG and mp3.exists() and not wav.exists():
            to_wav(mp3, wav)
        d = dur(wav) if HAS_FFMPEG and wav.exists() else None
        ln["_file"] = wav if (HAS_FFMPEG and wav.exists()) else mp3
        ln["_dur"] = d
        report.append({"id": ln["id"], "file": ln["_file"].name, "dur": round(d, 3) if d else None, "voice": ln["_voice"],
                       "rate": ln["_rate"], "pitch": ln["_pitch"], "text": ln["text"], "say": ln["_say"]})
    cache_p.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / ("dry_report.json" if a.dry else "report.json")).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    if a.concat or a.dry:
        tl = {"lead": 1.2, "gap_line": 0.5, "tail": 3.0} | cfg.get("timeline", {})
        t, cues, inputs, filt = float(tl["lead"]), [], [], []
        prev_gap = None
        for i, ln in enumerate(lines):
            if i:
                t += float(prev_gap if prev_gap is not None else tl["gap_line"])
            d = ln["_dur"]
            caps = []
            if not ln.get("nocap"):
                chunks = [c for c in re.split(r"[｜|]", ln["text"]) if c.strip()]
                w = [max(len(c), 2) for c in chunks]
                ct = t
                for c, wc in zip(chunks, w):
                    cd = d * wc / sum(w)
                    caps.append({"text": c, "start": round(ct, 3), "end": round(ct + cd, 3)})
                    ct += cd
            cues.append({"id": ln["id"], "text": re.sub(r"[｜|]", "", ln["text"]), "start": round(t, 3), "end": round(t + d, 3), "caps": caps})
            inputs += ["-i", str(ln["_file"])]
            ms = int(t * 1000)
            filt.append(f"[{i}]aresample={SR},adelay={ms}|{ms}[a{i}]")
            t += d
            prev_gap = ln.get("gap")
        total = round(t + float(tl["tail"]), 3)
        filt.append("".join(f"[a{i}]" for i in range(len(lines))) + f"amix=inputs={len(lines)}:normalize=0,apad=whole_dur={total}[out]")
        script = out / ".mix.txt"
        script.write_text(";".join(filt), encoding="utf-8")
        nar = out / ("dry_narration.wav" if a.dry else "narration.wav")
        ff(*inputs, "-filter_complex_script", script, "-map", "[out]", "-ar", SR, "-ac", 2, "-t", total, nar)
        (out / ("dry_cues.json" if a.dry else "cues.json")).write_text(
            json.dumps({"total": total, "dry": a.dry, "lines": cues}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n串接完成：{nar.name}，總長 {total} 秒（時間軸：{'dry_' if a.dry else ''}cues.json）")

    print("\n全部完成！檔案在：", out)
    if not a.dry:
        print("（如果是 Claude 請你執行的，現在可以回到 Claude 對話說「旁白好了」。）")


if __name__ == "__main__":
    asyncio.run(main())
