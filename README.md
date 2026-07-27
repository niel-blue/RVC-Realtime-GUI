# RVC-Realtime-GUI

RVC-Realtime-GUI is a Windows desktop client for low-latency, real-time RVC
(Retrieval-based Voice Conversion).

This repository contains the source for the **CUDA 12.8 standard build**.
It is maintained as a focused derivative of
[RVC-Project/Retrieval-based-Voice-Conversion-WebUI](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI).

The ready-to-run package is distributed separately on Hugging Face. It includes
the bundled Python runtime, CUDA/PyTorch stack, FFmpeg, inference assets, and
the release model set. The download link will be added with the first public
release.

## Highlights

- Dedicated CustomTkinter desktop interface with Japanese and English UI
- CUDA 12.8 standard build, including current NVIDIA GPU support
- Real-time RVC inference with CUDA Graph warm-up
- WASAPI and native ASIO audio-device routing
- Independent input, output, and monitor device selection
- Model gallery and model-specific general settings
- WAV recording: separate input/output, mix, or split L/R recording
- Audio-file input through bundled FFmpeg in the packaged release
- Runtime-log display and log-file export

## Source layout

| Path | Purpose |
| --- | --- |
| `app/` | Application entry point and GUI |
| `infer/` | RVC real-time inference, HuBERT, RMVPE, and FCPE code |
| `tools/` | GUI adapter, audio routing, recording, file input, and helpers |
| `configs/config.py` | CUDA device and precision selection |
| `models/README.md` | Model folder layout used by the packaged application |
| `tests/` | Source-level regression tests |

## Not stored in Git

The Git repository intentionally excludes all user-specific and large binary
files:

- Bundled Python runtime, PyTorch, CUDA libraries, and package cache
- RVC `.pth` models and FAISS `.index` files
- HuBERT and RMVPE weight files
- FFmpeg binaries
- Audio recordings, logs, window position, and local device settings

These files belong to the Hugging Face release package, not the source history.

## Development

This source tree is intended for development of the packaged CUDA 12.8 build.
Use the release package as the reference runtime, then run:

```bat
RVC-Realtime-GUI-CUDA128.bat
```

The package must contain `runtime/`, `assets/`, `tools/ffmpeg/`, and at least
one model folder under `models/`.

## Upstream and license

This project is based on RVC-WebUI by RVC-Project. See [NOTICE.md](NOTICE.md)
and [LICENSE](LICENSE) for attribution and license information.
