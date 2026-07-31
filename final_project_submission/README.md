# TCP Signal Visualization Application

## Overview

This final project is a PySide6 desktop application for live visualization and offline inspection of streamed EMG-like signal data.

The application connects to a local TCP server, receives raw signal packets from `recording.pkl`, reconstructs the TCP byte stream into NumPy arrays, and displays the signal in real time. After disconnecting, the recorded data can also be inspected in an offline Matplotlib plot.

## Submitted Files

```text
final_project_submission/
├── final_project/        # Main PySide6 application
├── TCP_Server/           # Local TCP data server
├── recording.pkl         # Signal data used by the TCP server
├── pyproject.toml        # Project dependencies
├── uv.lock               # Locked dependency versions
└── README.md             # This file
```

## Requirements

The project uses Python and the following main libraries:

- `PySide6` for the GUI
- `vispy` for live plotting
- `matplotlib` for offline plotting
- `numpy` for signal arrays and buffering
- `scipy` for signal processing

Dependencies can be installed with `uv`:

```bash
uv sync
```

If `uv` is not available, the final project dependencies can also be installed with:

```bash
python -m pip install -r final_project/requirements.txt
```

## How to Run

Run the commands from inside the `final_project_submission` folder.

First, start the TCP server in one terminal:

```bash
.venv/bin/python TCP_Server/main.py
```

The server loads `recording.pkl` and starts listening on:

```text
localhost:12345
```

Then start the GUI application in a second terminal:

```bash
.venv/bin/python -m final_project.main
```

In the GUI:

1. Enter `localhost` as the host.
2. Enter `12345` as the port.
3. Click `Connect`.
4. Use the channel selector to inspect channels 1 to 32.
5. Use the mode selector to switch between original, filtered, and RMS signals.
6. Click `Plot All Channels` to show all channels together.
7. Click `Disconnect` to stop live streaming.
8. Click `Show Offline Plot` to inspect the recorded data after streaming.

## TCP Data Format

The TCP server sends packets with this format:

```text
32 channels x 18 samples
float64
```

One complete packet contains:

```text
32 x 18 x 8 = 4608 bytes
```

Because TCP is a byte stream, the client stores incoming bytes in a buffer and only reconstructs a packet when at least `4608` bytes are available.

## Features

- TCP connection to the local signal server
- Host and port input fields
- Connect and disconnect controls
- Live signal plotting with VisPy
- Offline signal inspection with Matplotlib
- Channel selection from channel 1 to channel 32
- Single-channel and all-channel display modes
- Original, filtered, and RMS signal modes
- Error handling for invalid ports, failed connections, lost connections, invalid channels, and missing offline data

## Architecture

The application follows an MVVM-style structure:

- `models/` handles TCP communication, buffering, packet reconstruction, and signal processing.
- `viewmodels/` manages application state and connects GUI actions to the model layer.
- `views/` contains the PySide6 widgets and plotting views.

Important files:

```text
final_project/main.py
final_project/models/tcp_client_model.py
final_project/models/signal_processing.py
final_project/viewmodels/main_view_model.py
final_project/views/main_view.py
final_project/views/live_plot_view.py
final_project/views/offline_plot_view.py
TCP_Server/main.py
```

## Team Members and Responsibilities

| Team Member | Responsibility |
|---|---|
| Zihan Zhang | TCP client model, byte buffering, and packet reconstruction |
| Ziyv Chen | PySide6 GUI views, VisPy live plot, and Matplotlib offline plot |
| Tianze Niu | ViewModel integration, signal processing, documentation, and testing |

## Testing

The project was tested with the included TCP server and `recording.pkl`.

Verified behavior:

- TCP server loads the signal data successfully.
- Server sends packets with shape `(32, 18)`.
- Each TCP packet contains `4608` bytes.
- Client reconstructs streamed bytes into channel/sample arrays.
- Live plot updates while connected.
- Recorded data remains available after disconnecting.
- Offline plot displays recorded data.
- Original, filtered, and RMS modes run without changing the expected channel/sample structure.
