"""原創配樂（純樂器，無版權疑慮）：依段落各寫一段 MIDI → FluidSynth＋GM 音色庫算成音訊 → 交叉淡化接成一首。
用法：python compose_music.py sections.json out.wav [--sf 音色庫.sf2]
sections.json：[{"mood": "mystery", "start": 0, "end": 28.7}, {"mood": "cute", "start": 28.7, "end": 69.6}, ...]
  （start／end 是全片秒數；舊格式用 "name": "A"～"F" 也可以）
mood：mystery 神秘俏皮｜cute 甜美輕快｜march 冒險進行曲｜spooky 俏皮懸疑｜warm 溫暖收尾｜calm 安靜期待
需要：python -m pip install mido；fluidsynth＋GM 音色庫
  Linux／雲端：apt-get install -y fluidsynth fluid-soundfont-gm（音色庫在 /usr/share/sounds/sf2/FluidR3_GM.sf2，MIT 授權）
  Windows：建議在 WSL 或雲端跑；或自行安裝 fluidsynth 並用 --sf 指定 .sf2
前 2 小節只有伴奏（讓旁白進場），每 8 小節旋律休息 2 小節，旁白時再由 assemble.py 自動壓低。"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import mido

SF_CANDIDATES = ["/usr/share/sounds/sf2/FluidR3_GM.sf2", "/usr/share/soundfonts/FluidR3_GM.sf2", "/usr/share/sounds/sf2/default-GM.sf2",
                 "C:/soundfonts/FluidR3_GM.sf2"]
SF = None
TMP = Path(tempfile.mkdtemp(prefix="music_"))
NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11}


def chord(name):
    """'Dm' → [根音, 三音, 五音, 七音?]（相對 C 的半音）。"""
    root = name[:2] if len(name) > 1 and name[1] in "#b" else name[0]
    r = NOTE[root]
    third = 3 if "m" in name[len(root):] else 4
    tones = [r, r + third, r + 7]
    if name.endswith("7"):
        tones.append(r + 10)
    return tones


# 旋律：(拍位置, 和弦音索引 0=根 1=三 2=五 3=高八度根 4=高八度三；可加 .5 表示經過音上一級, 長度拍)
MOT = {
    "A": [(0, 2, .5), (.5, 3, .5), (1, 4, 1), (2.5, 3, .5), (3, 2, 1)],
    "A2": [(0, 4, .5), (.5, 3, .5), (1, 2, .5), (1.5, 1, .5), (2, 2, 1.5), (3.5, 0, .5)],
    "B": [(0, 0, .5), (.5, 1, .5), (1, 2, .5), (1.5, 3, .5), (2, 2, 1), (3, 1, 1)],
    "B2": [(0, 3, .75), (.75, 2, .25), (1, 1, 1), (2, 2, .5), (2.5, 1, .5), (3, 0, 1)],
    "C": [(0, 0, .5), (.5, 0, .25), (.75, 0, .25), (1, 2, 1), (2, 3, .5), (2.5, 2, .5), (3, 4, 1)],
    "C2": [(0, 4, 1), (1, 3, .5), (1.5, 2, .5), (2, 3, 1.5), (3.5, 2, .5)],
    "D": [(0, 0, .5), (.5, 2, .5), (1, 3, .5), (1.5, 2, .5), (2, 1, .75), (2.75, 2, .25), (3, 0, 1)],
    "D2": [(0, 3, .25), (.25, 4, .25), (.5, 3, .5), (1, 2, 1), (2.5, 1, .5), (3, 0, 1)],
}

SECT = {  # 鍵名 A～F 是舊格式；MOOD 對照在下面
    # mystery 開場：神秘又俏皮（D 小調，撥弦＋鋼片琴）
    "A": dict(bpm=100, key=2, prog=["Dm", "Bb", "Gm", "A7"], mel=("A", "A2"), mel_prog=8, mel_oct=72, arp_prog=45, arp_oct=60,
              bass_prog=32, pad_prog=48, pad_vel=38, drums="light", arp="pizz"),
    # cute 甜美輕快（F 大調，鐘琴＋木琴）
    "B": dict(bpm=112, key=5, prog=["F", "Dm", "Bb", "C"], mel=("B", "B2"), mel_prog=9, mel_oct=74, arp_prog=12, arp_oct=62,
              bass_prog=32, pad_prog=48, pad_vel=32, drums="pop", arp="arp8"),
    # march 冒險進行曲（G 大調，法國號＋弦樂斷奏＋定音鼓）
    "C": dict(bpm=124, key=7, prog=["G", "Em", "C", "D"], mel=("C", "C2"), mel_prog=60, mel_oct=67, arp_prog=48, arp_oct=60,
              bass_prog=43, pad_prog=61, pad_vel=40, drums="march", arp="stacc"),
    # spooky 俏皮的懸疑（E 小調，大鍵琴＋木琴＋低音管）
    "D": dict(bpm=116, key=4, prog=["Em", "C", "Am", "B7"], mel=("D", "D2"), mel_prog=13, mel_oct=72, arp_prog=6, arp_oct=60,
              bass_prog=70, pad_prog=19, pad_vel=30, drums="spooky", arp="arp8"),
    # warm 回顧與收尾：溫暖主旋律（C 大調，弦樂＋鐘琴）
    "E": dict(bpm=104, key=0, prog=["C", "Am", "F", "G"], mel=("B", "B2"), mel_prog=9, mel_oct=74, arp_prog=46, arp_oct=60,
              bass_prog=32, pad_prog=48, pad_vel=50, drums="pop", arp="arp8"),
    # calm 安靜的期待感（A 小調轉大調，撥弦＋鋼片琴，較安靜）
    "F": dict(bpm=104, key=9, prog=["Am", "F", "C", "E7"], mel=("A", "B2"), mel_prog=8, mel_oct=72, arp_prog=45, arp_oct=60,
              bass_prog=32, pad_prog=48, pad_vel=36, drums="light", arp="pizz"),
}

MOOD = {"mystery": "A", "cute": "B", "march": "C", "spooky": "D", "warm": "E", "calm": "F"}


def build(name, secs, path):
    S = SECT[name]; tpb = 480; spb = 60 / S["bpm"]
    bars = int(secs / (spb * 4)) + 2
    mid = mido.MidiFile(ticks_per_beat=tpb)
    events = []                                         # (tick, ch, type, note, vel)

    def note(ch, beat, n, length, vel):
        t0 = int(beat * tpb); t1 = int((beat + length) * tpb * 0.95)
        events.append((t0, ch, "on", n, vel)); events.append((t1, ch, "off", n, 0))

    progs = {0: S["mel_prog"], 1: S["arp_prog"], 2: S["bass_prog"], 3: S["pad_prog"], 4: 47}
    for b in range(bars):
        ch_name = S["prog"][b % len(S["prog"])]
        tones = [t + 0 for t in chord(ch_name)]
        base = b * 4
        fade_in = min(1.0, (b + 1) / 2)
        last = b >= bars - 2
        # 低音
        root = 36 + tones[0] % 12
        if S["arp"] == "stacc":
            for k in range(4):
                note(2, base + k, root + (7 if k % 2 else 0), .5, 80)
        else:
            note(2, base, root, 1.5, 84); note(2, base + 2, root + 7, 1.5, 70)
        # 伴奏
        ch_notes = [S["arp_oct"] + (t % 12) for t in tones[:3]]
        if S["arp"] == "pizz":
            for k, bt in enumerate([0, 1, 2, 3]):
                note(1, base + bt, ch_notes[k % 3] + (12 if k == 3 else 0), .4, 70)
        elif S["arp"] == "arp8":
            seq = ch_notes + [ch_notes[0] + 12] + ch_notes[::-1][1:] + [ch_notes[0]]
            for k in range(8):
                note(1, base + k * .5, seq[k % len(seq)], .45, 58)
        elif S["arp"] == "stacc":
            for k in range(8):
                for n in ch_notes:
                    note(1, base + k * .5, n, .25, 52 if k % 2 else 66)
        # 長音鋪底
        for n in ch_notes:
            note(3, base, n - 12 if S["pad_prog"] in (19, 61) else n, 4, int(S["pad_vel"] * fade_in))
        # 旋律：前 2 小節只有伴奏（讓旁白進場），之後兩個動機交替，每 8 小節休息 2 小節
        if b >= 2 and not last and (b % 8) not in (6, 7):
            mot = MOT[S["mel"][(b // 2) % 2]]
            scale_tones = sorted(set(tones[:3]))
            for (bt, idx, ln) in mot:
                octv = int(idx) // 3; t = scale_tones[int(idx) % 3]
                n = S["mel_oct"] + (t % 12) + 12 * octv
                while n > S["mel_oct"] + 19:
                    n -= 12
                note(0, base + bt, n, ln, 92)
        # 鼓
        dr = S["drums"]
        if dr == "pop":
            for k in range(8):
                note(9, base + k * .5, 42, .2, 50 if k % 2 else 64)
            note(9, base, 36, .5, 80); note(9, base + 2, 38, .5, 60); note(9, base + 2.5, 36, .5, 60)
        elif dr == "march":
            for k in range(4):
                note(9, base + k, 38, .2, 70 if k % 2 else 50)
            note(9, base + 3.5, 38, .1, 45); note(9, base + 3.75, 38, .1, 50)
            note(4, base, root + 12, 1, 85)            # 定音鼓
        elif dr == "spooky":
            note(9, base, 36, .5, 70); note(9, base + 2, 75, .2, 70); note(9, base + 3, 76, .2, 60); note(9, base + 3.5, 75, .2, 60)
        elif dr == "light":
            note(9, base + 1, 81, .2, 40); note(9, base + 3, 81, .2, 40)
            if b % 4 == 0:
                note(9, base, 49 if b else 49, 1, 40)
    # 收尾和弦
    end = bars * 4
    for t in chord(S["prog"][0]):
        note(3, end, 60 + t % 12, 4, 60); note(1, end, S["arp_oct"] + t % 12, 2, 60)
    note(2, end, 36 + chord(S["prog"][0])[0] % 12, 4, 80)

    tr = mido.MidiTrack(); mid.tracks.append(tr)
    tr.append(mido.MetaMessage("set_tempo", tempo=int(spb * 1e6)))
    for ch, pg in progs.items():
        tr.append(mido.Message("program_change", channel=ch, program=pg))
    tr.append(mido.Message("control_change", channel=0, control=91, value=50))
    for ch in range(5):
        tr.append(mido.Message("control_change", channel=ch, control=91, value=60))
    tr.append(mido.Message("control_change", channel=3, control=7, value=80))
    events.sort(key=lambda e: (e[0], e[2] == "on"))
    now = 0
    for t, ch, ty, n, v in events:
        tr.append(mido.Message("note_on" if ty == "on" else "note_off", channel=ch, note=max(0, min(127, n)), velocity=v, time=t - now)); now = t
    mid.save(path.with_suffix(".mid"))
    subprocess.run(["fluidsynth", "-ni", "-g", "0.6", "-r", "48000", "-F", str(path), SF, str(path.with_suffix(".mid"))],
                   check=True, capture_output=True)


def main():
    global SF
    ap = argparse.ArgumentParser()
    ap.add_argument("sections"); ap.add_argument("out"); ap.add_argument("--sf"); ap.add_argument("--xfade", type=float, default=1.5)
    a = ap.parse_args()
    SF = a.sf or next((c for c in SF_CANDIDATES if Path(c).exists()), None)
    if not SF or not Path(SF).exists():
        sys.exit("找不到 GM 音色庫（.sf2）。Linux：apt-get install -y fluidsynth fluid-soundfont-gm；或用 --sf 指定路徑")
    if not shutil.which("fluidsynth"):
        sys.exit("找不到 fluidsynth。Linux：apt-get install -y fluidsynth")
    secs = json.load(open(a.sections, encoding="utf-8")); out = Path(a.out)
    X = a.xfade
    parts = []
    for i, s in enumerate(secs):
        name = s.get("name") or MOOD.get(s.get("mood", "warm"))
        if name not in SECT:
            sys.exit(f"第 {i + 1} 段的 mood 不認得：{s.get('mood')}（可用 {', '.join(MOOD)}）")
        d = s["end"] - s["start"] + (X if i < len(secs) - 1 else 4)
        p = TMP / f"{i:02d}_{name}.wav"; build(name, d, p)
        q = TMP / f"{i:02d}_{name}_n.wav"
        fo = "" if i < len(secs) - 1 else f",afade=t=out:st={d - 4:.2f}:d=4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", p, "-af", f"atrim=0:{d:.3f},loudnorm=I=-20:TP=-3{fo},aresample=48000",
                        "-ac", "2", q], check=True)
        parts.append(q)
    cur = parts[0]
    for i, p in enumerate(parts[1:], 1):
        nxt = TMP / f"x{i:02d}.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", cur, "-i", p, "-filter_complex", f"acrossfade=d={X}:c1=tri:c2=tri", nxt], check=True)
        cur = nxt
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", cur, "-af", "aecho=0.8:0.6:40|70:0.15|0.1", out], check=True)
    shutil.rmtree(TMP, ignore_errors=True)
    print("music", out)


if __name__ == "__main__":
    main()
