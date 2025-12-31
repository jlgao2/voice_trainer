"""Audio recording module for voice training."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf


class Recorder:
    """Handles audio recording from microphone."""

    def __init__(
        self,
        sample_rate: int = 44100,
        channels: int = 1,
        recordings_dir: str = "recordings",
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recordings_dir = Path(recordings_dir)
        self.recordings_dir.mkdir(exist_ok=True)

    def record(
        self,
        duration: float = 10.0,
        filename: Optional[str] = None,
    ) -> Path:
        """
        Record audio from microphone.

        Args:
            duration: Recording duration in seconds
            filename: Optional custom filename, otherwise timestamp-based

        Returns:
            Path to the saved recording
        """
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.wav"

        filepath = self.recordings_dir / filename

        # Record audio
        audio_data = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.float32,
        )
        sd.wait()  # Wait for recording to complete

        # Save to file
        sf.write(filepath, audio_data, self.sample_rate)

        return filepath

    def get_countdown_callback(self, console) -> callable:
        """Create a callback for countdown display during recording."""
        from rich.live import Live
        from rich.text import Text

        start_time = None

        def callback(indata, frames, time_info, status):
            nonlocal start_time
            if start_time is None:
                import time
                start_time = time.time()

        return callback

    @staticmethod
    def list_devices() -> list:
        """List available audio input devices."""
        devices = sd.query_devices()
        input_devices = []
        for i, device in enumerate(devices):
            if device["max_input_channels"] > 0:
                input_devices.append({
                    "id": i,
                    "name": device["name"],
                    "channels": device["max_input_channels"],
                    "sample_rate": device["default_samplerate"],
                })
        return input_devices

    @staticmethod
    def get_default_device() -> dict:
        """Get the default input device info."""
        device_id = sd.default.device[0]
        if device_id is None:
            device_id = sd.query_devices(kind="input")["index"]
        return sd.query_devices(device_id)
