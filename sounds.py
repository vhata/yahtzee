"""
SoundManager — Synthesized audio for Yahtzee using pure Python.

Generates 16-bit PCM waveforms via struct.pack + math.sin (no numpy).
All sounds are pre-generated at init for zero-latency playback.
"""
from __future__ import annotations

import math
import struct

import pygame

SAMPLE_RATE = 44100


def _generate_samples(
    duration_ms: int, freq: float = 440.0, waveform: str = "sine", volume: float = 0.3, fade_out: bool = True,
) -> bytes:
    """Generate raw 16-bit mono PCM bytes for a tone or noise burst.

    Args:
        duration_ms: Duration in milliseconds.
        freq: Frequency in Hz (ignored for noise).
        waveform: "sine", "square", or "noise".
        volume: Peak amplitude 0.0-1.0.
        fade_out: Apply linear fade-out envelope.

    Returns:
        bytes of signed 16-bit little-endian samples.
    """
    import random as _rand
    num_samples = int(SAMPLE_RATE * duration_ms / 1000)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        # Envelope: linear fade-out
        env = 1.0 - (i / num_samples) if fade_out else 1.0

        if waveform == "sine":
            val = math.sin(2 * math.pi * freq * t)
        elif waveform == "square":
            val = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
        elif waveform == "noise":
            val = _rand.uniform(-1.0, 1.0)
        else:
            val = 0.0

        sample = int(val * volume * env * 32767)
        sample = max(-32768, min(32767, sample))
        samples.append(struct.pack("<h", sample))

    return b"".join(samples)


def _make_sound(pcm_bytes: bytes) -> pygame.mixer.Sound:
    """Wrap raw PCM bytes in a pygame.mixer.Sound."""
    return pygame.mixer.Sound(buffer=pcm_bytes)


def _two_note(freq1: float, freq2: float, note_ms: int = 175, volume: float = 0.25) -> bytes:
    """Generate a two-note chime (ascending)."""
    return _generate_samples(note_ms, freq1, "sine", volume) + \
           _generate_samples(note_ms, freq2, "sine", volume)


def _three_note(freq1: float, freq2: float, freq3: float, note_ms: int = 200, volume: float = 0.25) -> bytes:
    """Generate a three-note fanfare (ascending)."""
    return _generate_samples(note_ms, freq1, "sine", volume) + \
           _generate_samples(note_ms, freq2, "sine", volume) + \
           _generate_samples(note_ms, freq3, "sine", volume)


class SoundManager:
    """Pre-generates and plays all game sound effects.

    All play methods are no-ops when disabled.
    """

    def __init__(self) -> None:
        self._enabled = True

        # Pre-generate all sounds
        # Dice rattle: short noise burst
        self._roll = _make_sound(_generate_samples(200, waveform="noise", volume=0.15))

        # Hold click: soft sine pip
        self._click = _make_sound(_generate_samples(50, freq=800, waveform="sine", volume=0.15))

        # Score chime: C5 → E5 ascending
        self._score = _make_sound(_two_note(523.25, 659.25, note_ms=175, volume=0.25))

        # Game over fanfare: C5 → E5 → G5
        self._fanfare = _make_sound(_three_note(523.25, 659.25, 783.99, note_ms=200, volume=0.25))

    def toggle(self) -> bool:
        """Toggle sound on/off. Returns new enabled state."""
        self._enabled = not self._enabled
        return self._enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    def play_roll(self) -> None:
        if self._enabled:
            self._roll.play()

    def play_click(self) -> None:
        if self._enabled:
            self._click.play()

    def play_score(self) -> None:
        if self._enabled:
            self._score.play()

    def play_fanfare(self) -> None:
        if self._enabled:
            self._fanfare.play()
