import numpy as np
from scipy import signal


class SignalProcessor:
    """Signal processing used by both live and offline plots."""

    ORIGINAL = "original"
    FILTERED = "filtered"
    RMS = "rms"
    MODES = (ORIGINAL, FILTERED, RMS)

    def __init__(
        self,
        sampling_rate: float,
        rms_window_ms: float = 100.0,
        filter_low_hz: float = 20.0,
        filter_high_hz: float = 450.0,
        filter_order: int = 4,
    ):
        self.sampling_rate = float(sampling_rate)
        self.rms_window_ms = float(rms_window_ms)
        self.filter_low_hz = float(filter_low_hz)
        self.filter_high_hz = float(filter_high_hz)
        self.filter_order = int(filter_order)

    def process(self, data: np.ndarray, mode: str) -> np.ndarray:
        """Return processed data with shape (channels, samples)."""
        data = self._as_2d_float(data)

        if mode == self.ORIGINAL:
            return data.copy()
        if mode == self.FILTERED:
            return self.bandpass_filter(data)
        if mode == self.RMS:
            return self.compute_rms(data)

        raise ValueError(f"Unknown signal mode: {mode}")

    def bandpass_filter(self, data: np.ndarray) -> np.ndarray:
        """Apply a Butterworth band-pass filter along the sample axis."""
        data = self._as_2d_float(data)
        if data.shape[1] < 3:
            return data.copy()

        nyquist = self.sampling_rate / 2.0
        if nyquist <= 0:
            return data.copy()

        high_hz = min(self.filter_high_hz, nyquist * 0.95)
        low_hz = min(self.filter_low_hz, high_hz * 0.5)
        if low_hz <= 0 or low_hz >= high_hz:
            return data.copy()

        low = low_hz / nyquist
        high = high_hz / nyquist
        b, a = signal.butter(self.filter_order, [low, high], btype="bandpass")

        pad_length = 3 * max(len(a), len(b))
        if data.shape[1] <= pad_length:
            return signal.lfilter(b, a, data, axis=1)

        return signal.filtfilt(b, a, data, axis=1)

    def compute_rms(self, data: np.ndarray) -> np.ndarray:
        """Compute a moving RMS envelope."""
        data = self._as_2d_float(data)
        if data.shape[1] == 0:
            return data.copy()

        window_size = max(1, int(self.rms_window_ms * self.sampling_rate / 1000.0))
        window_size = min(window_size, data.shape[1])
        kernel = np.ones(window_size, dtype=float) / window_size

        mean_squared = signal.convolve(
            data * data,
            kernel.reshape(1, -1),
            mode="same",
        )
        return np.sqrt(mean_squared)

    def _as_2d_float(self, data: np.ndarray) -> np.ndarray:
        array = np.asarray(data, dtype=float)
        if array.ndim == 1:
            return array.reshape(1, -1)
        if array.ndim != 2:
            raise ValueError("Signal data must be 1D or 2D.")
        return array
