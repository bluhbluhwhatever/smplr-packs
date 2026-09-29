"""Makes the SMPLR test packs: sounds made in code, so downloading can be
tested before real artist packs arrive. Run from the repo root:

    python3 tools/make_test_packs.py

Needs numpy, scipy and ffmpeg. Writes packs/<id>/*.m4a and index.json.
"""
import json
import os
import subprocess
import tempfile

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rng = np.random.default_rng(7)


def t(sec):
    return np.arange(int(sec * SR)) / SR


def env(sec, decay, attack=0.002):
    x = t(sec)
    e = np.exp(-x / decay)
    a = np.minimum(1.0, x / attack)
    return e * a


def filt(x, kind, f, order=2):
    if kind == "band":
        sos = butter(order, f, btype="band", fs=SR, output="sos")
    else:
        sos = butter(order, f, btype=kind, fs=SR, output="sos")
    return sosfilt(sos, x)


def norm(x, peak=0.9):
    m = np.max(np.abs(x))
    if m < 1e-9:
        return x
    return x * (peak / m)


def fade_out(x, sec=0.01):
    n = min(len(x), int(sec * SR))
    x = x.copy()
    x[-n:] *= np.linspace(1, 0, n)
    return x


def sat(x, d):
    return np.tanh(x * d) / np.tanh(d)


# one shots

def kick(f0=130, f1=45, sweep=0.05, decay=0.35, drive=1.5, click=0.3):
    x = t(decay * 3)
    f = f1 + (f0 - f1) * np.exp(-x / sweep)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * env(decay * 3, decay)
    clk = filt(rng.standard_normal(len(x)), "high", 2000) * env(decay * 3, 0.004) * click
    return fade_out(norm(sat(body + clk, drive)))


def snare(tone=190, decay=0.18, noise=0.8, lo=1500, hi=8000):
    n = int(decay * 4 * SR)
    x = t(decay * 4)
    body = np.sin(2 * np.pi * tone * x) * env(decay * 4, decay * 0.4)
    nz = filt(rng.standard_normal(n), "band", [lo, hi]) * env(decay * 4, decay) * noise
    return fade_out(norm(sat(body + nz * 2, 1.3)))


def clap(decay=0.2):
    n = int(0.6 * SR)
    nz = filt(rng.standard_normal(n), "band", [900, 5000])
    e = np.zeros(n)
    for k, off in enumerate([0, 0.011, 0.022]):
        s = int(off * SR)
        e[s:] += np.exp(-np.arange(n - s) / SR / 0.008) * (0.7 + 0.1 * k)
    s = int(0.03 * SR)
    e[s:] += np.exp(-np.arange(n - s) / SR / decay)
    return fade_out(norm(nz * e))


def hat(decay=0.05, lo=7000):
    n = int(max(0.12, decay * 5) * SR)
    nz = filt(rng.standard_normal(n), "high", lo, 4)
    return fade_out(norm(nz * env(n / SR, decay)))


def shaker():
    n = int(0.25 * SR)
    nz = filt(rng.standard_normal(n), "band", [4000, 10000])
    x = t(0.25)
    e = np.sin(np.pi * np.minimum(1, x / 0.25)) ** 3
    return fade_out(norm(nz * e))


def tom(f=110, decay=0.25):
    x = t(decay * 3)
    ff = f * (1 + 0.5 * np.exp(-x / 0.03))
    ph = 2 * np.pi * np.cumsum(ff) / SR
    return fade_out(norm(np.sin(ph) * env(decay * 3, decay)))


def rim():
    x = t(0.15)
    s = np.sin(2 * np.pi * 1700 * x) + 0.6 * np.sin(2 * np.pi * 820 * x)
    nz = filt(rng.standard_normal(len(x)), "band", [2000, 6000]) * 0.4
    return fade_out(norm((s + nz) * env(0.15, 0.015)))


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def bass(note=33, sec=0.9, cut=500, kind="saw"):
    x = t(sec)
    f = midi(note)
    if kind == "sine":
        w = np.sin(2 * np.pi * f * x) + 0.2 * np.sin(4 * np.pi * f * x)
    else:
        w = 2 * ((f * x) % 1) - 1
        w = filt(w, "low", cut, 2)
    e = env(sec, sec * 0.6, 0.004)
    return fade_out(norm(sat(w * e, 1.6)), 0.05)


def ep(notes, sec=2.2, trem=4.5):
    x = t(sec)
    out = np.zeros(len(x))
    for n in notes:
        f = midi(n)
        tone = np.sin(2 * np.pi * f * x + 0.8 * np.sin(2 * np.pi * f * x) * np.exp(-x / 0.3))
        out += tone * env(sec, 0.9, 0.005)
    out *= 1 + 0.25 * np.sin(2 * np.pi * trem * x)
    return fade_out(norm(out), 0.08)


def pad_chord(notes, sec=3.0):
    x = t(sec)
    out = np.zeros(len(x))
    for n in notes:
        for d in (-0.08, 0.08):
            f = midi(n) * 2 ** (d / 12)
            out += 2 * ((f * x) % 1) - 1
    out = filt(out, "low", 1400)
    a = np.minimum(1, x / 0.4)
    r = np.minimum(1, (sec - x) / 0.8)
    return norm(out * a * r * 0.5)


def pluck(note, sec=0.8):
    x = t(sec)
    f = midi(note)
    w = np.sign(np.sin(2 * np.pi * f * x)) * 0.6 + np.sin(2 * np.pi * f * x)
    w = filt(w, "low", 2500)
    return fade_out(norm(w * env(sec, 0.18)))


def riser(sec=2.0):
    x = t(sec)
    nz = rng.standard_normal(len(x))
    out = np.zeros(len(x))
    step = int(0.05 * SR)
    for i in range(0, len(x), step):
        c = 400 + 7000 * (i / len(x)) ** 2
        seg = filt(nz[max(0, i - 400):i + step], "band", [c * 0.7, c * 1.3])
        out[i:i + step] = seg[-len(out[i:i + step]):]
    return fade_out(norm(out * np.minimum(1, x / sec) ** 2))


def vinyl(sec=2.0):
    n = int(sec * SR)
    hiss = filt(rng.standard_normal(n), "band", [800, 6000]) * 0.08
    crack = np.zeros(n)
    idx = rng.integers(0, n, 70)
    crack[idx] = rng.uniform(-1, 1, 70)
    crack = filt(crack, "high", 1500)
    return norm(hiss + crack * 3)


def blip(note=84):
    x = t(0.3)
    f = midi(note) * (1 + 0.8 * np.exp(-x / 0.02))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return fade_out(norm(np.sin(ph) * env(0.3, 0.07)))


def vox(vowel="a", note=57, sec=0.8):
    """A made up sung vowel: a buzz through three formant filters."""
    forms = {"a": [800, 1150, 2900], "o": [450, 800, 2830], "e": [400, 2000, 2550]}
    x = t(sec)
    f = midi(note) * (1 + 0.01 * np.sin(2 * np.pi * 5.5 * x))
    ph = np.cumsum(f) / SR
    buzz = 2 * (ph % 1) - 1
    out = np.zeros(len(x))
    for k, fc in enumerate(forms[vowel]):
        out += filt(buzz, "band", [fc * 0.85, fc * 1.15]) / (k + 1)
    a = np.minimum(1, x / 0.05)
    r = np.minimum(1, (sec - x) / 0.2)
    return norm(out * a * r)


# loops

def mix_at(buf, snd, at, gain=1.0):
    s = int(at * SR)
    if s >= len(buf):
        return
    n = min(len(snd), len(buf) - s)
    buf[s:s + n] += snd[:n] * gain


def drum_loop(bpm, bars, kickp, snarep, hatp, swing=0.0, kit=None):
    beat = 60.0 / bpm
    step = beat / 4
    total = bars * 4 * beat
    buf = np.zeros(int(total * SR) + SR)
    k, s, h = kit
    for b in range(bars):
        for i in range(16):
            at = (b * 16 + i) * step
            if i % 2 == 1:
                at += step * swing
            if kickp[i] == "x":
                mix_at(buf, k, at, 0.9)
            if snarep[i] == "x":
                mix_at(buf, s, at, 0.8)
            if hatp[i] in "xo":
                mix_at(buf, h, at, 0.5 if hatp[i] == "x" else 0.25)
    buf = buf[:int(total * SR)]
    return norm(sat(buf, 1.2))


def keys_loop(bpm, bars, chords):
    beat = 60.0 / bpm
    total = bars * 4 * beat
    buf = np.zeros(int(total * SR) + SR * 3)
    per = total / len(chords)
    for i, c in enumerate(chords):
        mix_at(buf, ep(c, sec=per + 0.6), i * per, 0.7)
    buf = buf[:int(total * SR)]
    return norm(buf)


def bass_loop(bpm, bars, notes):
    beat = 60.0 / bpm
    step = beat / 2
    total = bars * 4 * beat
    buf = np.zeros(int(total * SR) + SR)
    for i, n in enumerate(notes * bars):
        if n is None:
            continue
        mix_at(buf, bass(n, sec=step * 1.4, cut=700), i * step, 0.8)
    buf = buf[:int(total * SR)]
    return norm(buf)


# writing

def write(pack, fname, x):
    d = os.path.join(ROOT, "packs", pack)
    os.makedirs(d, exist_ok=True)
    x = np.clip(x, -1, 1).astype(np.float32)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wavfile.write(tmp.name, SR, (x * 32767).astype(np.int16))
        out = os.path.join(d, fname)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp.name,
                        "-c:a", "aac", "-b:a", "128k", "-ac", "1", "-ar", str(SR), out], check=True)
    os.unlink(tmp.name)


def build_pack(pid, sounds):
    entries = []
    for fname, name, tag, x, extra in sounds:
        write(pid, fname, x)
        e = {"file": fname, "name": name, "tag": tag}
        e.update(extra)
        entries.append(e)
    return entries


def main():
    # TEST PRESSING: a kit in the starting kit's order, so templates find their parts
    tp = [
        ("kick-round.m4a", "ROUND", "KICK", kick(120, 48, 0.05, 0.4), {}),
        ("snare-crack.m4a", "CRACK", "SNARE", snare(200, 0.16), {}),
        ("hat-tight.m4a", "TIGHT", "HAT", hat(0.035), {}),
        ("clap-room.m4a", "ROOM CLAP", "SNARE", clap(0.25), {}),
        ("bass-low-a.m4a", "LOW A", "BASS", bass(33, 1.0, 450), {}),
        ("keys-min9.m4a", "MIN 9", "KEYS", ep([57, 60, 64, 67, 71]), {}),
        ("perc-rim.m4a", "RIM", "PERC", rim(), {}),
        ("hat-open.m4a", "OPEN", "HAT", hat(0.22, 6000), {}),
        ("hat-shaker.m4a", "SHAKER", "HAT", shaker(), {}),
        ("perc-tom.m4a", "TOM", "PERC", tom(105), {}),
        ("snare-soft.m4a", "SOFT", "SNARE", snare(170, 0.12, 0.5, 1000, 5000), {}),
        ("bass-sub-d.m4a", "SUB D", "BASS", bass(38, 1.2, 0, "sine"), {}),
        ("keys-maj7.m4a", "MAJ 7", "KEYS", ep([53, 57, 60, 64]), {}),
        ("keys-pad.m4a", "PAD", "KEYS", pad_chord([50, 57, 60, 65]), {}),
        ("keys-pluck.m4a", "PLUCK", "KEYS", pluck(69), {}),
        ("fx-riser.m4a", "RISER", "FX", riser(), {}),
    ]
    # DUSTY LOOPS: loops at their tempo plus one shots to play over them
    dk = (kick(110, 45, 0.06, 0.3, 2.0), snare(180, 0.14), hat(0.03))
    dl = [
        ("loop-drums-86.m4a", "DUST DRUMS", "LOOP",
         drum_loop(86, 2, "x.....x...x.....", "....x.......x...", "x.x.x.x.x.x.x.xo", 0.2, dk),
         {"bpm": 86, "bars": 2}),
        ("loop-drums-92.m4a", "KNOCK", "LOOP",
         drum_loop(92, 2, "x..x......x..x..", "....x.......x..x", "xxxxxxxxxxxxxxxx", 0.1, dk),
         {"bpm": 92, "bars": 2}),
        ("loop-keys-80.m4a", "LATE KEYS", "LOOP",
         keys_loop(80, 2, [[57, 60, 64, 67], [53, 57, 60, 64]]), {"bpm": 80, "bars": 2}),
        ("loop-bass-86.m4a", "WALKER", "LOOP",
         bass_loop(86, 2, [33, None, 33, 36, None, 38, 40, None]), {"bpm": 86, "bars": 2}),
        ("kick-dust.m4a", "DUST", "KICK", dk[0], {}),
        ("snare-dust.m4a", "DUST", "SNARE", dk[1], {}),
        ("hat-dust.m4a", "DUST", "HAT", dk[2], {}),
        ("perc-blip.m4a", "BLIP", "PERC", blip(), {}),
        ("bass-c.m4a", "BASS C", "BASS", bass(36, 0.8, 600), {}),
        ("keys-stab.m4a", "STAB", "KEYS", ep([60, 63, 67, 70], 0.9), {}),
        ("vox-ah.m4a", "AH", "VOX", vox("a"), {}),
        ("vox-oh.m4a", "OH", "VOX", vox("o", 60), {}),
        ("vox-eh.m4a", "EH", "VOX", vox("e", 55), {}),
        ("fx-vinyl.m4a", "VINYL", "FX", vinyl(), {}),
        ("perc-clap.m4a", "CLAP", "PERC", clap(0.15), {}),
        ("keys-low.m4a", "LOW KEYS", "KEYS", ep([45, 52, 57], 2.5), {}),
    ]
    # TAPE KIT: a darker kit, again in the starting kit's order
    tk = [
        ("kick-deep.m4a", "DEEP", "KICK", kick(100, 40, 0.07, 0.5, 1.2), {}),
        ("snare-tape.m4a", "TAPE", "SNARE", filt(snare(160, 0.2), "low", 5000), {}),
        ("hat-dark.m4a", "DARK", "HAT", hat(0.04, 5000), {}),
        ("snare-side.m4a", "SIDE", "SNARE", rim(), {}),
        ("bass-f.m4a", "F", "BASS", bass(29, 1.0, 350), {}),
        ("keys-dusk.m4a", "DUSK", "KEYS", ep([50, 53, 57, 60], 2.5, 3.0), {}),
        ("perc-wood.m4a", "WOOD", "PERC", tom(320, 0.08), {}),
        ("hat-half.m4a", "HALF", "HAT", hat(0.12, 5500), {}),
        ("hat-tick.m4a", "TICK", "HAT", hat(0.015, 9000), {}),
        ("perc-low-tom.m4a", "LOW TOM", "PERC", tom(80, 0.3), {}),
        ("snare-snap.m4a", "SNAP", "SNARE", clap(0.08), {}),
        ("bass-g.m4a", "G", "BASS", bass(31, 1.0, 380), {}),
        ("keys-hum.m4a", "HUM", "KEYS", pad_chord([45, 52, 57, 60], 3.0), {}),
        ("keys-bell.m4a", "BELL", "KEYS", pluck(81, 1.0), {}),
        ("keys-sad.m4a", "SAD", "KEYS", ep([48, 51, 55, 58], 2.0), {}),
        ("fx-hiss.m4a", "HISS", "FX", vinyl(2.5), {}),
    ]

    packs = [
        {"id": "test-pressing", "title": "TEST PRESSING", "by": "SMPLR TEST PACK",
         "brief": "MADE IN CODE TO TEST DOWNLOADS. REAL ARTIST PACKS TAKE OVER FROM HERE.",
         "date": "OCT 2026", "sounds": build_pack("test-pressing", tp)},
        {"id": "challenge-2", "title": "CHALLENGE 2: NO KICK", "by": "WEEKLY CHALLENGE",
         "brief": "ALL 16 COME FROM PAST PACKS. THE TWIST: NO KICK DRUM ALLOWED.",
         "date": "WEEK 40",
         "sounds": [
             {"pack": "dusty-loops", "file": "loop-keys-80.m4a", "name": "LATE KEYS", "tag": "LOOP", "bpm": 80, "bars": 2},
             {"pack": "test-pressing", "file": "snare-crack.m4a", "name": "CRACK", "tag": "SNARE"},
             {"pack": "tape-kit", "file": "hat-dark.m4a", "name": "DARK", "tag": "HAT"},
             {"pack": "test-pressing", "file": "clap-room.m4a", "name": "ROOM CLAP", "tag": "SNARE"},
             {"pack": "tape-kit", "file": "bass-f.m4a", "name": "F", "tag": "BASS"},
             {"pack": "test-pressing", "file": "keys-min9.m4a", "name": "MIN 9", "tag": "KEYS"},
             {"pack": "dusty-loops", "file": "perc-blip.m4a", "name": "BLIP", "tag": "PERC"},
             {"pack": "test-pressing", "file": "hat-open.m4a", "name": "OPEN", "tag": "HAT"},
             {"pack": "test-pressing", "file": "hat-shaker.m4a", "name": "SHAKER", "tag": "HAT"},
             {"pack": "tape-kit", "file": "perc-wood.m4a", "name": "WOOD", "tag": "PERC"},
             {"pack": "tape-kit", "file": "snare-snap.m4a", "name": "SNAP", "tag": "SNARE"},
             {"pack": "test-pressing", "file": "bass-sub-d.m4a", "name": "SUB D", "tag": "BASS"},
             {"pack": "dusty-loops", "file": "vox-ah.m4a", "name": "AH", "tag": "VOX"},
             {"pack": "dusty-loops", "file": "vox-oh.m4a", "name": "OH", "tag": "VOX"},
             {"pack": "tape-kit", "file": "keys-bell.m4a", "name": "BELL", "tag": "KEYS"},
             {"pack": "dusty-loops", "file": "fx-vinyl.m4a", "name": "VINYL", "tag": "FX"},
         ]},
        {"id": "dusty-loops", "title": "DUSTY LOOPS", "by": "SMPLR TEST PACK",
         "brief": "FOUR LOOPS AT THEIR OWN TEMPO, PLUS ONE SHOTS AND VOICES TO PLAY OVER THEM.",
         "date": "SEP 2026", "sounds": build_pack("dusty-loops", dl)},
        {"id": "tape-kit", "title": "TAPE KIT", "by": "SMPLR TEST PACK",
         "brief": "A DARKER, SLOWER KIT. SITS WELL UNDER 80 BPM.",
         "date": "AUG 2026", "sounds": build_pack("tape-kit", tk)},
    ]
    index = {"v": 1, "artist": "test-pressing", "weekly": "challenge-2", "packs": packs}
    with open(os.path.join(ROOT, "index.json"), "w") as f:
        json.dump(index, f, indent=1)
    print("done")


if __name__ == "__main__":
    main()
