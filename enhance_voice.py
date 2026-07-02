"""Автоулучшение «глухого» голоса: HPF, EQ, компрессия, нормализация."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile


def _to_mono(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 1:
        return audio.astype(np.float64)
    return audio.mean(axis=1).astype(np.float64)


def _peaking_eq(samples: np.ndarray, sr: int, freq: float, gain_db: float, q: float = 1.4) -> np.ndarray:
    a = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * freq / sr
    alpha = np.sin(w0) / (2 * q)
    cos_w0 = np.cos(w0)

    b0 = 1 + alpha * a
    b1 = -2 * cos_w0
    b2 = 1 - alpha * a
    a0 = 1 + alpha / a
    a1 = -2 * cos_w0
    a2 = 1 - alpha / a

    b = np.array([b0, b1, b2]) / a0
    a_coef = np.array([1.0, a1 / a0, a2 / a0])
    return signal.lfilter(b, a_coef, samples)


def _highpass(samples: np.ndarray, sr: int, cutoff: float = 100.0) -> np.ndarray:
    sos = signal.butter(2, cutoff, btype="highpass", fs=sr, output="sos")
    return signal.sosfilt(sos, samples)


def _compress(samples: np.ndarray, threshold_db: float = -18.0, ratio: float = 2.5) -> np.ndarray:
    threshold = 10 ** (threshold_db / 20)
    out = samples.copy()
    mask = np.abs(out) > threshold
    out[mask] = np.sign(out[mask]) * (threshold + (np.abs(out[mask]) - threshold) / ratio)
    return out


def _normalize(samples: np.ndarray, peak_db: float = -1.0) -> np.ndarray:
    peak = np.max(np.abs(samples))
    if peak == 0:
        return samples
    target = 10 ** (peak_db / 20)
    return samples * (target / peak)


def enhance(samples: np.ndarray, sr: int) -> np.ndarray:
    x = _highpass(samples, sr, 100)
    x = _peaking_eq(x, sr, 300, -4.0)
    x = _peaking_eq(x, sr, 2000, 3.0)
    x = _peaking_eq(x, sr, 4500, 5.0)
    x = _compress(x)
    x = _normalize(x)
    return np.clip(x, -1.0, 1.0)


def main() -> int:
    if len(sys.argv) < 2:
        print("Использование: python enhance_voice.py путь\\к\\файлу.wav")
        return 1

    src = Path(sys.argv[1])
    if not src.exists():
        print(f"Файл не найден: {src}")
        return 1

    sr, audio = wavfile.read(src)
    if audio.dtype == np.int16:
        samples = audio.astype(np.float64) / 32768.0
        out_dtype = np.int16
    elif audio.dtype == np.int32:
        samples = audio.astype(np.float64) / 2147483648.0
        out_dtype = np.int32
    else:
        samples = audio.astype(np.float64)
        out_dtype = np.float32

    stereo = audio.ndim == 2 and audio.shape[1] == 2
    if stereo:
        left = enhance(samples[:, 0], sr)
        right = enhance(samples[:, 1], sr)
        enhanced = np.column_stack([left, right])
    else:
        enhanced = enhance(_to_mono(samples), sr)

    dst = src.with_name(f"{src.stem}_улучшено.wav")
    if out_dtype == np.int16:
        wavfile.write(dst, sr, (enhanced * 32767).astype(np.int16))
    elif out_dtype == np.int32:
        wavfile.write(dst, sr, (enhanced * 2147483647).astype(np.int32))
    else:
        wavfile.write(dst, sr, enhanced.astype(np.float32))

    print(f"Готово: {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
