# TCP Signal Visualization Application

## Project Overview

This project is a PySide6 desktop application for live visualization and offline inspection of streamed signal data.

The application can load `recording.pkl` directly for offline plotting. It can also connect to a TCP server, receive raw EMG-like signal data, reconstruct the incoming byte stream into NumPy arrays, and display the data in real time.

The application follows an MVVM-style architecture:

- Models handle TCP communication, buffering, and signal processing.
- ViewModels manage application state and connect GUI actions to the model layer.
- Views contain the PySide6 GUI and plotting widgets.

## Installation

Clone the repository and open the project folder:

```bash
git clone <your-repository-url>
cd Applied-Programming-2026
```

Install the project dependencies with `uv`:

```bash
uv sync
```

Alternatively, install only the final project dependencies with `pip`:

```bash
python -m pip install -r final_project/requirements.txt
```

If the virtual environment already exists, the application can also be run directly with:

```bash
.venv/bin/python
```

## Dependencies

The main libraries used by the final project are:

- `numpy`: numerical data handling and buffer storage
- `scipy`: RMS and Butterworth band-pass signal processing
- `PySide6`: desktop GUI framework
- `vispy`: real-time live plotting
- `matplotlib`: offline signal inspection
- `uv`: dependency and environment management

The complete dependency list is defined in the project `pyproject.toml`.
The final project dependency subset is also listed in `final_project/requirements.txt`.

## Running the Application

Start the GUI application:

```bash
.venv/bin/python -m final_project.main
```

The GUI automatically looks for `recording.pkl` in the current project folder and opens the Offline tab with the loaded plot.

To use live streaming, start the TCP server in another terminal:

```bash
.venv/bin/python TCP_Server/main.py
```

The server loads `recording.pkl` and streams the first 32 channels as raw `float64` values.

In the GUI:

1. Enter `localhost` as host.
2. Enter `12345` as port.
3. Click `Connect`.
4. The live stream starts automatically after the connection succeeds.
5. Click `Disconnect` to stop receiving data.
6. Click `Load Offline Plot` to inspect the local or recorded signal.

## TCP Data Format

The client expects the same data format as the provided TCP server:

```text
32 channels x 18 samples
float64
```

One complete packet contains:

```text
32 x 18 x 8 = 4608 bytes
```

Because TCP is a byte stream, one `recv()` call may contain a partial packet, one complete packet, or multiple packets. The client therefore stores incoming bytes in a byte buffer and only reconstructs a NumPy packet when at least 4608 bytes are available.

## Features

The application provides:

- TCP connection to the provided signal server
- Host and port input fields
- Connect and disconnect controls
- Visible connection status messages
- Live signal plotting with VisPy
- Offline signal inspection with Matplotlib
- Channel selection from channel 1 to channel 32
- Single-channel live display
- `Plot All Channels` mode with vertical offsets
- Signal mode switching for live and offline plots
- Error handling for invalid ports, failed connections, lost connections, invalid channels, and missing offline data

## Signal Processing

The application supports three signal modes:

### Original

The raw reconstructed signal is displayed without additional processing.

### Filtered

A Butterworth band-pass filter is applied channel by channel.

Parameters:

- Low cutoff: `20 Hz`
- High cutoff: `450 Hz`
- Filter order: `4`

If the sampling rate is too low for the configured high cutoff, the high cutoff is limited below the Nyquist frequency.

### RMS

The RMS signal is computed using a moving window.

Parameters:

- RMS window: `100 ms`

## Project Structure

```text
final_project/
├── README.md
├── requirements.txt
├── __init__.py
├── main.py
├── models/
│   ├── __init__.py
│   ├── signal_processing.py
│   └── tcp_client_model.py
├── viewmodels/
│   ├── __init__.py
│   └── main_view_model.py
└── views/
    ├── __init__.py
    ├── live_plot_view.py
    ├── main_view.py
    └── offline_plot_view.py
```

## MVVM Architecture

### Models

`TcpClientModel` handles:

- TCP socket connection and disconnection
- non-blocking byte receiving
- byte buffering
- packet reconstruction
- rolling live buffer
- full recording buffer for offline plotting

`SignalProcessor` handles:

- original signal mode
- RMS computation
- Butterworth band-pass filtering

The model layer does not contain GUI code.

### ViewModel

`MainViewModel` handles:

- connect and disconnect actions
- selected channel state
- selected signal mode state
- Plot All Channels state
- periodic live data updates with `QTimer`
- status messages
- communication between model and view using Qt signals

The ViewModel owns the model objects and emits processed plot data to the views.

### Views

`MainView` contains the main PySide6 window and user controls.

`LivePlotView` contains the VisPy live plot.

`OfflinePlotView` contains the Matplotlib offline plot.

The view layer does not directly receive TCP data.

## Team Members and Responsibilities

| Team Member     | Responsibility |
|-----------------|---|
| Zihan Zhang | TCP client model, byte buffering, packet reconstruction |
| Ziyv Chen   | PySide6 views, VisPy live plot, Matplotlib offline plot |
| Tianze Niu  | ViewModel integration, signal processing, documentation and testing |

## Testing

The application was tested with the provided TCP server and `recording.pkl`.

Verified behavior:

- TCP server loads data with shape `(32, 18, 2223)`
- server sends packets with shape `(32, 18)`
- each packet contains `4608` bytes
- client reconstructs streamed data into `(32, samples)`
- live plot signals are emitted by the ViewModel
- offline plot data remains available after disconnecting
- original, RMS, and filtered modes preserve the expected data shape
