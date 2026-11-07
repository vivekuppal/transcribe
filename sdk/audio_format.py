"""In-memory audio conversion shared by capture and speech to text.

Every chunked speech to text path works on one format: 16 kHz, mono, 16-bit PCM.
Converting once, when a phrase is captured, keeps the rolling buffers about six
times smaller than 48 kHz stereo and lets each provider receive audio without
temporary files or an ffmpeg process per phrase.
"""

from __future__ import annotations

import io
import wave

import numpy as np

TARGET_SAMPLE_RATE = 16000
TARGET_SAMPLE_WIDTH = 2
TARGET_CHANNELS = 1
BYTES_PER_SECOND = TARGET_SAMPLE_RATE * TARGET_SAMPLE_WIDTH * TARGET_CHANNELS

_DTYPES = {1: np.uint8, 2: np.int16, 4: np.int32}
_SCALE = {1: 128.0, 2: 32768.0, 4: 2147483648.0}


def _to_float_mono(data: bytes, sample_width: int, channels: int) -> np.ndarray:
    if sample_width not in _DTYPES:
        raise ValueError(f"Unsupported sample width: {sample_width}")
    channels = max(int(channels), 1)
    frame_size = sample_width * channels
    usable = len(data) - (len(data) % frame_size)
    samples = np.frombuffer(data[:usable], dtype=_DTYPES[sample_width]).astype(np.float32)
    if sample_width == 1:
        samples -= 128.0                       # 8-bit WAV data is unsigned
    samples /= _SCALE[sample_width]
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples


_LOWPASS_CACHE: dict[int, np.ndarray] = {}


def _lowpass_taps(sample_rate: int) -> np.ndarray:
    """Windowed-sinc low-pass that keeps speech up to ~7 kHz and removes what would fold back
    above 8 kHz (the Nyquist limit of 16 kHz audio)."""
    taps = _LOWPASS_CACHE.get(sample_rate)
    if taps is None:
        cutoff = 7200.0 / sample_rate                       # cycles per input sample
        length = 4 * int(round(sample_rate / 1000)) + 1     # ~4 ms of taps: 193 at 48 kHz
        n = np.arange(length) - (length - 1) / 2
        taps = 2 * cutoff * np.sinc(2 * cutoff * n) * np.blackman(length)
        taps = (taps / taps.sum()).astype(np.float32)
        _LOWPASS_CACHE[sample_rate] = taps
    return taps


def _resample(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    if sample_rate == TARGET_SAMPLE_RATE or samples.size == 0:
        return samples
    if sample_rate > TARGET_SAMPLE_RATE:
        taps = _lowpass_taps(sample_rate)
        half = taps.size // 2
        # Pad with the edge values so the first and last milliseconds are not faded out.
        padded = np.pad(samples, half, mode="edge")
        samples = np.convolve(padded, taps, mode="valid").astype(np.float32)
        if sample_rate % TARGET_SAMPLE_RATE == 0:
            return samples[::sample_rate // TARGET_SAMPLE_RATE].copy()    # 32 / 48 / 96 kHz
    target_length = int(round(samples.size * TARGET_SAMPLE_RATE / sample_rate))
    if target_length <= 0:
        return np.zeros(0, dtype=np.float32)
    positions = np.linspace(0, samples.size - 1, target_length, dtype=np.float64)
    return np.interp(positions, np.arange(samples.size), samples).astype(np.float32)


def to_pcm16_mono_16k(data: bytes, sample_rate: int, sample_width: int = 2, channels: int = 1) -> bytes:
    """Convert interleaved PCM of any common format to 16 kHz mono 16-bit PCM."""
    if not data:
        return b""
    if int(sample_rate) == TARGET_SAMPLE_RATE and sample_width == 2 and int(channels) <= 1:
        return data[:len(data) - (len(data) % 2)]      # already in the target format
    samples = _resample(_to_float_mono(data, sample_width, channels), int(sample_rate))
    return (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()


def pcm16_to_float32(pcm: bytes) -> np.ndarray:
    """16-bit PCM bytes to the float32 [-1, 1] array local Whisper engines accept directly."""
    usable = len(pcm) - (len(pcm) % 2)
    return np.frombuffer(pcm[:usable], dtype="<i2").astype(np.float32) / 32768.0


def pcm16_to_wav_bytes(pcm: bytes, sample_rate: int = TARGET_SAMPLE_RATE) -> bytes:
    """Wrap 16-bit mono PCM in a WAV header, in memory."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(TARGET_CHANNELS)  # pylint: disable=E1101
        wav_file.setsampwidth(TARGET_SAMPLE_WIDTH)  # pylint: disable=E1101
        wav_file.setframerate(sample_rate)  # pylint: disable=E1101
        wav_file.writeframes(pcm)  # pylint: disable=E1101
    return buffer.getvalue()


def write_pcm16_wav(path: str, pcm: bytes, sample_rate: int = TARGET_SAMPLE_RATE):
    """Write 16-bit mono PCM to a WAV file (for engines that only read files)."""
    with open(path, "wb") as file_handle:
        file_handle.write(pcm16_to_wav_bytes(pcm, sample_rate))
