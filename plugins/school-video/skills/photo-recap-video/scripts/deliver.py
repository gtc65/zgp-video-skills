"""交付版本：從高畫質成片做出 LINE 版（≤ 目標 MB），並列出規格。
用法：python deliver.py cut/film.mp4 [--mb 25] [--name 活動回顧_橫式]
輸出：<name>_高畫質.mp4（複製原檔）、<name>_LINE版.mp4（2-pass，依片長算位元率）、規格摘要。
Cowork 寫回使用者電腦單檔上限約 30MB：LINE 版寫回資料夾；高畫質版 > 30MB 時只在對話中提供下載。"""
import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def probe(p):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_type,width,height,r_frame_rate",
                                   "-of", "json", str(p)], capture_output=True, text=True).stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    return float(j["format"]["duration"]), int(j["format"]["size"]), v["width"], v["height"], v["r_frame_rate"]


def loud(p):
    r = subprocess.run(["ffmpeg", "-i", str(p), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    s = r[r.rfind("Summary:"):]
    i = re.search(r"I:\s*(-?[\d.]+) LUFS", s); pk = re.search(r"Peak:\s*(-?[\d.]+) dBFS", s)
    return (float(i.group(1)) if i else None), (float(pk.group(1)) if pk else None)


ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("--mb", type=float, default=25.0); ap.add_argument("--name")
a = ap.parse_args()
src = Path(a.src).resolve(); name = a.name or src.stem; od = src.parent
dur, size, w, h, fr = probe(src)
hq = od / f"{name}_高畫質.mp4"
if hq != src:
    shutil.copy2(src, hq)
line = od / f"{name}_LINE版.mp4"
abr = 128_000
vbr = int((a.mb * 8e6 / dur - abr) * 0.94)
if size <= a.mb * 1e6:
    shutil.copy2(src, line); how = "原檔已低於上限，直接複製"
else:
    vbr = max(vbr, 400_000)
    tmp = Path(tempfile.mkdtemp()); log = tmp / "2pass"
    base = ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-c:v", "libx264", "-preset", "slow", "-b:v", str(vbr), "-maxrate", str(int(vbr * 1.5)),
            "-bufsize", str(vbr * 2), "-pix_fmt", "yuv420p", "-passlogfile", str(log)]
    subprocess.run(base + ["-pass", "1", "-an", "-f", "mp4", os.devnull], check=True)
    subprocess.run(base + ["-pass", "2", "-c:a", "aac", "-b:a", str(abr), "-movflags", "+faststart", str(line)], check=True)
    shutil.rmtree(tmp, ignore_errors=True); how = f"2-pass {vbr / 1e6:.2f} Mbps"
for p in (hq, line):
    d, s, ww, hh, f = probe(p); I, pk = loud(p)
    ok = "可寫回電腦" if s <= 30e6 else "超過 30MB：只在對話中下載"
    print(f"{p.name}: {ww}×{hh} {f}fps {d:.2f}s {s / 1e6:.1f}MB  {I} LUFS  峰值 {pk} dBFS  [{ok}]")
print(f"LINE 版：{how}")
