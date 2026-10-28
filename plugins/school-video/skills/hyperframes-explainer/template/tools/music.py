# -*- coding: utf-8 -*-
"""自製輕快配樂（純 numpy 合成，無版權疑慮）：木琴感琶音＋貝斯；旁白時自動壓低，場景轉換加上行三連音。
用法：python tools/music.py      → assets/audio/bgm.wav（長度＝cues.json 的 total）
換風格：改 BPM、prog（和弦）、pat（琶音順序）。"""
import json
import os
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cues = json.load(open(os.path.join(ROOT, "cues.json"), encoding="utf-8"))
SR = 48000
T = cues["total"]
N = int(T * SR)
out = np.zeros(N)
fx = np.zeros(N)          # 音效（不受 ducking 影響）


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def tone(buf, m, t0, dur, vel, decay=4.0, harm=(1, 0.35, 0.12)):
    n = int(min(dur + 1.2, T - t0) * SR)
    if n <= 0 or t0 < 0:
        return
    t = np.arange(n) / SR
    env = np.exp(-t * decay) * np.minimum(1, t / 0.004)
    w = sum(a * np.sin(2 * np.pi * hz(m) * (k + 1) * t) * np.exp(-t * k * 2) for k, a in enumerate(harm))
    i0 = int(t0 * SR)
    buf[i0:i0 + n] += vel * env * w


BPM = 104
beat = 60 / BPM
bar = beat * 4
prog = [(41, [65, 69, 72]), (36, [64, 67, 72]), (38, [62, 65, 69]), (34, [62, 65, 70])]   # F - C - Dm - Bb（明亮）
pat = [0, 2, 1, 2, 0, 2, 1, 2]
t, k = 0.0, 0
while t < T - 1:
    root, ch = prog[k % 4]
    tone(out, root, t, bar, 0.22, decay=1.6, harm=(1, 0.2))
    tone(out, root, t + beat * 2, bar / 2, 0.16, decay=2.0, harm=(1, 0.2))
    for i, a in enumerate(pat):
        tone(out, ch[a] + 12, t + i * beat / 2, beat, 0.09 if i % 2 else 0.12, decay=7.0, harm=(1, 0.5, 0.25))
    if k % 2 == 1:
        tone(out, ch[2] + 24, t + beat * 3.5, beat, 0.05, decay=6.0)
    t += bar
    k += 1

for sc in cues["scenes"][1:]:                          # 場景轉換：上行三連音
    for j, m in enumerate([84, 88, 91]):
        tone(fx, m, sc["clip_start"] + 0.08 + j * 0.07, 0.6, 0.05, decay=6)

env = np.zeros(N)                                      # ducking：旁白時壓低
for sc in cues["scenes"]:
    for ln in sc["lines"]:
        a, b = int((ln["start"] - 0.25) * SR), int((ln["end"] + 0.35) * SR)
        env[max(a, 0):min(b, N)] = np.maximum(env[max(a, 0):min(b, N)], 0.6)
kk = int(0.4 * SR)
env = np.convolve(env, np.ones(kk) / kk, mode="same")
out *= 1 - env
fi, fo = int(1.0 * SR), int(3.5 * SR)
out[:fi] *= np.linspace(0, 1, fi)
out[-fo:] *= np.linspace(1, 0, fo) ** 1.5
out = out / max(np.max(np.abs(out)), 1e-9) * 0.5 + fx
Lc, Rc = out.copy(), out.copy()
for d, g in [(0.029, 0.22), (0.047, 0.18), (0.083, 0.13), (0.131, 0.08)]:   # 簡易立體聲殘響
    s1 = int(d * SR); Lc[s1:] += g * out[:-s1]
    s2 = int(d * 1.13 * SR); Rc[s2:] += g * out[:-s2]
st = np.stack([Lc, Rc], 1)
st = st / np.max(np.abs(st)) * 0.45
os.makedirs(os.path.join(ROOT, "assets", "audio"), exist_ok=True)
with wave.open(os.path.join(ROOT, "assets", "audio", "bgm.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
print("bgm ok", T)
