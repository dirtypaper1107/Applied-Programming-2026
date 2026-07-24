import socket
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TcpDataFormat:
    """Data contract shared by the TCP server and client."""

    channels: int = 32
    samples_per_packet: int = 18
    dtype: type = np.float64

    @property
    def packet_size_bytes(self) -> int:
        return (
            self.channels
            * self.samples_per_packet
            * np.dtype(self.dtype).itemsize
        )


class TcpClientModel:
    """
    TCP client model for receiving streamed EMG/signal data.

    Responsibilities:
    - connect to the TCP server
    - receive raw bytes without blocking the GUI
    - reconstruct complete NumPy packets with shape (32, 18)
    - keep a rolling live buffer and a full recording buffer

    This class intentionally contains no Qt, VisPy, or Matplotlib code.
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
        self.sampling_rate = sampling_rate
        self.window_seconds = window_seconds
        self.data_format = data_format or TcpDataFormat()

        self.socket: socket.socket | None = None
        self.is_connected = False

        self.byte_buffer = bytearray()
        self.data_buffer = np.empty((self.channels, 0), dtype=self.dtype)
        self.recorded_data = np.empty((self.channels, 0), dtype=self.dtype)
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
        return int(self.sampling_rate * self.window_seconds)

    def connect(
        self,
        host: str | None = None,
        port: int | None = None,
        timeout_seconds: float = 3.0,
    ) -> None:
        """Connect to the TCP server and switch the socket to non-blocking mode."""
        if self.is_connected:
            return

        if host is not None:
            self.host = host
        if port is not None:
            self.port = port

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

    def disconnect(self) -> None:
        """Close the TCP connection and keep already received data for offline use."""
        self.is_connected = False

        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def clear(self) -> None:
        """Clear all buffered and recorded data."""
        self.byte_buffer.clear()
        self.data_buffer = np.empty((self.channels, 0), dtype=self.dtype)
        self.recorded_data = np.empty((self.channels, 0), dtype=self.dtype)
        self.total_samples_received = 0

    def receive_available_data(self) -> int:
        """
        Receive all bytes currently available and return the number of new samples.

        TCP is a byte stream, so recv() may return partial packets, exactly one
        packet, or multiple packets. Complete packets are extracted only after
        enough bytes have accumulated.
        """
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

        return self._extract_packets_from_byte_buffer()

    def _extract_packets_from_byte_buffer(self) -> int:
        packets = []

        while len(self.byte_buffer) >= self.packet_size_bytes:
            packet_bytes = self.byte_buffer[: self.packet_size_bytes]
            del self.byte_buffer[: self.packet_size_bytes]

            packet = np.frombuffer(packet_bytes, dtype=self.dtype)
            packet = packet.reshape(self.channels, self.samples_per_packet)
            packets.append(packet)

        if not packets:
            return 0

        new_data = np.concatenate(packets, axis=1)
        self._append_samples(new_data)

        return new_data.shape[1]

    def _append_samples(self, new_data: np.ndarray) -> None:
        if new_data.shape[0] != self.channels:
            raise ValueError(
                f"Expected {self.channels} channels, got {new_data.shape[0]}."
            )

        self.recorded_data = np.concatenate((self.recorded_data, new_data), axis=1)
        self.data_buffer = np.concatenate((self.data_buffer, new_data), axis=1)
        self.total_samples_received += new_data.shape[1]

        if self.data_buffer.shape[1] > self.window_size_samples:
            self.data_buffer = self.data_buffer[:, -self.window_size_samples :]

    def has_live_data(self) -> bool:
        return self.data_buffer.shape[1] > 0

    def has_recording(self) -> bool:
        return self.recorded_data.shape[1] > 0

    def get_live_channel(self, channel_index: int) -> tuple[np.ndarray, np.ndarray]:
        """Return x/y arrays for one channel from the rolling live buffer."""
        self._validate_channel_index(channel_index)
        return self._make_time_axis(self.data_buffer), self.data_buffer[channel_index]

    def get_recorded_channel(
        self, channel_index: int
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return x/y arrays for one channel from the full recording."""
        self._validate_channel_index(channel_index)
        return (
            self._make_time_axis(self.recorded_data),
            self.recorded_data[channel_index],
        )

    def get_live_all_channels(self) -> tuple[np.ndarray, np.ndarray]:
        """Return x and all channel rows from the rolling live buffer."""
        return self._make_time_axis(self.data_buffer), self.data_buffer.copy()

    def get_recorded_all_channels(self) -> tuple[np.ndarray, np.ndarray]:
        """Return x and all channel rows from the full recording."""
        return self._make_time_axis(self.recorded_data), self.recorded_data.copy()

    def get_signal_time_seconds(self) -> float:
        return self.total_samples_received / self.sampling_rate

    def _make_time_axis(self, data: np.ndarray) -> np.ndarray:
        return np.arange(data.shape[1]) / self.sampling_rate

    def _validate_channel_index(self, channel_index: int) -> None:
        if not 0 <= channel_index < self.channels:
            raise ValueError(
                f"Channel index must be between 0 and {self.channels - 1}."
            )
