from PySide6.QtCore import QObject, QTimer, Signal

from final_project.models import TcpClientModel
from final_project.models.signal_processing import SignalProcessor


class MainViewModel(QObject):
    """
    ViewModel for the TCP signal visualization application.

    The View calls this class for user actions. This class owns the TCP model,
    periodically pulls new data, applies the selected signal mode, and emits
    plot/status updates back to the View.
    """

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

        self.timer = QTimer()
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
        """Connect to the TCP server using a port string from the GUI."""
        try:
            port = int(port_text)
            if not 0 < port < 65536:
                raise ValueError
        except ValueError:
            self.status_updated.emit("Invalid TCP port.")
            return

        try:
            self.tcp_model.clear()
            self.tcp_model.connect(host=host, port=port)
        except OSError as error:
            self.status_updated.emit(f"Could not connect: {error}")
            self.connection_changed.emit(False)
            return

        self.timer.start(self.update_interval_ms)
        self.status_updated.emit(f"Connected to {host}:{port}.")
        self.connection_changed.emit(True)

    def disconnect_from_server(self) -> None:
        """Disconnect from the server and stop live updates."""
        self.timer.stop()
        self.tcp_model.disconnect()
        self.status_updated.emit("Disconnected.")
        self.connection_changed.emit(False)

    def set_selected_channel(self, channel_number: int) -> None:
        """Set the active channel using 1-based channel numbers from the GUI."""
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
        """Receive new TCP data and emit a live plot update if data is available."""
        was_connected = self.tcp_model.is_connected
        self.tcp_model.receive_available_data()

        if was_connected and not self.tcp_model.is_connected:
            self.timer.stop()
            self.status_updated.emit("Connection closed by server.")
            self.connection_changed.emit(False)

        if self.tcp_model.has_live_data():
            self.emit_live_plot()

    def emit_live_plot(self) -> None:
        if self.plot_all_channels:
            x, data = self.tcp_model.get_live_all_channels()
            y = self.processor.process(data, self.signal_mode)
        else:
            x, data = self.tcp_model.get_live_channel(self.selected_channel)
            y = self.processor.process(data.reshape(1, -1), self.signal_mode)[0]

        self.live_plot_updated.emit(x, y)

    def emit_offline_plot(self) -> None:
        if not self.tcp_model.has_recording():
            self.status_updated.emit("No recorded data available.")
            return

        if self.plot_all_channels:
            x, data = self.tcp_model.get_recorded_all_channels()
            y = self.processor.process(data, self.signal_mode)
        else:
            x, data = self.tcp_model.get_recorded_channel(self.selected_channel)
            y = self.processor.process(data.reshape(1, -1), self.signal_mode)[0]

        self.offline_plot_updated.emit(x, y)

    def refresh_current_plot(self) -> None:
        """Refresh whichever data source is available after a setting changed."""
        if self.tcp_model.has_live_data() and self.tcp_model.is_connected:
            self.emit_live_plot()
        elif self.tcp_model.has_recording():
            self.emit_offline_plot()
