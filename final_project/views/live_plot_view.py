import numpy as np
from PySide6.QtWidgets import QVBoxLayout, QWidget
from vispy import scene


class LivePlotView(QWidget):
    """VisPy widget for live single-channel or all-channel plotting."""

    def __init__(self, max_channels: int = 32):
        super().__init__()

        self.max_channels = max_channels
        self.lines = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.canvas = scene.SceneCanvas(
            keys="interactive",
            show=False,
            bgcolor="white",
            size=(1000, 600),
            dpi=96,
        )

        grid = self.canvas.central_widget.add_grid(margin=12)

        self.y_axis = scene.AxisWidget(
            orientation="left",
            axis_label="Amplitude",
            axis_font_size=10,
            axis_label_margin=35,
            tick_label_margin=6,
        )
        self.x_axis = scene.AxisWidget(
            orientation="bottom",
            axis_label="Time (s)",
            axis_font_size=10,
            axis_label_margin=30,
            tick_label_margin=6,
        )

        self.y_axis.width_max = 72
        self.x_axis.height_max = 52

        grid.add_widget(self.y_axis, row=0, col=0)
        self.view = grid.add_view(row=0, col=1)
        self.view.camera = "panzoom"
        grid.add_widget(self.x_axis, row=1, col=1)

        self.x_axis.link_view(self.view)
        self.y_axis.link_view(self.view)

        self._ensure_line_count(1)
        layout.addWidget(self.canvas.native)

    def update_plot(self, x, y) -> None:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)

        if x.size == 0 or y.size == 0:
            return

        if y.ndim == 1:
            self._plot_single_channel(x, y)
        else:
            self._plot_all_channels(x, y)

    def _plot_single_channel(self, x: np.ndarray, y: np.ndarray) -> None:
        self._ensure_line_count(1)
        self._hide_lines_after(1)

        self.lines[0].set_data(pos=np.column_stack((x, y)))
        self.lines[0].visible = True

        y_min, y_max = float(np.min(y)), float(np.max(y))
        y_pad = max(0.1, 0.1 * (y_max - y_min + 1e-9))
        self.view.camera.set_range(
            x=(float(x.min()), float(x.max())),
            y=(y_min - y_pad, y_max + y_pad),
        )

    def _plot_all_channels(self, x: np.ndarray, y: np.ndarray) -> None:
        channel_count = min(y.shape[0], self.max_channels)
        y = y[:channel_count]

        self._ensure_line_count(channel_count)
        self._hide_lines_after(channel_count)

        offset = self._channel_offset(y)
        for channel_index in range(channel_count):
            shifted = y[channel_index] + channel_index * offset
            self.lines[channel_index].set_data(pos=np.column_stack((x, shifted)))
            self.lines[channel_index].visible = True

        shifted_stack = y + np.arange(channel_count).reshape(-1, 1) * offset
        y_min = float(np.min(shifted_stack))
        y_max = float(np.max(shifted_stack))
        y_pad = max(offset, 0.1)
        self.view.camera.set_range(
            x=(float(x.min()), float(x.max())),
            y=(y_min - y_pad, y_max + y_pad),
        )

    def _ensure_line_count(self, count: int) -> None:
        while len(self.lines) < count:
            color = self._line_color(len(self.lines))
            line = scene.Line(
                pos=np.array([[0.0, 0.0], [1.0, 0.0]], dtype=float),
                color=color,
                parent=self.view.scene,
                width=1.6,
            )
            self.lines.append(line)

    def _hide_lines_after(self, count: int) -> None:
        for line in self.lines[count:]:
            line.visible = False

    def _channel_offset(self, y: np.ndarray) -> float:
        ranges = np.ptp(y, axis=1)
        typical_range = float(np.nanmedian(ranges))
        return max(typical_range * 1.4, 0.1)

    def _line_color(self, index: int) -> tuple[float, float, float, float]:
        palette = (
            (0.10, 0.32, 0.68, 1.0),
            (0.76, 0.18, 0.14, 1.0),
            (0.14, 0.50, 0.28, 1.0),
            (0.83, 0.55, 0.12, 1.0),
            (0.39, 0.30, 0.63, 1.0),
            (0.16, 0.55, 0.60, 1.0),
        )
        return palette[index % len(palette)]
