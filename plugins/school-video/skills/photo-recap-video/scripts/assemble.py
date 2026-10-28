"""通用剪接：一個 edl.json 描述整支片（影片片段、照片推拉、字卡、定格、字幕、旁白、音效、配樂），輸出成片並自動量響度。
用法：python assemble.py edl.json            （相對路徑以 edl.json 所在資料夾為準）
edl.json：
{
 "size": [1080, 1920], "fps": 30, "out": "cut/film.mp4",
 "transition": 0.0,                      # 段與段之間交叉淡化秒數；0＝硬切
 "segments": [
  {"id": "S1", "type": "clip", "file": "clips/S1.mp4", "in": 0.0, "out": 3.2, "keep_audio": false, "audio_gain": -6},
  {"id": "P1", "type": "image", "file": "photos/poster.jpg", "dur": 3.0, "motion": "in", "fit": "blur"},
  {"id": "C1", "type": "card", "file": "cards/C1.png", "dur": 3.5, "anim": "pop"},
  {"id": "END", "type": "freeze", "file": "clips/S9.mp4", "at": -0.05, "dur": 4.6, "dim": 0.45},
  {"id": "BLK", "type": "color", "color": "#000000", "dur": 0.5}
 ],
 "overlays": [{"file": "cards/end_text.png", "seg": "END", "at": 0.3, "dur": 4.0, "fade": 0.3}],   # 透明 PNG 疊在畫面上
 "subtitles": {"style": {"size": 64, "margin_v": 260, "outline": 5, "color": "#FFFFFF", "outline_color": "#000000"},
               "items": [{"seg": "S1", "at": 0.2, "dur": 2.6, "text": "同學們好！", "pos": "bottom"}]},
 "voice": [{"file": "voice/n1.wav", "seg": "S1", "at": 0.2, "gain": 0}],
 "sfx":   [{"file": "sfx/pop.mp3", "seg": "C1", "at": 0.0, "gain": -8}],
 "music": {"file": "music/bgm.mp3", "gain": -6, "duck": true, "duck_depth": 8, "fade_in": 0.5, "fade_out": 2.0, "offset": 0},
 "loudness": {"I": -16, "TP": -1.5}
}
時間：寫 "seg"+"at"（相對該段開頭）或直接寫 "start"（全片秒數）。
motion：in（慢推）｜out（慢拉）｜left｜right｜up｜down｜none。fit：cover（裁滿）｜blur（完整放進、兩側模糊底）。
card anim：pop（輕微彈入）｜fade｜none。freeze at：負數＝從片尾往前算。"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ROOT = None
SR = 48000
# 字幕字型：Windows 用微軟正黑體，其他系統用 Noto Sans CJK TC（可在 subtitles.style.font 覆寫）
DEFAULT_FONT = "Microsoft JhengHei" if os.name == "nt" else "Noto Sans CJK TC Black"


def P(x):
    p = Path(x)
    return p if p.is_absolute() else ROOT / p


def run(cmd, **kw):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit(f"指令失敗：{' '.join(map(str, cmd))[:300]}\n{r.stderr[-1500:]}")
    return r


def dur_of(p):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).stdout.strip())


def has_audio(p):
    return bool(run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", p]).stdout.strip())


class Writer:
    """把 PIL 影格直接餵給 ffmpeg。"""
    def __init__(self, dst, W, H, fps):
        self.p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                                   "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", str(dst)], stdin=subprocess.PIPE)

    def put(self, im):
        self.p.stdin.write(im.convert("RGB").tobytes())

    def close(self):
        self.p.stdin.close(); self.p.wait()


def cover(im, W, H):
    s = max(W / im.width, H / im.height)
    im = im.resize((max(W, round(im.width * s)), max(H, round(im.height * s))), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))


def blurfit(im, W, H):
    bg = cover(im, W, H).filter(ImageFilter.GaussianBlur(max(W, H) / 40))
    bg = ImageEnhance.Brightness(bg).enhance(0.7)
    s = min(W / im.width, H / im.height); fg = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    bg.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2))
    return bg


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * min(1, max(0, t)))


def moving(base, W, H, n, motion, amount=0.10):
    """base 比畫面大 (1+amount) 倍；每格裁一個視窗再縮回 W×H（Ken Burns）。"""
    BW, BH = base.size
    for i in range(n):
        t = ease(i / max(1, n - 1))
        if motion in ("in", "out"):
            z = 1 + amount * (t if motion == "in" else 1 - t)
            cw, ch = BW / z, BH / z; x, y = (BW - cw) / 2, (BH - ch) / 2
        else:
            cw, ch = BW / (1 + amount / 2), BH / (1 + amount / 2)
            dx, dy = BW - cw, BH - ch
            x = {"left": dx * (1 - t), "right": dx * t}.get(motion, dx / 2)
            y = {"up": dy * (1 - t), "down": dy * t}.get(motion, dy / 2)
        yield base.resize((W, H), Image.BICUBIC, box=(x, y, x + cw, y + ch))


def render_seg(s, i, tmp, W, H, fps):
    dst = tmp / f"seg{i:03d}.mp4"; t = s["type"]
    if t == "clip":
        src = P(s["file"]); a = float(s.get("in", 0)); b = float(s["out"]) if s.get("out") is not None else dur_of(src)
        s["dur"] = round(b - a, 4); n = max(1, round(s["dur"] * fps))
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}" if s.get("fit", "cover") == "cover" else
              f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:3,eq=brightness=-0.1[bg];"
              f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{a:.3f}", "-i", src, "-t", f"{s['dur']:.3f}", "-filter_complex",
             f"[0:v]{vf},fps={fps},setsar=1,tpad=stop_mode=clone:stop_duration=2[v]", "-map", "[v]", "-frames:v", str(n), "-an",
             "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", dst])
        return dst
    n = max(1, round(float(s["dur"]) * fps)); w = Writer(dst, W, H, fps)
    if t == "image":
        im = ImageOps.exif_transpose(Image.open(P(s["file"]))).convert("RGB")
        amt = 0.10 if s.get("motion", "in") != "none" else 0.0
        BW, BH = round(W * (1 + amt)), round(H * (1 + amt))
        base = blurfit(im, BW, BH) if s.get("fit", "cover") == "blur" else cover(im, BW, BH)
        for f in moving(base, W, H, n, s.get("motion", "in"), amt):
            w.put(f)
    elif t == "card":
        im = cover(Image.open(P(s["file"])).convert("RGB"), W, H); anim = s.get("anim", "pop"); k = max(1, round(0.3 * fps))
        for j in range(n):
            if anim == "pop" and j < k:
                z = 1.08 - 0.08 * ease(j / k)
                cw, ch = W / z, H / z; f = im.resize((W, H), Image.BICUBIC, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))
                f = Image.blend(Image.new("RGB", (W, H), (255, 255, 255)), f, min(1, 0.4 + j / k))
            elif anim == "fade" and j < k:
                f = Image.blend(Image.new("RGB", (W, H)), im, j / k)
            else:
                f = im
            w.put(f)
    elif t == "freeze":
        src = P(s["file"]); at = float(s.get("at", -0.05)); at = dur_of(src) + at if at < 0 else at
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, at):.3f}", "-i", str(src), "-frames:v", "1",
                              "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
        import io
        im = cover(Image.open(io.BytesIO(raw)).convert("RGB"), W, H)
        if s.get("dim"):
            im = ImageEnhance.Brightness(im).enhance(1 - float(s["dim"]))
        for f in moving(cover(im, round(W * 1.04), round(H * 1.04)), W, H, n, s.get("motion", "in"), 0.04):
            w.put(f)
    elif t == "color":
        c = s.get("color", "#000000").lstrip("#"); im = Image.new("RGB", (W, H), tuple(int(c[k:k + 2], 16) for k in (0, 2, 4)))
        for _ in range(n):
            w.put(im)
    else:
        sys.exit(f"不認得的 segment type：{t}")
    w.close(); s["dur"] = n / fps
    return dst


def ass_time(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def ass_color(hexc, alpha=0):
    c = hexc.lstrip("#"); return f"&H{alpha:02X}{c[4:6]}{c[2:4]}{c[0:2]}"


def write_ass(sub, W, H, when, dst):
    st = {"size": round(72 * min(W, H) / 1080), "margin_v": round(H * 0.13), "outline": 5, "color": "#FFFFFF", "outline_color": "#000000",
          "font": DEFAULT_FONT} | sub.get("style", {})
    head = (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
    for name, al in (("bottom", 2), ("top", 8), ("center", 5)):
        head += (f"Style: {name},{st['font']},{st['size']},{ass_color(st['color'])},&H000000FF,{ass_color(st['outline_color'])},&H64000000,"
                 f"0,0,0,0,100,100,0,0,1,{st['outline']},2,{al},{round(W * 0.06)},{round(W * 0.06)},{st['margin_v']},1\n")
    ev = "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    for it in sub.get("items", []):
        a = when(it); b = a + float(it["dur"]) if "dur" in it else float(it["end"])
        txt = it["text"].replace("\n", "\\N")
        if it.get("color"):
            txt = "{\\c" + ass_color(it["color"]) + "}" + txt
        ev += f"Dialogue: 0,{ass_time(a)},{ass_time(b)},{it.get('pos', 'bottom')},,0,0,0,,{{\\fad(120,120)}}{txt}\n"
    dst.write_text(head + ev, encoding="utf-8")


def main():
    global ROOT
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ep = Path(sys.argv[1]).resolve(); ROOT = ep.parent; E = json.loads(ep.read_text(encoding="utf-8"))
    W, H = E.get("size", [1080, 1920]); fps = E.get("fps", 30); T = float(E.get("transition", 0)); segs = E["segments"]
    out = P(E.get("out", "cut/film.mp4")); out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="asm_"))
    try:
        files = []
        for i, s in enumerate(segs):
            files.append(render_seg(s, i, tmp, W, H, fps)); print(f"[seg] {s.get('id', i)} {s['type']} {s['dur']:.2f}s", flush=True)
        starts, t = {}, 0.0
        for i, s in enumerate(segs):
            s["_start"] = t; starts[s.get("id", str(i))] = t; t += s["dur"] - (T if i < len(segs) - 1 else 0)
        total = t

        def when(it):
            if "start" in it:
                return float(it["start"])
            if it.get("seg") not in starts:
                sys.exit(f"找不到 seg：{it.get('seg')}")
            return starts[it["seg"]] + float(it.get("at", 0))

        # ── 影像：串接（硬切或交叉淡化）→ 疊圖 → 字幕
        inputs, fc, last = [], [], None
        if T > 0 and len(files) > 1:
            for f in files:
                inputs += ["-i", f]
            last = "[0:v]"
            for i in range(1, len(files)):
                off = segs[i]["_start"]
                fc.append(f"{last}[{i}:v]xfade=transition=fade:duration={T}:offset={off:.4f}[x{i}]"); last = f"[x{i}]"
            nin = len(files)
        else:
            lst = tmp / "list.txt"; lst.write_text("".join(f"file '{Path(f).as_posix()}'\n" for f in files), encoding="utf-8")
            inputs += ["-f", "concat", "-safe", "0", "-i", lst]; last = "[0:v]"; nin = 1
        for k, ov in enumerate(E.get("overlays", [])):
            a = when(ov); d = float(ov.get("dur", 3)); fd = float(ov.get("fade", 0.3))
            inputs += ["-loop", "1", "-t", f"{a + d:.3f}", "-i", P(ov["file"])]
            j = nin + k
            fc.append(f"[{j}:v]format=rgba,scale={W}:{H}:force_original_aspect_ratio=decrease,"
                      f"fade=in:st={a:.3f}:d={fd}:alpha=1,fade=out:st={a + d - fd:.3f}:d={fd}:alpha=1[o{k}]")
            fc.append(f"{last}[o{k}]overlay=(W-w)/2:(H-h)/2:enable='between(t,{a:.3f},{a + d:.3f})'[v{k}]"); last = f"[v{k}]"
        if E.get("subtitles", {}).get("items"):
            ass = tmp / "subs.ass"; write_ass(E["subtitles"], W, H, when, ass)
            fc.append(f"{last}ass=subs.ass[vs]"); last = "[vs]"
        fc.append(f"{last}format=yuv420p[vout]")
        vid = tmp / "video.mp4"
        run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(fc), "-map", "[vout]", "-t", f"{total:.3f}",
             "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-r", str(fps), vid], cwd=tmp)

        # ── 聲音：旁白＋音效＋鏡頭原音＋配樂（旁白時自動壓低）→ 兩段式 loudnorm
        ain, parts, vb, fx = [], [], [], []
        def add(file, start, gain, a=None, b=None, tag="fx"):
            if a is not None:
                ain.extend(["-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(file)])
            else:
                ain.extend(["-i", str(file)])
            k = sum(1 for x in ain if x == "-i") - 1
            lab = f"a{k}"
            parts.append(f"[{k}:a]aresample={SR},aformat=channel_layouts=stereo,volume={gain}dB,adelay={int(start * 1000)}:all=1[{lab}]")
            (vb if tag == "voice" else fx).append(f"[{lab}]")
        for v in E.get("voice", []):
            add(P(v["file"]), when(v), v.get("gain", 0), tag="voice")
        for v in E.get("sfx", []):
            add(P(v["file"]), when(v), v.get("gain", -6))
        for s in segs:
            if s["type"] == "clip" and s.get("keep_audio") and has_audio(P(s["file"])):
                a = float(s.get("in", 0)); add(P(s["file"]), s["_start"], s.get("audio_gain", 0), a, a + s["dur"])
        mus = E.get("music")
        if mus:
            mk = sum(1 for x in ain if x == "-i"); md = dur_of(P(mus["file"])) - float(mus.get("offset", 0))
            if md < total:
                print(f"  ⚠ 配樂 {md:.1f}s 比片長 {total:.1f}s 短：尾端會沒有音樂（延長配樂或縮短片子）")
            ain += ["-ss", f"{float(mus.get('offset', 0)):.3f}", "-i", str(P(mus["file"]))]
            parts.append(f"[{mk}:a]aresample={SR},aformat=channel_layouts=stereo,volume={mus.get('gain', -6)}dB,atrim=0:{total:.3f},"
                         f"afade=t=in:d={mus.get('fade_in', 0.5)},afade=t=out:st={max(0, min(md, total) - mus.get('fade_out', 2)):.3f}:d={mus.get('fade_out', 2)}[mus]")
        mixes = []
        if vb:
            parts.append(f"{''.join(vb)}amix=inputs={len(vb)}:normalize=0[vbus]")
            if mus and mus.get("duck", True):
                parts.append("[vbus]asplit[vmain][vsc]")
                ratio = max(2, round(10 ** (mus.get("duck_depth", 8) / 10)))
                parts.append(f"[mus][vsc]sidechaincompress=threshold=0.02:ratio={ratio}:attack=30:release=450:makeup=1[mduck]")
                mixes += ["[vmain]", "[mduck]"]
            else:
                mixes += ["[vbus]"] + (["[mus]"] if mus else [])
        elif mus:
            mixes.append("[mus]")
        mixes += fx
        if not mixes:
            parts.append(f"anullsrc=r={SR}:cl=stereo,atrim=0:{total:.3f}[mix]")
        else:
            parts.append(f"{''.join(mixes)}amix=inputs={len(mixes)}:normalize=0,apad,atrim=0:{total:.3f}[mix]")
        L = E.get("loudness", {}); I, TP = L.get("I", -16), L.get("TP", -1.5)
        rawmix = tmp / "mix.wav"
        run(["ffmpeg", "-y", "-v", "error", *ain, "-filter_complex", ";".join(parts), "-map", "[mix]", "-ar", str(SR), rawmix] if ain else
            ["ffmpeg", "-y", "-v", "error", "-filter_complex", ";".join(parts), "-map", "[mix]", rawmix])
        m = run(["ffmpeg", "-v", "info", "-i", rawmix, "-af", f"loudnorm=I={I}:TP={TP}:LRA=11:print_format=json", "-f", "null", "-"]).stderr
        j = json.loads(m[m.rfind("{"):m.rfind("}") + 1])
        aud = tmp / "mix_norm.wav"
        if float(j["input_i"]) < -60:
            shutil.copy(rawmix, aud)
        else:
            run(["ffmpeg", "-y", "-v", "error", "-i", rawmix, "-af",
                 f"loudnorm=I={I}:TP={TP}:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
                 f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,aresample={SR}", aud])
        run(["ffmpeg", "-y", "-v", "error", "-i", vid, "-i", aud, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
             "-shortest", "-movflags", "+faststart", out])
        # ── 報告
        r = subprocess.run(["ffmpeg", "-i", str(out), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
        summ = r[r.rfind("Summary:"):]
        lufs = re.search(r"I:\s*(-?[\d.]+) LUFS", summ); pk = re.search(r"Peak:\s*(-?[\d.]+) dBFS", summ)
        rep = dict(out=str(out), dur=round(dur_of(out), 2), size_mb=round(out.stat().st_size / 1e6, 1), lufs=float(lufs.group(1)) if lufs else None,
                   true_peak=float(pk.group(1)) if pk else None, segments={k: round(v, 2) for k, v in starts.items()})
        (out.with_suffix(".report.json")).write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(rep, ensure_ascii=False))
        if rep["lufs"] is not None and not (I - 1 <= rep["lufs"] <= I + 1):
            print(f"  ⚠ 響度 {rep['lufs']} 偏離目標 {I}")
        if rep["true_peak"] is not None and rep["true_peak"] > -1.0:
            print(f"  ⚠ 峰值 {rep['true_peak']} dBFS 高於 −1")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
