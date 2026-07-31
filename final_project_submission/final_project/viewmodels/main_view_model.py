from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from final_project.models import SignalProcessor, TcpClientModel


class MainViewModel(QObject):
    """Application state and user-action logic for the main window."""

    live_plot_updated = Signal(object, object)
    offline_plot_updated = Signal(object, object)
    status_updated = Signal(str)
    connection_changed = Signal(bool)
    channel_changed = Signal(int)
    signal_mode_changed = Signal(str)
    plot_all_channels_changed = Signal(bool)

    def __init__(
        self,
        host: str = "localhost",
        port: int = 12345,
        sampling_rate: float = 2000.0,
        window_seconds: float = 10.0,
        update_interval_ms: int = 20,
    ):
        super().__init__()

        self.tcp_model = TcpClientModel(
            host=host,
            port=port,
            sampling_rate=sampling_rate,
            window_seconds=window_seconds,
        )
        self.processor = SignalProcessor(sampling_rate=sampling_rate)

        self.selected_channel = 0
        self.signal_mode = SignalProcessor.ORIGINAL
        self.plot_all_channels = False
        self.update_interval_ms = update_interval_ms

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_live_data)

    @property
    def is_connected(self) -> bool:
        return self.tcp_model.is_connected

    @property
    def available_modes(self) -> tuple[str, ...]:
        return SignalProcessor.MODES

    @property
    def channel_count(self) -> int:
        return self.tcp_model.channels

    def connect_to_server(self, port_text: str, host: str = "localhost") -> None:
        port = self._parse_port(port_text)
        if port is None:
            self.status_updated.emit("Invalid TCP port. Use a number from 1 to 65535.")
            return

        try:
            self.tcp_model.connect(host=host, port=port)
        except OSError as error:
            self.status_updated.emit(f"Could not connect to {host}:{port}: {error}")
            self.connection_changed.emit(False)
            return

        self.processor.sampling_rate = self.tcp_model.sampling_rate
        self.timer.start(self.update_interval_ms)
        self.status_updated.emit(f"Connected to {host}:{port}.")
        self.connection_changed.emit(True)

    def disconnect_from_server(self) -> None:
        self.timer.stop()
        self.tcp_model.disconnect()
        self.status_updated.emit("Disconnected.")
        self.connection_changed.emit(False)

    def load_default_recording(self) -> bool:
        recording_path = self._find_default_recording_path()
        if recording_path is None:
            self.status_updated.emit("No recording.pkl file found.")
            return False

        try:
            sample_count = self.tcp_model.load_recording_file(recording_path)
        except (OSError, ValueError) as error:
            self.status_updated.emit(f"Could not load recording.pkl: {error}")
            return False

        self.processor.sampling_rate = self.tcp_model.sampling_rate
        duration_seconds = sample_count / self.tcp_model.sampling_rate
        self.status_updated.emit(
            f"Loaded recording.pkl: {sample_count} samples, {duration_seconds:.1f} s."
        )
        self.emit_offline_plot()
        return True

    def set_selected_channel(self, channel_number: int) -> None:
        channel_index = channel_number - 1
        if not 0 <= channel_index < self.channel_count:
            self.status_updated.emit("Invalid channel.")
            return

        self.selected_channel = channel_index
        self.channel_changed.emit(channel_number)
        self.refresh_current_plot()

    def set_signal_mode(self, mode: str) -> None:
        if mode not in SignalProcessor.MODES:
            self.status_updated.emit("Invalid signal mode.")
            return

        self.signal_mode = mode
        self.signal_mode_changed.emit(mode)
        self.refresh_current_plot()

    def set_plot_all_channels(self, enabled: bool) -> None:
        self.plot_all_channels = enabled
        self.plot_all_channels_changed.emit(enabled)
        self.refresh_current_plot()

    def update_live_data(self) -> None:
        was_connected = self.tcp_model.is_connected
        new_samples = self.tcp_model.receive_available_data()

        if was_connected and not self.tcp_model.is_connected:
            self.timer.stop()
            self.status_updated.emit("Connection closed by server.")
            self.connection_changed.emit(False)

        if new_samples > 0 or self.tcp_model.has_live_data():
            self.emit_live_plot()

    def emit_live_plot(self) -> None:
        if not self.tcp_model.has_live_data():
            return

        x, y = self._current_data(live=True)
        self.live_plot_updated.emit(x, y)

    def emit_offline_plot(self) -> None:
        if not self.tcp_model.has_recording():
            self.status_updated.emit("No recorded data available.")
            return

        x, y = self._current_data(live=False)
        self.offline_plot_updated.emit(x, y)

    def refresh_current_plot(self) -> None:
        if self.tcp_model.is_connected and self.tcp_model.has_live_data():
            self.emit_live_plot()
        if self.tcp_model.has_recording():
            self.emit_offline_plot()

    def _current_data(self, live: bool) -> tuple[object, object]:
        if self.plot_all_channels:
            x, data = (
                self.tcp_model.get_live_all_channels()
                if live
                else self.tcp_model.get_recorded_all_channels()
            )
            return x, self.processor.process(data, self.signal_mode)

        x, channel = (
            self.tcp_model.get_live_channel(self.selected_channel)
            if live
            else self.tcp_model.get_recorded_channel(self.selected_channel)
        )
        processed = self.processor.process(channel, self.signal_mode)[0]
        return x, processed

    def _parse_port(self, port_text: str) -> int | None:
        try:
            port = int(port_text)
        except ValueError:
            return None

        if 1 <= port <= 65535:
            return port
        return None

    def _find_default_recording_path(self) -> Path | None:
        candidates = (
            Path.cwd() / "recording.pkl",
            Path(__file__).resolve().parents[2] / "recording.pkl",
        )

        for path in candidates:
            if path.exists():
                return path
        return None
