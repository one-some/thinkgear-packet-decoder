from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

if TYPE_CHECKING:
    from main import ASICEEGPower

eeg_wave_buffer = {}


def update_eeg_data(data: ASICEEGPower):
    for key, val in data.waves.items():
        if key not in eeg_wave_buffer:
            eeg_wave_buffer[key] = []

        eeg_wave_buffer[key].append(val / (0xFFFFFF * 0.5))
        if len(eeg_wave_buffer[key]) > 100:
            eeg_wave_buffer[key].pop(0)
        # print(len(eeg_wave_buffer[key]))


special_buf = {}


def set_special(k, v):
    if k not in special_buf:
        special_buf[k] = []
    special_buf[k].append(v)
    if len(special_buf[k]) > 100:
        special_buf[k].pop(0)


TITLE = "MIND READING EEG THINGEY"

app = pg.mkQApp(TITLE)
# mw = QtWidgets.QMainWindow()
# mw.resize(800,800)

win = pg.GraphicsLayoutWidget(show=True, title=TITLE)
win.resize(1000, 600)
win.setWindowTitle(TITLE)

# Enable antialiasing for prettier plots
pg.setConfigOptions(antialias=True)

curves = {}

for name in [
    "attention",
    "meditation",
    "delta",
    "theta",
    "low_alpha",
    "high_alpha",
    "low_beta",
    "high_beta",
    "low_gamma",
    "mid_gamma",
]:
    plot = win.addPlot(title=name)
    if name in ["attention", "meditation"]:
        plot.setYRange(0, 100)
    else:
        plot.setYRange(0, 0.6)

    x_axis = plot.getAxis("bottom")
    x_axis.setStyle(showValues=False)

    curve = plot.plot(pen="y")
    curves[name] = curve

    win.nextRow()


def update():
    if not eeg_wave_buffer:
        return

    for name, curve in curves.items():
        val = eeg_wave_buffer.get(name) or special_buf[name]
        curve.setData(val)


timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(50)


def ui_thread():
    pg.exec()
