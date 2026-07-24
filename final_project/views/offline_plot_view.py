import numpy as np
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg,
    NavigationToolbar2QT,
)
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget


class OfflinePlotView(QWidget):
    """Matplotlib widget for offline inspection after data was recorded."""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.figure = Figure(figsize=(8, 5), constrained_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.axis = self.figure.add_subplot(111)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        self._draw_empty_plot()

    def update_plot(self, x, y) -> None:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)

        self.axis.clear()

        if x.size == 0 or y.size == 0:
            self._draw_empty_plot()
            return

        if y.ndim == 1:
            self.axis.plot(x, y, linewidth=1.0)
            self.axis.set_ylabel("Amplitude")
        else:
            offset = self._channel_offset(y)
            for channel_index, channel in enumerate(y):
                self.axis.plot(
                    x,
                    channel + channel_index * offset,
                    linewidth=0.8,
                )
            self.axis.set_ylabel("Channels with offset")

        self.axis.set_xlabel("Time (s)")
        self.axis.grid(True, alpha=0.25)
        self.canvas.draw_idle()

    def _draw_empty_plot(self) -> None:
        self.axis.clear()
        self.axis.set_xlabel("Time (s)")
        self.axis.set_ylabel("Amplitude")
        self.axis.grid(True, alpha=0.25)
        self.canvas.draw_idle()

    def _channel_offset(self, y: np.ndarray) -> float:
        ranges = np.ptp(y, axis=1)
        typical_range = float(np.nanmedian(ranges))
        return max(typical_range * 1.4, 0.1)
