from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from final_project.views.live_plot_view import LivePlotView
from final_project.views.offline_plot_view import OfflinePlotView


class MainView(QMainWindow):
    """Main PySide6 window for the TCP signal visualization app."""

    def __init__(self, view_model):
        super().__init__()

        self.view_model = view_model

        self.setWindowTitle("TCP Signal Visualization Application")
        self.resize(1240, 820)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        root_layout.addWidget(self._build_control_panel())

        self.tabs = QTabWidget()
        self.live_plot = LivePlotView(max_channels=self.view_model.channel_count)
        self.offline_plot = OfflinePlotView()
        self.tabs.addTab(self.live_plot, "Live")
        self.tabs.addTab(self.offline_plot, "Offline")
        root_layout.addWidget(self.tabs, stretch=1)

        self.status_label = QLabel("Disconnected.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        root_layout.addWidget(self.status_label)

        self._connect_signals()
        self._set_connected_state(False)

    def _build_control_panel(self) -> QWidget:
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        connection_form = QFormLayout()
        connection_form.setContentsMargins(0, 0, 0, 0)
        connection_form.setSpacing(6)

        self.host_input = QLineEdit("localhost")
        self.host_input.setMinimumWidth(140)

        self.port_input = QLineEdit("12345")
        self.port_input.setFixedWidth(90)

        connection_form.addRow("Host", self.host_input)
        connection_form.addRow("Port", self.port_input)
        layout.addLayout(connection_form)

        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")
        layout.addWidget(self.connect_button)
        layout.addWidget(self.disconnect_button)

        self.channel_spin = QSpinBox()
        self.channel_spin.setRange(1, self.view_model.channel_count)
        self.channel_spin.setValue(1)
        self.channel_spin.setFixedWidth(72)
        layout.addWidget(QLabel("Channel"))
        layout.addWidget(self.channel_spin)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(self.view_model.available_modes)
        self.mode_combo.setFixedWidth(130)
        layout.addWidget(QLabel("Mode"))
        layout.addWidget(self.mode_combo)

        self.plot_all_button = QPushButton("Plot All Channels")
        self.plot_all_button.setCheckable(True)
        layout.addWidget(self.plot_all_button)

        self.offline_button = QPushButton("Show Offline Plot")
        layout.addWidget(self.offline_button)

        layout.addStretch(1)

        return panel

    def _connect_signals(self) -> None:
        self.connect_button.clicked.connect(self._connect_clicked)
        self.disconnect_button.clicked.connect(
            self.view_model.disconnect_from_server
        )
        self.channel_spin.valueChanged.connect(
            self.view_model.set_selected_channel
        )
        self.mode_combo.currentTextChanged.connect(self.view_model.set_signal_mode)
        self.plot_all_button.toggled.connect(
            self.view_model.set_plot_all_channels
        )
        self.offline_button.clicked.connect(self._show_offline_plot)

        self.view_model.live_plot_updated.connect(self.live_plot.update_plot)
        self.view_model.offline_plot_updated.connect(self.offline_plot.update_plot)
        self.view_model.status_updated.connect(self.status_label.setText)
        self.view_model.connection_changed.connect(self._set_connected_state)
        self.view_model.channel_changed.connect(self._sync_channel_spin)
        self.view_model.signal_mode_changed.connect(self._sync_mode_combo)
        self.view_model.plot_all_channels_changed.connect(
            self.plot_all_button.setChecked
        )

    def _connect_clicked(self) -> None:
        host = self.host_input.text().strip() or "localhost"
        self.view_model.connect_to_server(self.port_input.text(), host)

    def _show_offline_plot(self) -> None:
        self.tabs.setCurrentWidget(self.offline_plot)
        self.view_model.emit_offline_plot()

    def _set_connected_state(self, connected: bool) -> None:
        self.connect_button.setEnabled(not connected)
        self.disconnect_button.setEnabled(connected)
        self.host_input.setEnabled(not connected)
        self.port_input.setEnabled(not connected)

    def _sync_channel_spin(self, channel_number: int) -> None:
        if self.channel_spin.value() != channel_number:
            self.channel_spin.setValue(channel_number)

    def _sync_mode_combo(self, mode: str) -> None:
        if self.mode_combo.currentText() != mode:
            self.mode_combo.setCurrentText(mode)

    def closeEvent(self, event) -> None:
        self.view_model.disconnect_from_server()
        super().closeEvent(event)
