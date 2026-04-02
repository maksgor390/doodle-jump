"""
Генератор звукових файлів та зображень для Doodle Jump
Запускати окремо: python generate_assets.py
"""

import wave
import struct
import math
import os

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)


def write_wav(filename: str, samples: list, sample_rate: int = 44100) -> None:
    with wave.open(filename, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        for s in samples:
            clamped = max(-32767, min(32767, int(s)))
            f.writeframes(struct.pack("<h", clamped))


def generate_jump_sound(filename: str) -> None:
    sample_rate = 44100
    duration = 0.18
    samples = []
    for i in range(int(sample_rate * duration)):
        t = i / sample_rate
        progress = t / duration
        freq = 300 + 700 * (1 - progress)
        envelope = math.exp(-progress * 8)
        val = envelope * 28000 * math.sin(2 * math.pi * freq * t)
        samples.append(val)
    write_wav(filename, samples, sample_rate)
    print(f"  ✓ {filename}")


def generate_break_sound(filename: str) -> None:
    sample_rate = 44100
    duration = 0.35
    samples = []
    for i in range(int(sample_rate * duration)):
        t = i / sample_rate
        progress = t / duration
        noise = ((__import__("random").random() * 2 - 1))
        freq1 = 150 * (1 - progress * 0.7)
        freq2 = 80 * (1 - progress * 0.5)
        tone = (math.sin(2 * math.pi * freq1 * t) +
                math.sin(2 * math.pi * freq2 * t)) * 0.3
        envelope = math.exp(-progress * 5) * (1 - progress)
        val = envelope * 26000 * (noise * 0.6 + tone)
        samples.append(val)
    write_wav(filename, samples, sample_rate)
    print(f"  ✓ {filename}")


def generate_spring_sound(filename: str) -> None:
    sample_rate = 44100
    duration = 0.22
    samples = []
    for i in range(int(sample_rate * duration)):
        t = i / sample_rate
        progress = t / duration
        freq = 500 + 1500 * (1 - progress) ** 2
        envelope = math.exp(-progress * 6)
        vibrato = 1 + 0.05 * math.sin(2 * math.pi * 30 * t)
        val = envelope * 25000 * math.sin(2 * math.pi * freq * t * vibrato)
        samples.append(val)
    write_wav(filename, samples, sample_rate)
    print(f"  ✓ {filename}")


def generate_fall_sound(filename: str) -> None:
    sample_rate = 44100
    duration = 0.5
    samples = []
    for i in range(int(sample_rate * duration)):
        t = i / sample_rate
        progress = t / duration
        freq = 400 - 350 * progress
        envelope = math.exp(-progress * 3) * math.sin(math.pi * progress)
        val = envelope * 22000 * math.sin(2 * math.pi * freq * t)
        samples.append(val)
    write_wav(filename, samples, sample_rate)
    print(f"  ✓ {filename}")


if __name__ == "__main__":
    print("Генерація звукових файлів...")
    generate_jump_sound(os.path.join(ASSETS_DIR, "jump.wav"))
    generate_break_sound(os.path.join(ASSETS_DIR, "break.wav"))
    generate_spring_sound(os.path.join(ASSETS_DIR, "spring.wav"))
    generate_fall_sound(os.path.join(ASSETS_DIR, "fall.wav"))
    print("Готово! Всі файли збережено в папку assets/")
