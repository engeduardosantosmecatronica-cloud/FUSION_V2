from __future__ import annotations

from typing import Any

import pyqtgraph as pg
from PySide6.QtCore import QPointF


class TimeAxis(pg.AxisItem):
    def __init__(self, orientation: str = "bottom") -> None:
        super().__init__(orientation=orientation)
        self.labels: list[str] = []

    def set_labels(self, labels: list[str]) -> None:
        self.labels = labels

    def tickStrings(self, values: list[float], scale: float, spacing: float) -> list[str]:
        out: list[str] = []
        for value in values:
            index = int(round(value))
            if 0 <= index < len(self.labels):
                label = self.labels[index]
                out.append(label[5:16] if len(label) >= 16 else label)
            else:
                out.append("")
        return out


class PriceAxis(pg.AxisItem):
    def mouseDragEvent(self, event: Any) -> None:
        linked_view = self.linkedView()
        if linked_view is None or self.orientation not in {"left", "right"}:
            event.ignore()
            return

        if event.isStart():
            event.accept()
            return

        dy = event.pos().y() - event.lastPos().y()
        if dy == 0:
            event.accept()
            return

        factor = max(0.70, min(1.30, 1.0 + dy * 0.012))
        x_range, y_range = linked_view.viewRange()
        center = QPointF((x_range[0] + x_range[1]) / 2, (y_range[0] + y_range[1]) / 2)
        linked_view.scaleBy((1.0, factor), center=center)
        event.accept()
