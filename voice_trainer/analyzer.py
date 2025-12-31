"""Voice analysis module using parselmouth (Praat)."""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import json

import numpy as np
import parselmouth
from parselmouth.praat import call


@dataclass
class VoiceAnalysis:
    """Results from voice analysis."""
    # File info
    filename: str
    duration_seconds: float

    # Pitch metrics (in Hz)
    pitch_mean: float
    pitch_min: float
    pitch_max: float
    pitch_std: float
    pitch_range: float  # max - min

    # Pitch variability
    pitch_variability_percent: float  # (std / mean) * 100

    # Voice register estimates (approximate)
    chest_voice_percent: float  # Time below threshold
    head_voice_percent: float  # Time above threshold
    mixed_voice_percent: float  # Time in middle range

    # Intensity/Volume metrics (in dB)
    intensity_mean: float
    intensity_std: float
    intensity_min: float
    intensity_max: float

    # Speaking metrics
    voiced_fraction: float  # Proportion of time with detected voice
    speaking_rate_estimate: float  # Voiced segments per second (rough proxy for syllable rate)

    # Expressiveness score (composite)
    expressiveness_score: float  # 0-100 based on pitch range and variability

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class VoiceAnalyzer:
    """Analyzes voice recordings using Praat via parselmouth."""

    # Pitch thresholds for voice register estimation (adjustable)
    # These are rough approximations - actual values vary by individual
    CHEST_VOICE_THRESHOLD = 165  # Hz - below this is likely chest voice
    HEAD_VOICE_THRESHOLD = 260  # Hz - above this is likely head voice

    def __init__(
        self,
        pitch_floor: float = 75.0,  # Minimum expected pitch
        pitch_ceiling: float = 500.0,  # Maximum expected pitch
    ):
        self.pitch_floor = pitch_floor
        self.pitch_ceiling = pitch_ceiling

    def analyze(self, audio_path: str | Path) -> VoiceAnalysis:
        """
        Perform comprehensive voice analysis on an audio file.

        Args:
            audio_path: Path to the audio file

        Returns:
            VoiceAnalysis object with all metrics
        """
        audio_path = Path(audio_path)

        # Load sound
        sound = parselmouth.Sound(str(audio_path))
        duration = sound.get_total_duration()

        # Extract pitch
        pitch = sound.to_pitch(
            time_step=0.01,
            pitch_floor=self.pitch_floor,
            pitch_ceiling=self.pitch_ceiling,
        )

        # Get pitch values (excluding unvoiced frames)
        pitch_values = pitch.selected_array["frequency"]
        voiced_pitch = pitch_values[pitch_values > 0]

        if len(voiced_pitch) == 0:
            # No voiced segments detected
            return self._create_empty_analysis(audio_path.name, duration)

        # Calculate pitch statistics
        pitch_mean = float(np.mean(voiced_pitch))
        pitch_min = float(np.min(voiced_pitch))
        pitch_max = float(np.max(voiced_pitch))
        pitch_std = float(np.std(voiced_pitch))
        pitch_range = pitch_max - pitch_min

        # Pitch variability as coefficient of variation
        pitch_variability = (pitch_std / pitch_mean) * 100 if pitch_mean > 0 else 0

        # Voice register estimation
        chest_count = np.sum(voiced_pitch < self.CHEST_VOICE_THRESHOLD)
        head_count = np.sum(voiced_pitch > self.HEAD_VOICE_THRESHOLD)
        mixed_count = len(voiced_pitch) - chest_count - head_count

        total_voiced = len(voiced_pitch)
        chest_percent = (chest_count / total_voiced) * 100
        head_percent = (head_count / total_voiced) * 100
        mixed_percent = (mixed_count / total_voiced) * 100

        # Voiced fraction
        voiced_fraction = len(voiced_pitch) / len(pitch_values) if len(pitch_values) > 0 else 0

        # Extract intensity
        intensity = sound.to_intensity(minimum_pitch=self.pitch_floor)
        intensity_values = intensity.values[0]
        intensity_values = intensity_values[~np.isnan(intensity_values)]

        if len(intensity_values) > 0:
            intensity_mean = float(np.mean(intensity_values))
            intensity_std = float(np.std(intensity_values))
            intensity_min = float(np.min(intensity_values))
            intensity_max = float(np.max(intensity_values))
        else:
            intensity_mean = intensity_std = intensity_min = intensity_max = 0.0

        # Speaking rate estimate (count voiced segments transitions)
        speaking_rate = self._estimate_speaking_rate(pitch_values, duration)

        # Expressiveness score (0-100)
        expressiveness = self._calculate_expressiveness(
            pitch_range, pitch_variability, voiced_fraction
        )

        return VoiceAnalysis(
            filename=audio_path.name,
            duration_seconds=round(duration, 2),
            pitch_mean=round(pitch_mean, 1),
            pitch_min=round(pitch_min, 1),
            pitch_max=round(pitch_max, 1),
            pitch_std=round(pitch_std, 1),
            pitch_range=round(pitch_range, 1),
            pitch_variability_percent=round(pitch_variability, 1),
            chest_voice_percent=round(chest_percent, 1),
            head_voice_percent=round(head_percent, 1),
            mixed_voice_percent=round(mixed_percent, 1),
            intensity_mean=round(intensity_mean, 1),
            intensity_std=round(intensity_std, 1),
            intensity_min=round(intensity_min, 1),
            intensity_max=round(intensity_max, 1),
            voiced_fraction=round(voiced_fraction, 3),
            speaking_rate_estimate=round(speaking_rate, 1),
            expressiveness_score=round(expressiveness, 1),
        )

    def _estimate_speaking_rate(self, pitch_values: np.ndarray, duration: float) -> float:
        """
        Estimate speaking rate by counting voiced segment transitions.
        This is a rough proxy for syllable rate.
        """
        if len(pitch_values) == 0 or duration == 0:
            return 0.0

        # Count transitions from unvoiced to voiced (approximating syllable onsets)
        voiced_mask = pitch_values > 0
        transitions = np.diff(voiced_mask.astype(int))
        onset_count = np.sum(transitions == 1)

        # Return onsets per second (rough syllable rate)
        return onset_count / duration

    def _calculate_expressiveness(
        self,
        pitch_range: float,
        pitch_variability: float,
        voiced_fraction: float,
    ) -> float:
        """
        Calculate an expressiveness score based on pitch characteristics.
        Score from 0-100, where higher is more expressive/varied.
        """
        # Normalize pitch range (typical range: 50-200 Hz for conversational speech)
        range_score = min(100, (pitch_range / 150) * 50)

        # Normalize variability (typical: 10-30%)
        variability_score = min(100, (pitch_variability / 25) * 30)

        # Voiced fraction contribution (being voiced ~60-80% is typical)
        voice_score = min(100, voiced_fraction * 20)

        # Weighted combination
        expressiveness = range_score + variability_score + voice_score

        return min(100, max(0, expressiveness))

    def _create_empty_analysis(self, filename: str, duration: float) -> VoiceAnalysis:
        """Create an analysis result when no voice is detected."""
        return VoiceAnalysis(
            filename=filename,
            duration_seconds=round(duration, 2),
            pitch_mean=0,
            pitch_min=0,
            pitch_max=0,
            pitch_std=0,
            pitch_range=0,
            pitch_variability_percent=0,
            chest_voice_percent=0,
            head_voice_percent=0,
            mixed_voice_percent=0,
            intensity_mean=0,
            intensity_std=0,
            intensity_min=0,
            intensity_max=0,
            voiced_fraction=0,
            speaking_rate_estimate=0,
            expressiveness_score=0,
        )

    def compare(
        self, analysis1: VoiceAnalysis, analysis2: VoiceAnalysis
    ) -> dict:
        """
        Compare two voice analyses and return differences.

        Args:
            analysis1: First (baseline) analysis
            analysis2: Second (comparison) analysis

        Returns:
            Dictionary with differences for each metric
        """
        d1 = analysis1.to_dict()
        d2 = analysis2.to_dict()

        comparison = {}
        skip_fields = {"filename", "duration_seconds"}

        for key in d1:
            if key in skip_fields:
                continue

            val1 = d1[key]
            val2 = d2[key]

            diff = val2 - val1
            if val1 != 0:
                pct_change = ((val2 - val1) / abs(val1)) * 100
            else:
                pct_change = 0 if val2 == 0 else 100

            comparison[key] = {
                "baseline": val1,
                "current": val2,
                "difference": round(diff, 2),
                "percent_change": round(pct_change, 1),
            }

        return comparison
