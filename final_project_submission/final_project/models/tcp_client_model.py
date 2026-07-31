import pickle
import socket
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class TcpDataFormat:
    """Packet format used by the provided TCP server."""

    channels: int = 32
    samples_per_packet: int = 18
    dtype: type = np.float64

    @property
    def packet_shape(self) -> tuple[int, int]:
        return self.channels, self.samples_per_packet

    @property
    def packet_size_bytes(self) -> int:
        return int(np.prod(self.packet_shape) * np.dtype(self.dtype).itemsize)


class TcpClientModel:
    """
    Model layer for TCP communication and signal storage.

    The class has no Qt or plotting code. It receives raw TCP bytes, reconstructs
    complete packets, keeps a short live buffer, and stores all received samples
    for offline plotting.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 12345,
        sampling_rate: float = 2000.0,
        window_seconds: float = 10.0,
        data_format: TcpDataFormat | None = None,
    ):
        self.host = host
        self.port = port
        self.sampling_rate = float(sampling_rate)
        self.window_seconds = float(window_seconds)
        self.data_format = data_format or TcpDataFormat()

        self.socket: socket.socket | None = None
        self.is_connected = False

        self.byte_buffer = bytearray()
        self.data_buffer = self._empty_signal()
        self.recorded_data = self._empty_signal()
        self.total_samples_received = 0

    @property
    def channels(self) -> int:
        return self.data_format.channels

    @property
    def samples_per_packet(self) -> int:
        return self.data_format.samples_per_packet

    @property
    def dtype(self) -> type:
        return self.data_format.dtype

    @property
    def packet_size_bytes(self) -> int:
        return self.data_format.packet_size_bytes

    @property
    def window_size_samples(self) -> int:
        return max(1, int(self.sampling_rate * self.window_seconds))

    def connect(
        self,
        host: str | None = None,
        port: int | None = None,
        timeout_seconds: float = 3.0,
    ) -> None:
        """Open a non-blocking TCP connection."""
        if self.is_connected:
            return

        self.host = host or self.host
        self.port = self.port if port is None else port

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(timeout_seconds)

        try:
            client_socket.connect((self.host, self.port))
            client_socket.setblocking(False)
        except OSError:
            client_socket.close()
            raise

        self.socket = client_socket
        self.is_connected = True
        self.clear_stream_buffers()

    def disconnect(self) -> None:
        """Close the socket while preserving recorded samples."""
        self.is_connected = False
        if self.socket is None:
            return

        try:
            self.socket.close()
        finally:
            self.socket = None

    def clear_stream_buffers(self) -> None:
        """Clear live TCP buffers before starting a new stream."""
        self.byte_buffer.clear()
        self.data_buffer = self._empty_signal()
        self.recorded_data = self._empty_signal()
        self.total_samples_received = 0

    def load_recording_file(self, recording_path: str | Path) -> int:
        """
        Load the course recording file for offline plotting.

        The file stores data as (channels, samples_per_packet, windows). The GUI
        uses (channels, samples), so the windows are flattened in streaming order.
        """
        path = Path(recording_path)
        with path.open("rb") as file:
            recording = pickle.load(file)

        biosignal = self._extract_biosignal(recording)
        flattened = biosignal.transpose(0, 2, 1).reshape(self.channels, -1)
        flattened = flattened.astype(self.dtype, copy=False)

        device_info = recording.get("device_information", {})
        sampling_frequency = device_info.get("sampling_frequency")
        if sampling_frequency:
            self.sampling_rate = float(sampling_frequency)

        self.byte_buffer.clear()
        self.recorded_data = flattened.copy()
        self.data_buffer = flattened[:, -self.window_size_samples :].copy()
        self.total_samples_received = flattened.shape[1]

        return flattened.shape[1]

    def receive_available_data(self) -> int:
        """Read currently available TCP bytes and return new sample count."""
        if not self.is_connected or self.socket is None:
            return 0

        while True:
            try:
                new_bytes = self.socket.recv(8192)
            except BlockingIOError:
                break
            except OSError:
                self.disconnect()
                break

            if not new_bytes:
                self.disconnect()
                break

            self.byte_buffer.extend(new_bytes)

        return self._extract_complete_packets()

    def has_live_data(self) -> bool:
        return self.data_buffer.shape[1] > 0

    def has_recording(self) -> bool:
        return self.recorded_data.shape[1] > 0

    def get_live_channel(self, channel_index: int) -> tuple[np.ndarray, np.ndarray]:
        self._validate_channel_index(channel_index)
        return self._time_axis_for(self.data_buffer), self.data_buffer[channel_index].copy()

    def get_recorded_channel(
        self, channel_index: int
    ) -> tuple[np.ndarray, np.ndarray]:
        self._validate_channel_index(channel_index)
        return (
            self._time_axis_for(self.recorded_data),
            self.recorded_data[channel_index].copy(),
        )

    def get_live_all_channels(self) -> tuple[np.ndarray, np.ndarray]:
        return self._time_axis_for(self.data_buffer), self.data_buffer.copy()

    def get_recorded_all_channels(self) -> tuple[np.ndarray, np.ndarray]:
        return self._time_axis_for(self.recorded_data), self.recorded_data.copy()

    def _extract_complete_packets(self) -> int:
        packets = []
        while len(self.byte_buffer) >= self.packet_size_bytes:
            packet_bytes = self.byte_buffer[: self.packet_size_bytes]
            del self.byte_buffer[: self.packet_size_bytes]

            packet = np.frombuffer(packet_bytes, dtype=self.dtype).reshape(
                self.data_format.packet_shape
            )
            packets.append(packet)

        if not packets:
            return 0

        new_data = np.concatenate(packets, axis=1)
        self._append_samples(new_data)
        return new_data.shape[1]

    def _append_samples(self, new_data: np.ndarray) -> None:
        if new_data.shape[0] != self.channels:
            raise ValueError(f"Expected {self.channels} channels, got {new_data.shape[0]}.")

        self.recorded_data = np.concatenate((self.recorded_data, new_data), axis=1)
        self.data_buffer = np.concatenate((self.data_buffer, new_data), axis=1)
        self.total_samples_received += new_data.shape[1]

        if self.data_buffer.shape[1] > self.window_size_samples:
            self.data_buffer = self.data_buffer[:, -self.window_size_samples :]

    def _extract_biosignal(self, recording: object) -> np.ndarray:
        if not isinstance(recording, dict) or "biosignal" not in recording:
            raise ValueError("recording.pkl must contain a 'biosignal' array.")

        biosignal = np.asarray(recording["biosignal"])
        expected = "(channels, samples_per_packet, windows)"

        if biosignal.ndim != 3:
            raise ValueError(f"Expected biosignal shape {expected}.")
        if biosignal.shape[0] < self.channels:
            raise ValueError(f"Expected at least {self.channels} channels.")
        if biosignal.shape[1] != self.samples_per_packet:
            raise ValueError(f"Expected {self.samples_per_packet} samples per packet.")

        return biosignal[: self.channels]

    def _time_axis_for(self, data: np.ndarray) -> np.ndarray:
        return np.arange(data.shape[1], dtype=float) / self.sampling_rate

    def _empty_signal(self) -> np.ndarray:
        return np.empty((self.channels, 0), dtype=self.dtype)

    def _validate_channel_index(self, channel_index: int) -> None:
        if not 0 <= channel_index < self.channels:
            raise ValueError(f"Channel must be between 1 and {self.channels}.")
