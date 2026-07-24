import numpy as np
from scipy import signal


class SignalProcessor:
    """Signal processing service for original, RMS, and filtered display modes."""

    ORIGINAL = "original"
    RMS = "rms"
    FILTERED = "filtered"
    MODES = (ORIGINAL, RMS, FILTERED)

    def __init__(
        self,
        sampling_rate: float,
        rms_window_ms: float = 100.0,
        filter_low_hz: float = 20.0,
        filter_high_hz: float = 450.0,
        filter_order: int = 4,
    ):
        self.sampling_rate = sampling_rate
        self.rms_window_ms = rms_window_ms
        self.filter_low_hz = filter_low_hz
        self.filter_high_hz = filter_high_hz
        self.filter_order = filter_order

    def process(self, data: np.ndarray, mode: str) -> np.ndarray:
        """Return a processed copy of data with shape (channels, samples)."""
        if mode == self.ORIGINAL:
            return np.asarray(data, dtype=float).copy()
        if mode == self.FILTERED:
            return self.bandpass_filter(data)
        if mode == self.RMS:
            return self.compute_rms(data)

        raise ValueError(f"Unknown signal mode: {mode}")

    def bandpass_filter(self, data: np.ndarray) -> np.ndarray:
        """Apply a Butterworth band-pass filter channel by channel."""
        data = np.asarray(data, dtype=float)

        if data.shape[1] < 3:
            return data.copy()

        nyquist = self.sampling_rate / 2
        high_hz = min(self.filter_high_hz, nyquist * 0.95)

        if self.filter_low_hz <= 0:
            raise ValueError("Filter low cutoff must be greater than 0 Hz.")
        if self.filter_low_hz >= high_hz:
            raise ValueError("Filter low cutoff must be smaller than high cutoff.")

        low = self.filter_low_hz / nyquist
        high = high_hz / nyquist
        b, a = signal.butter(self.filter_order, [low, high], btype="band")

        padlen = 3 * max(len(a), len(b))
        if data.shape[1] <= padlen:
            return signal.lfilter(b, a, data, axis=1)

        return signal.filtfilt(b, a, data, axis=1)

    def compute_rms(self, data: np.ndarray) -> np.ndarray:
        """Compute centered RMS using a moving average window."""
        data = np.asarray(data, dtype=float)
        window_size = max(1, int(self.rms_window_ms / 1000 * self.sampling_rate))
        kernel = np.ones(window_size) / window_size

        squared = data * data
        mean_squared = signal.convolve(
            squared,
            kernel.reshape(1, -1),
            mode="same",
        )

        return np.sqrt(mean_squared)
