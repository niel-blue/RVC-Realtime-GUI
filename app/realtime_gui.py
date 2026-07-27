import os
import queue
import re
import sys
import locale
import threading

app_dir = os.path.dirname(os.path.abspath(__file__))
now_dir = os.path.dirname(app_dir)
if now_dir not in sys.path:
    sys.path.insert(0, now_dir)

from tools.file_io import read_text
from tools.model_registry import discover_models
from app.version import APP_TITLE, BUILD_LABEL

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("SD_ENABLE_ASIO", "1")

os.environ["OMP_NUM_THREADS"] = "4"

realtime_config_path = os.path.join(now_dir, "configs", "config.json")
window_state_path = os.path.join(now_dir, "configs", "window.json")
logs_dir = os.path.join(now_dir, "logs")

# Shared layout dimensions. Keep these in one place so runtime updates do not
# silently restore a different size than the initial layout.
MAIN_WINDOW_WIDTH = 700
MAIN_WINDOW_HEIGHT = 720
AUDIO_DEVICES_WIDTH = 520
AUDIO_DEVICES_HEIGHT_MIC = 200
AUDIO_DEVICES_HEIGHT_FILE = 230
MODEL_FRAME_SIZE = (160, 205)
GENERAL_SETTINGS_SIZE = (340, 255)
PERFORMANCE_SETTINGS_SIZE = (340, 255)
MODEL_GALLERY_WIDTH = 690
MODEL_GALLERY_HEIGHT_MENU = 160
MODEL_GALLERY_HEIGHT_COMBO = 100
RECORDING_FRAME_SIZE = (690, 70)
# Bottom operation bar (Start / Passthrough / latency / log toggle).
# Adjust this single value to tune the outer width and height of the bar.
BOTTOM_CONTROLS_FRAME_SIZE = (690, 65)
RUNTIME_LOG_FRAME_SIZE = (690, 180)
FILE_INPUT_EXTRA_HEIGHT = AUDIO_DEVICES_HEIGHT_FILE - AUDIO_DEVICES_HEIGHT_MIC
MODEL_GALLERY_EXTRA_HEIGHT = (
    MODEL_GALLERY_HEIGHT_MENU - MODEL_GALLERY_HEIGHT_COMBO
)
RUNTIME_LOG_TEXT_SIZE = (660, 140)

# Screen-specific control geometry.  Keep visual tuning values here; the
# generic widget rendering values stay in tools/ctk_gui.py.
SETTINGS_LABEL_SIZE = (15, 1)
AUDIO_DEVICE_LABEL_SIZE = (14, 1)
SETTINGS_SLIDER_SIZE = (18, 15)
SETTINGS_SLIDER_VALUE_RIGHT_MARGIN = 6
MODEL_SELECTOR_COMBO_SIZE = (25, 1)
MODEL_RELOAD_BUTTON_SIZE = (12, 1)
MODEL_GALLERY_VIEW_SIZE = (675, 90)
MODEL_HEADER_BUTTON_WIDTH = 88
THEME_HEADER_BUTTON_WIDTH = 96
INPUT_SOURCE_COMBO_SIZE = (17, 1)
DEVICE_COMBO_SIZE = (34, 1)
DEVICE_LEVEL_METER_SIZE = (90, 8)
FILE_NAME_SIZE = (16, 1)
FILE_MEDIA_BUTTON_WIDTH = 28
FILE_SEEK_SIZE = (18, 1)
FILE_POSITION_SIZE = (6, 1)
FILE_VOLUME_SLIDER_SIZE = (11, 1)
FILE_VOLUME_VALUE_WIDTH = 16
MODEL_IMAGE_SIZE = (140, 140)
MODEL_NAME_SIZE = (20, 1)
GPU_COMBO_SIZE = (24, 1)
MEDIUM_ACTION_BUTTON_WIDTH = 88
RECORDING_MODE_COMBO_SIZE = (29, 1)
RECORDING_STATUS_SIZE = (18, 1)
RUN_STATUS_SIZE = (42, 1)
LOG_BUTTON_WIDTH = 80
LOG_TEXT_SIZE = (80, 6)

flag_vc = False
_ui_language = (
    os.environ.get("RVC_UI_LANGUAGE")
    or locale.getlocale()[0]
    or ""
).lower()
IS_JAPANESE_UI = _ui_language.startswith("ja")
UI_TEXT = {
    "gpu": ("\u4f7f\u7528GPU", "GPU"),
    "model_list": ("\u4e00\u89a7\u8868\u793a", "Show list"),
    "model_combo": ("\u30e1\u30cb\u30e5\u30fc\u8868\u793a", "Show menu"),
    "theme_dark": ("ダークモード", "Dark mode"),
    "theme_light": ("ライトモード", "Light mode"),
    "recording": ("録音", "Recording"),
    "record": ("● 録音", "● Record"),
    "recording_separate": ("別ファイル（入力＋変換後）", "Separate files (input + output)"),
    "recording_mix": ("ミックス（入力＋変換後）", "Mix (input + output)"),
    "recording_stereo": ("L/R分離（左: 入力／右: 変換後）", "Split L/R (left: input / right: output)"),
    "save_folder": ("保存先", "Save folder"),
    "change": ("変更", "Change"),
    "open_folder": ("フォルダを開く", "Open folder"),
    "monitor_disabled": ("使用しない", "Disabled"),
    "model": ("モデル", "Model"),
    "reload": ("再読み込み", "Reload"),
    "device_type": ("デバイス種別", "Audio system"),
    "wasapi_exclusive": ("WASAPI排他", "WASAPI exclusive"),
    "show_legacy_devices": ("互換デバイスを表示", "Show compatibility devices"),
    "reload_devices": ("デバイスリストのリロード", "Reload device list"),
    "input_device": ("入力デバイス", "Input device"),
    "output_device": ("出力デバイス", "Output device"),
    "monitor_device": ("モニターデバイス", "Monitor device"),
    "asio_driver": ("ASIOドライバー", "ASIO driver"),
    "asio_input_channels": ("ASIO入力", "ASIO input"),
    "asio_output_channels": ("ASIO出力", "ASIO output"),
    "asio_monitor_channels": ("ASIOモニター", "ASIO monitor"),
    "active_rate": ("動作サンプルレート：", "Sample rate:"),
    "input_gain": ("入力ゲイン (dB)", "Input gain (dB)"),
    "output_gain": ("出力ゲイン (dB)", "Output gain (dB)"),
    "monitor_gain": ("モニターゲイン (dB)", "Monitor gain (dB)"),
    "noise_gate": ("ノイズゲート値 (dB)", "Noise gate (dB)"),
    "pitch": ("ピッチ", "Tune"),
    "formant": ("フォルマント", "Formant"),
    "index_rate": ("インデックス使用率", "Index"),
    "rms_mix": ("音量追従ミックス", "Volume envelope"),
    "pitch_detector": ("ピッチ検出方式", "F0 detector"),
    "reset": ("リセット", "Reset"),
    "chunk": ("チャンク長 (秒)", "Chunk (sec)"),
    "crossfade": ("クロスフェード (秒)", "Crossfade (sec)"),
    "extra": ("追加推論バッファ (秒)", "Extra (sec)"),
    "input_denoise": ("入力ノイズの低減", "Input denoise"),
    "output_denoise": ("出力ノイズの低減", "Output denoise"),
    "clear_log": ("ログを消去", "Clear log"),
    "save_log": ("ログを保存", "Save log"),
    "runtime_log": ("ログを表示", "Show log"),
    "hide_runtime_log": ("ログを隠す", "Hide log"),
    "start": ("スタート", "Start"),
    "converting": ("変換中", "Converting"),
    "audio_passthrough": ("音声パススルー", "Passthrough"),
    "passthrough_active": ("パススルー中", "Passthrough Active"),
    "algorithm_latency": ("遅延:", "Latency:"),
    "inference_time": ("推論:", "Inference:"),
    "status_conversion_started": ("変換を開始しました", "Conversion started"),
    "status_conversion_stopped": ("変換を停止しました", "Conversion stopped"),
    "status_passthrough_started": ("音声パススルーを開始しました", "Passthrough started"),
    "status_passthrough_stopped": ("音声パススルーを停止しました", "Passthrough stopped"),
    "status_recording_started": ("録音を開始しました", "Recording started"),
    "status_recording_saved": ("録音を保存しました", "Recording saved"),
    "status_log_saved": ("ログを保存しました", "Log saved"),
    "status_file_selected": ("音声ファイルを選択しました", "Audio file selected"),
    "status_playing": ("再生中", "Playing"),
    "status_paused": ("一時停止中", "Paused"),
    "status_playback_stopped": ("再生を停止しました", "Playback stopped"),
    "status_settings_changed": ("設定変更のため変換を停止しました", "Conversion stopped for settings changes"),
    "status_audio_error": ("音声デバイスを開始できませんでした", "Could not start audio devices"),
}


def ui_text(key):
    return UI_TEXT[key][0 if IS_JAPANESE_UI else 1]


MONITOR_DISABLED = ui_text("monitor_disabled")
INPUT_SOURCE_MICROPHONE = "マイク／音声デバイス" if IS_JAPANESE_UI else "Microphone / audio device"
INPUT_SOURCE_FILE = "音声ファイル" if IS_JAPANESE_UI else "Audio file"
FILE_UI_TEXT = {
    "browse": "参照" if IS_JAPANESE_UI else "Browse",
    "play": "▶",
    "pause": "Ⅱ",
    "stop": "■",
}
GENERAL_DEFAULTS = {
    "input_gain_db": 0.0,
    "output_gain_db": 0.0,
    "monitor_gain_db": 0.0,
    "threhold": -60.0,
    "pitch": 0.0,
    "formant": 0.0,
    # Keep the original real-time RVC defaults.  They avoid index blending and
    # envelope post-processing until the user explicitly enables them.
    "index_rate": 0.0,
    "rms_mix_rate": 0.0,
    "f0method": "rmvpe",
}
MODEL_GENERAL_SETTINGS_FILENAME = "realtime_settings.json"
MODEL_GENERAL_SETTING_KEYS = (
    "input_gain_db",
    "output_gain_db",
    "monitor_gain_db",
    "threhold",
    "pitch",
    "formant",
    "index_rate",
)
MODEL_SETTINGS_SAVE_DELAY_SECONDS = 0.25

PERFORMANCE_DEFAULTS = {
    "block_time": 0.25,
    "crossfade_length": 0.05,
    "extra_time": 2.5,
    "I_noise_reduce": False,
    "O_noise_reduce": False,
}

MAX_LOG_CHARS = 40000


class QueueTextWriter:
    def __init__(self, text_queue, mirror=None):
        self.text_queue = text_queue
        self.mirror = mirror

    def write(self, text):
        if not text:
            return 0
        if self.mirror is not None:
            try:
                self.mirror.write(text)
            except UnicodeEncodeError:
                # The Japanese Windows console is often CP932 and cannot
                # print every character used by the UI title (for example —).
                encoding = getattr(self.mirror, "encoding", "cp932") or "cp932"
                safe_text = str(text).encode(encoding, "replace").decode(encoding)
                self.mirror.write(safe_text)
        enqueue_latest(self.text_queue, str(text))
        return len(text)

    def flush(self):
        if self.mirror is not None:
            self.mirror.flush()

    def isatty(self):
        return False


def db_to_linear(db):
    return 10.0 ** (float(db) / 20.0)


def enqueue_latest(block_queue, block):
    try:
        block_queue.put_nowait(block)
        return
    except queue.Full:
        pass
    try:
        block_queue.get_nowait()
    except queue.Empty:
        pass
    try:
        block_queue.put_nowait(block)
    except queue.Full:
        pass


def printt(strr, *args):
    if len(args) == 0:
        print(strr)
    else:
        print(strr % args)


if __name__ == "__main__":
    import datetime
    import json
    import time
    import traceback

    # Construct the splash before importing Torch/librosa.  Those imports may
    # take several seconds on a cold launch, so creating it in GUI.__init__
    # was too late for the user to see any startup feedback.
    try:
        saved_window = json.loads(read_text(window_state_path))
        # Center the 290x150 splash over the saved 720x580 main window.
        splash_x = int(saved_window["x"]) + 215
        splash_y = int(saved_window["y"]) + 215
        os.environ["RVC_SPLASH_POSITION"] = f"{splash_x},{splash_y}"
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        os.environ.pop("RVC_SPLASH_POSITION", None)

    from tools import ctk_gui as sg

    startup_screen = sg.StartupScreen(
        "起動中…" if IS_JAPANESE_UI else "Starting…",
        title=APP_TITLE,
        product_text=APP_TITLE.replace(" — ", "\n"),
    )

    import librosa
    from tools.torchgate import TorchGate
    import numpy as np
    import sounddevice as sd
    import torch
    import torch.nn.functional as F
    import torchaudio.transforms as tat

    from configs.config import Config, get_device_dtype_sm
    from infer import rtrvc as rvc_for_realtime
    from tools.audio_fifo import AudioFrameFifo
    from tools.cuda_graph import cuda_graph_enabled, run_cuda_graph
    from tools.file_audio_source import FileAudioSource
    from tools.wav_recorder import WavRecorder


    class GUIConfig:
        def __init__(self) :
            self.model_name = ""
            self.pth_path = ""
            self.index_path = ""
            self.pitch = GENERAL_DEFAULTS["pitch"]
            self.formant = GENERAL_DEFAULTS["formant"]
            self.sr_type = "auto"
            self.block_time = PERFORMANCE_DEFAULTS["block_time"]
            self.threhold = GENERAL_DEFAULTS["threhold"]
            self.crossfade_time = PERFORMANCE_DEFAULTS["crossfade_length"]
            self.extra_time = PERFORMANCE_DEFAULTS["extra_time"]
            self.I_noise_reduce = PERFORMANCE_DEFAULTS["I_noise_reduce"]
            self.O_noise_reduce = PERFORMANCE_DEFAULTS["O_noise_reduce"]
            self.rms_mix_rate = GENERAL_DEFAULTS["rms_mix_rate"]
            self.index_rate = GENERAL_DEFAULTS["index_rate"]
            self.input_gain_db = GENERAL_DEFAULTS["input_gain_db"]
            self.output_gain_db = GENERAL_DEFAULTS["output_gain_db"]
            self.monitor_gain_db = GENERAL_DEFAULTS["monitor_gain_db"]
            self.input_gain = 1.0
            self.output_gain = 1.0
            self.monitor_gain = 1.0
            self.f0method = GENERAL_DEFAULTS["f0method"]
            self.sg_input_hostapi = ""
            self.sg_output_hostapi = ""
            self.sg_monitor_hostapi = ""
            self.wasapi_exclusive = False
            self.sg_wasapi_exclusive = False
            self.show_legacy_devices = False
            self.sg_input_device = ""
            self.sg_output_device = ""
            self.sg_monitor_device = MONITOR_DISABLED

    class GUI:
        def __init__(self) :
            self.startup_screen = startup_screen
            self.log_queue = queue.Queue(maxsize=2000)
            self.log_text = ""
            self.original_stdout = sys.stdout
            self.original_stderr = sys.stderr
            sys.stdout = QueueTextWriter(self.log_queue, self.original_stdout)
            sys.stderr = QueueTextWriter(self.log_queue, self.original_stderr)
            self.gui_config = GUIConfig()
            self.config = Config()
            printt(APP_TITLE)
            printt(BUILD_LABEL)
            printt("RVC_CUDA_GRAPH=%s", os.environ.get("RVC_CUDA_GRAPH", "0"))
            self.function = "vc"
            self.delay_time = 0
            self.hostapis = None
            self.input_devices = None
            self.output_devices = None
            self.input_devices_indices = None
            self.output_devices_indices = None
            self.stream = None
            self.input_stream = None
            self.output_stream = None
            self.output_queue = None
            self.asio_input_fifo = None
            self.asio_worker_stop = None
            self.asio_worker_wakeup = None
            self.asio_worker = None
            self.asio_duplex_main_channels = 0
            self.asio_duplex_monitor_channels = 0
            self.input_wasapi_settings = None
            self.output_wasapi_settings = None
            self.monitor_wasapi_settings = None
            self.last_input_meter_update = 0.0
            self.last_output_meter_update = 0.0
            self.latest_input_meter = 0.0
            self.latest_output_meter = 0.0
            self.latest_monitor_meter = 0.0
            self.latest_infer_time = 0
            self.monitor_stream = None
            self.monitor_queue = None
            self.monitor_device_index = None
            self.recorder = WavRecorder()
            self.recording_folder = os.path.join(now_dir, "recordings")
            self.file_audio_source = None
            self.file_input_path = ""
            self.file_input_volume = 1.0
            self.file_source_active = False
            self.pending_model_settings_name = None
            self.model_settings_save_due = 0.0
            self.ffmpeg_path = os.path.join(now_dir, "tools", "ffmpeg", "ffmpeg.exe")
            self.models_root = os.path.join(now_dir, "models")
            os.makedirs(self.models_root, exist_ok=True)
            self.startup_screen.set_text(
                "モデルを確認しています…"
                if IS_JAPANESE_UI
                else "Checking models…"
            )
            self.refresh_models()
            self.abort_startup_if_requested()
            self.startup_screen.set_text(
                "オーディオデバイスを確認しています…"
                if IS_JAPANESE_UI
                else "Checking audio devices…"
            )
            self.update_devices(show_legacy=False)
            self.abort_startup_if_requested()
            self.launcher()

        def abort_startup_if_requested(self):
            if self.startup_screen.cancelled:
                self.restore_console_streams()
                raise SystemExit

        def refresh_models(self):
            self.models = discover_models(self.models_root)
            self.models_by_name = {model.name: model for model in self.models}
            self.model_names = [model.name for model in self.models]

        def refresh_gpu_options(self):
            automatic = "自動（推奨）" if IS_JAPANESE_UI else "Automatic (recommended)"
            self.gpu_option_indices = {automatic: None}
            self.gpu_options = [automatic]
            if not torch.cuda.is_available():
                return
            for index in range(torch.cuda.device_count()):
                device, _, _, _ = get_device_dtype_sm(index)
                if device.type != "cuda":
                    continue
                label = f"GPU {index} — {torch.cuda.get_device_name(index)}"
                self.gpu_option_indices[label] = index
                self.gpu_options.append(label)

        def apply_selected_gpu(self, option):
            index = self.gpu_option_indices.get(option)
            if index is None:
                return
            self.config.select_cuda_device(index)

        def model_description(self, model_name):
            model = self.models_by_name.get(model_name)
            if model is None:
                return (
                    "利用可能なモデルがありません"
                    if IS_JAPANESE_UI
                    else "No models available"
                )
            index_name = model.index_path.name if model.index_path else (
                "なし" if IS_JAPANESE_UI else "None"
            )
            prefix = "モデル" if IS_JAPANESE_UI else "Model"
            return f"{prefix}: {model.model_path.name} / Index: {index_name}"

        def model_general_settings_path(self, model_name):
            model = self.models_by_name.get(model_name)
            if model is None:
                return None
            return model.directory / MODEL_GENERAL_SETTINGS_FILENAME

        def load_model_general_settings(self, model_name):
            """Return one model's GENERAL SETTINGS, or safe defaults."""
            settings = {
                key: GENERAL_DEFAULTS[key] for key in MODEL_GENERAL_SETTING_KEYS
            }
            path = self.model_general_settings_path(model_name)
            if path is None or not path.is_file():
                return settings
            try:
                with open(path, "r", encoding="utf-8") as settings_file:
                    saved = json.load(settings_file)
                if not isinstance(saved, dict):
                    return settings
                for key in MODEL_GENERAL_SETTING_KEYS:
                    value = saved.get(key)
                    if isinstance(value, (int, float)) and np.isfinite(value):
                        settings[key] = float(value)
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                printt("Could not read model settings: %s", path)
            return settings

        def save_model_general_settings(self, model_name):
            """Atomically save GENERAL SETTINGS beside the selected model."""
            path = self.model_general_settings_path(model_name)
            if path is None:
                return
            settings = {
                key: float(getattr(self.gui_config, key))
                for key in MODEL_GENERAL_SETTING_KEYS
            }
            temporary_path = path.with_suffix(path.suffix + ".tmp")
            try:
                with open(temporary_path, "w", encoding="utf-8") as settings_file:
                    json.dump(settings, settings_file, ensure_ascii=False, indent=2)
                os.replace(temporary_path, path)
            except OSError as error:
                try:
                    if temporary_path.exists():
                        temporary_path.unlink()
                except OSError:
                    pass
                printt("Could not save model settings: %s", error)

        def schedule_model_general_settings_save(self):
            if not hasattr(self, "window"):
                return
            model_name = self.window["model_name"].get()
            if model_name not in self.models_by_name:
                return
            self.pending_model_settings_name = model_name
            self.model_settings_save_due = (
                time.monotonic() + MODEL_SETTINGS_SAVE_DELAY_SECONDS
            )

        def flush_model_general_settings_save(self, force=False):
            model_name = self.pending_model_settings_name
            if not model_name:
                return
            if not force and time.monotonic() < self.model_settings_save_due:
                return
            self.save_model_general_settings(model_name)
            self.pending_model_settings_name = None
            self.model_settings_save_due = 0.0

        def apply_model_general_settings(self, model_name):
            settings = self.load_model_general_settings(model_name)
            for key, value in settings.items():
                self.window[key].update(value)
                setattr(self.gui_config, key, value)
            self.gui_config.input_gain = db_to_linear(settings["input_gain_db"])
            self.gui_config.output_gain = db_to_linear(settings["output_gain_db"])
            self.gui_config.monitor_gain = db_to_linear(settings["monitor_gain_db"])

        def model_image_path(self, model_name):
            model = self.models_by_name.get(model_name)
            if model is None:
                return ""
            images = []
            for pattern in ("*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"):
                images.extend(model.directory.glob(pattern))
            if not images:
                return ""
            return str(sorted(images, key=lambda path: path.name.casefold())[0])

        def model_gallery_cards(self):
            self.model_card_events = {}
            cards = []
            for index, model_name in enumerate(self.model_names):
                event_key = f"model_gallery_{index}"
                self.model_card_events[event_key] = model_name
                cards.append((event_key, model_name, self.model_image_path(model_name)))
            return cards

        def update_selected_model_ui(self, model_name, refresh_gallery=True):
            self.window["model_name"].Update(value=model_name)
            self.window["model_description"].Update(
                self.model_description(model_name)
            )
            self.window["model_image"].Update(self.model_image_path(model_name))
            self.window["model_image_name"].Update(model_name)
            if refresh_gallery:
                self.window["model_gallery"].Update(
                    cards=self.model_gallery_cards(), selected=model_name
                )
            else:
                self.window["model_gallery"].Update(selected=model_name)

        def toggle_model_selector(self):
            self.model_gallery_visible = not self.model_gallery_visible
            combo_visible = not self.model_gallery_visible
            self.window["model_combo_container"].Update(visible=combo_visible)
            self.window["model_gallery"].Update(
                cards=self.model_gallery_cards(),
                selected=self.window["model_name"].get(),
            )
            self.window["model_gallery_container"].Update(
                visible=self.model_gallery_visible
            )
            self.window["inference_model_frame"].Update(
                size=(MODEL_GALLERY_WIDTH, MODEL_GALLERY_HEIGHT_MENU if self.model_gallery_visible else MODEL_GALLERY_HEIGHT_COMBO)
            )
            self.window.update_header_button(
                "toggle_model_selector",
                ui_text("model_combo" if self.model_gallery_visible else "model_list"),
            )
            self.resize_main_window()
            self.save_ui_preferences()

        def theme_button_text(self):
            current = self.theme_mode
            if current == "system":
                current = sg.get_appearance_mode()
            return ui_text("theme_light" if current == "dark" else "theme_dark")

        def resize_main_window(self):
            # Keep a compact baseline and add only optional visible rows.
            height = MAIN_WINDOW_HEIGHT
            if self.file_source_active:
                height += FILE_INPUT_EXTRA_HEIGHT
            if self.model_gallery_visible:
                height += MODEL_GALLERY_EXTRA_HEIGHT
            if self.log_visible:
                height += RUNTIME_LOG_FRAME_SIZE[1]
            self.window.set_size(MAIN_WINDOW_WIDTH, height)

        @staticmethod
        def format_file_time(seconds):
            seconds = max(0, int(seconds))
            return f"{seconds // 60:02}:{seconds % 60:02}"

        def update_file_input_ui(self, active):
            self.file_source_active = bool(active)
            self.window["file_input_container"].update(visible=active)
            self.window["browse_audio_file"].update(visible=active)
            self.window["file_input_name"].update(visible=active)
            self.window["audio_devices_frame"].update(
                size=(AUDIO_DEVICES_WIDTH, AUDIO_DEVICES_HEIGHT_FILE if active else AUDIO_DEVICES_HEIGHT_MIC)
            )
            self.window["sg_input_device"].widget.configure(
                state="disabled" if active else "normal"
            )
            self.resize_main_window()

        def refresh_file_playback_ui(self):
            source = self.file_audio_source
            if source is None:
                return
            if source.finished or not source.playing:
                self.window["play_audio_file"].update(
                    button_color=("#3b8ed0", "#1f6aa5"),
                    hover_color=("#36719f", "#144870"),
                )
            if source.error:
                error = source.error
                source.error = None
                sg.popup_error(str(error))
            self.window["file_position"].update(self.format_file_time(source.position))
            self.window["file_seek"].update(value=source.position)

        def choose_file_input(self):
            initial_dir = os.path.dirname(self.file_input_path) if self.file_input_path else now_dir
            path = sg.choose_audio_file(initial_dir)
            if not path:
                return
            if not os.path.isfile(self.ffmpeg_path):
                sg.popup_error(
                    "同梱FFmpegが見つかりません。tools\\ffmpeg\\ffmpeg.exe を確認してください。"
                    if IS_JAPANESE_UI
                    else "Bundled FFmpeg was not found at tools\\ffmpeg\\ffmpeg.exe."
                )
                return
            self.stop_file_playback()
            self.file_input_path = path
            file_name = os.path.basename(path)
            self.window["file_input_name"].update(file_name)
            self.set_run_status(f"{ui_text('status_file_selected')}: {file_name}")

        def start_file_playback(self):
            if False and not flag_vc:
                sg.popup("先に変換を開始してください。" if IS_JAPANESE_UI else "Start conversion first.")
                return
            if not self.file_source_active or not self.file_input_path:
                return
            if not os.path.isfile(self.ffmpeg_path):
                sg.popup_error("FFmpeg was not found.")
                return
            if self.output_stream is None:
                try:
                    self.prepare_file_playback_output()
                except Exception as error:
                    sg.popup_error(str(error))
                    return
            if self.file_audio_source is None:
                tail_blocks = max(2, int((self.gui_config.extra_time + self.gui_config.crossfade_time) / self.gui_config.block_time) + 2)
                try:
                    self.file_audio_source = FileAudioSource(
                        self.ffmpeg_path,
                        self.file_input_path,
                        self.gui_config.samplerate,
                        self.block_frame,
                        self.handle_file_audio_block,
                        tail_blocks=tail_blocks,
                    )
                except OSError as error:
                    sg.popup_error(str(error))
                    return
                self.window["file_seek"].widget.configure(to=max(self.file_audio_source.duration, 1.0))
            self.file_audio_source.play()
            self.window["play_audio_file"].update(
            button_color=("#36719f", "#144870"),
            hover_color=("#36719f", "#144870"),
            )
            self.set_run_status(ui_text("status_playing"))

        def pause_file_playback(self):
            if self.file_audio_source is not None:
                self.file_audio_source.pause()
            self.window["play_audio_file"].update(
                button_color=("#3b8ed0", "#1f6aa5"),
                hover_color=("#36719f", "#144870"),
            )
            self.set_run_status(ui_text("status_paused"))

        def prepare_file_playback_output(self):
            self.set_devices(
                self.window["sg_input_device"].get(),
                self.window["sg_output_device"].get(),
                self.window["sg_monitor_device"].get(),
            )
            self.gui_config.channels = 1
            self.gui_config.output_channels = self.get_output_channels()
            self.gui_config.samplerate = self.get_automatic_samplerate(48000)
            self.zc = self.gui_config.samplerate // 100
            self.block_frame = max(
                self.zc,
                int(round(self.gui_config.block_time * self.gui_config.samplerate / self.zc)) * self.zc,
            )
            self.start_file_stream()

        def handle_file_audio_block(self, block):
            if flag_vc:
                self.audio_callback(block[:, None], self.block_frame, None, None)
                return
            volume = float(np.clip(self.file_input_volume, 0.0, 1.0))
            block = np.clip(block * np.float32(volume), -1.0, 1.0)
            self.enqueue_audio_target(self.output_queue, block)
            self.enqueue_audio_target(
                self.monitor_queue,
                block * np.float32(self.gui_config.monitor_gain),
            )

        def stop_file_playback(self, announce=False):
            if self.file_audio_source is not None:
                self.file_audio_source.stop()
                self.file_audio_source = None
            self.window["file_position"].update("00:00")
            self.window["file_seek"].update(value=0)
            self.window["play_audio_file"].update(
                button_color=("#3b8ed0", "#1f6aa5"),
                hover_color=("#36719f", "#144870"),
            )
            if announce:
                self.set_run_status(ui_text("status_playback_stopped"))

        def seek_file_playback(self, seconds):
            if self.file_audio_source is not None:
                self.file_audio_source.seek(seconds)

        def toggle_theme(self):
            current = sg.get_appearance_mode()
            self.theme_mode = "light" if current == "dark" else "dark"
            sg.set_appearance_mode(self.theme_mode)
            self.window.refresh_appearance()
            # CTkImage can retain the previous appearance variant after
            # repeated switches.  Rebuild the compact model cards so every
            # thumbnail is created for the current appearance mode.
            self.window["model_gallery"].Update(
                cards=self.model_gallery_cards(),
                selected=self.window["model_name"].get(),
            )
            self.window.update_header_button("toggle_theme", self.theme_button_text())
            self.save_ui_preferences()

        def save_ui_preferences(self):
            try:
                settings = json.loads(read_text(realtime_config_path))
            except (OSError, ValueError, json.JSONDecodeError):
                settings = {}
            settings["model_selector_mode"] = "list" if self.model_gallery_visible else "combo"
            settings["theme_mode"] = self.theme_mode
            with open(realtime_config_path, "w", encoding="utf8") as config_file:
                json.dump(settings, config_file, ensure_ascii=False)

        def load(self):
            try:
                data = json.loads(read_text(realtime_config_path))
                if data.get("f0method") not in ("pm", "rmvpe", "fcpe"):
                    data["f0method"] = "rmvpe"
                data["pm"] = data["f0method"] == "pm"
                data["rmvpe"] = data["f0method"] == "rmvpe"
                data["fcpe"] = data["f0method"] == "fcpe"
                data["block_time"] = max(
                    0.02,
                    float(
                        data.get(
                            "block_time",
                            PERFORMANCE_DEFAULTS["block_time"],
                        )
                    ),
                )
                self.update_devices(show_legacy=False)
                old_api = data.get("sg_hostapi", "")
                data["sg_input_device"] = self.normalize_device_choice(
                    data.get("sg_input_device", ""), "input", old_api
                )
                data["sg_output_device"] = self.normalize_device_choice(
                    data.get("sg_output_device", ""), "output", old_api
                )
                for device_key, channel_key, mapping, selector_mapping in (
                    (
                        "sg_input_device",
                        "sg_asio_input_channels",
                        self.input_device_map,
                        self.input_asio_selectors,
                    ),
                    (
                        "sg_output_device",
                        "sg_asio_output_channels",
                        self.output_device_map,
                        self.output_asio_selectors,
                    ),
                ):
                    saved_channels = data.get(channel_key)
                    selected_label = data.get(device_key, "")
                    selected_index = mapping.get(selected_label)
                    if saved_channels and selected_index is not None:
                        try:
                            target_selectors = self.parse_channel_pair(saved_channels)
                        except (TypeError, ValueError):
                            target_selectors = []
                        migrated_label = next(
                            (
                                label
                                for label, index in mapping.items()
                                if index == selected_index
                                and selector_mapping.get(label) == target_selectors
                            ),
                            "",
                        )
                        if migrated_label:
                            data[device_key] = migrated_label
            except:
                with open(realtime_config_path, "w", encoding="utf8") as j:
                    data = {
                        "model_name": "",
                        "sg_wasapi_exclusive": False,
                        "sg_show_legacy_devices": False,
                        "sg_input_device": self.normalize_device_choice(
                            "", "input"
                        ),
                        "sg_output_device": self.normalize_device_choice(
                            "", "output"
                        ),
                        "sg_monitor_device": MONITOR_DISABLED,
                        "sr_type": "auto",
                        "rms_mix_rate": GENERAL_DEFAULTS["rms_mix_rate"],
                        "block_time": PERFORMANCE_DEFAULTS["block_time"],
                        "crossfade_length": PERFORMANCE_DEFAULTS[
                            "crossfade_length"
                        ],
                        "extra_time": PERFORMANCE_DEFAULTS["extra_time"],
                        "f0method": GENERAL_DEFAULTS["f0method"],
                    }
                    data["pm"] = data["f0method"] == "pm"
                    data["rmvpe"] = data["f0method"] == "rmvpe"
                    data["fcpe"] = data["f0method"] == "fcpe"
            saved_monitor = data.get("sg_monitor_device", MONITOR_DISABLED)
            monitor_device = self.normalize_device_choice(
                saved_monitor,
                "output",
                data.get("sg_hostapi", ""),
            )
            saved_monitor_name = saved_monitor.split("] ", 1)[-1]
            saved_monitor_name = saved_monitor_name.removesuffix(" ← RVC出力")
            monitor_exists = saved_monitor in self.output_device_map or any(
                self.device_names.get(index) == saved_monitor_name
                for index in self.output_device_map.values()
            )
            if saved_monitor == MONITOR_DISABLED or not monitor_exists:
                monitor_device = MONITOR_DISABLED
            if monitor_device not in self.output_devices:
                monitor_device = MONITOR_DISABLED
            data["sg_monitor_device"] = monitor_device
            selected_model = data.get("model_name", "")
            if selected_model not in self.models_by_name:
                selected_model = self.model_names[0] if self.model_names else ""
            data["model_name"] = selected_model
            data.pop("pth_path", None)
            data.pop("index_path", None)
            return data

        def launcher(self):
            data = self.load()
            # GENERAL SETTINGS belong to the selected model, not to the
            # machine-wide UI configuration.  A missing file intentionally
            # supplies the safe defaults for a newly added model.
            data.update(self.load_model_general_settings(data.get("model_name", "")))
            # Migrate the short-lived first recording UI without invalidating
            # existing user settings files.
            old_recording_modes = {
                "変換後のみ",
                "変換前のみ",
                "変換前＋変換後",
                "Converted output",
                "Original input",
                "Input + output",
            }
            if data.get("recording_mode") in old_recording_modes:
                data["recording_mode"] = ui_text("recording_separate")
            recording_mode_map = {
                "別ファイル（入力＋変換後）": ui_text("recording_separate"),
                "ミックス（入力＋変換後）": ui_text("recording_mix"),
                "L/R分離（左: 入力／右: 変換後）": ui_text("recording_stereo"),
                "Separate files (input + output)": ui_text("recording_separate"),
                "Mix (input + output)": ui_text("recording_mix"),
                "Split L/R (left: input / right: output)": ui_text("recording_stereo"),
            }
            data["recording_mode"] = recording_mode_map.get(
                data.get("recording_mode"), data.get("recording_mode")
            )
            if data["recording_mode"] not in {
                ui_text("recording_separate"),
                ui_text("recording_mix"),
                ui_text("recording_stereo"),
            }:
                data["recording_mode"] = ui_text("recording_separate")
            if data.get("input_source") not in (
                INPUT_SOURCE_MICROPHONE,
                INPUT_SOURCE_FILE,
            ):
                data["input_source"] = INPUT_SOURCE_MICROPHONE
            self.file_source_active = data["input_source"] == INPUT_SOURCE_FILE
            # Audio-file paths are deliberately session-only.  They can be
            # moved or removed between launches and must never be restored.
            data.pop("file_input_path", None)
            self.file_input_path = ""
            self.file_input_volume = float(
                np.clip(data.get("file_input_volume", 1.0), 0.0, 1.0)
            )
            self.theme_mode = data.get("theme_mode", "system")
            if self.theme_mode not in ("system", "light", "dark"):
                self.theme_mode = "system"
            self.refresh_gpu_options()
            if data.get("gpu_device") not in self.gpu_option_indices:
                data["gpu_device"] = self.gpu_options[0]
            sg.theme("LightBlue3")
            sg.set_appearance_mode(self.theme_mode)
            general_label_size = SETTINGS_LABEL_SIZE
            performance_label_size = SETTINGS_LABEL_SIZE
            audio_device_label_size = AUDIO_DEVICE_LABEL_SIZE
            slider_size = SETTINGS_SLIDER_SIZE

            def slider_row(label, key, value_range, resolution, default, tooltip=None):
                return [
                    sg.Text(label, size=general_label_size, justification="left", tooltip=tooltip),
                    sg.Push(),
                    sg.Slider(
                        range=value_range,
                        key=key,
                        resolution=resolution,
                        default_value=data.get(key, default),
                        enable_events=True,
                        size=slider_size,
                        value_right_margin=SETTINGS_SLIDER_VALUE_RIGHT_MARGIN,
                        tooltip=tooltip,
                    ),
                ]

            layout = [
                [
                    sg.Frame(
                        title="INFERENCE MODEL",
                        key="inference_model_frame",
                        size=(MODEL_GALLERY_WIDTH, MODEL_GALLERY_HEIGHT_COMBO),
                        header_button=(
                            ui_text("model_list"),
                            "toggle_model_selector",
                            MODEL_HEADER_BUTTON_WIDTH,
                            "small",
                        ),
                        header_buttons=[
                            (ui_text("model_list"), "toggle_model_selector", MODEL_HEADER_BUTTON_WIDTH, "small"),
                            (ui_text("theme_dark"), "toggle_theme", THEME_HEADER_BUTTON_WIDTH, "small"),
                        ],
                        layout=[
                            [
                                sg.Column(
                                    key="model_combo_container",
                                    layout=[
                                        [
                                            sg.Text(
                                                ui_text("model"),
                                                key="model_name_label",
                                            ),
                                            sg.Combo(
                                                self.model_names,
                                                default_value=data.get(
                                                    "model_name", ""
                                                ),
                                                key="model_name",
                                                readonly=True,
                                                enable_events=True,
                                                size=MODEL_SELECTOR_COMBO_SIZE,
                                            ),
                                            sg.Button(
                                                ui_text("reload"),
                                                key="reload_models",
                                                size=MODEL_RELOAD_BUTTON_SIZE,
                                                button_style="medium",
                                            ),
                                        ]
                                    ],
                                ),
                                sg.Column(
                                    key="model_gallery_container",
                                    layout=[
                                        [
                                            sg.ModelGallery(
                                                self.model_gallery_cards(),
                                                key="model_gallery",
                                                size=MODEL_GALLERY_VIEW_SIZE,
                                            )
                                        ]
                                    ],
                                ),
                            ],
                            [
                                sg.Text(
                                    self.model_description(data.get("model_name", "")),
                                    key="model_description",
                                ),
                            ],
                        ],
                    )
                ],
                [
                    sg.Frame(
                        layout=[
                            [
                                sg.Text(
                                    "入力ソース" if IS_JAPANESE_UI else "Input source",
                                    size=audio_device_label_size,
                                ),
                                sg.Combo(
                                    [INPUT_SOURCE_MICROPHONE, INPUT_SOURCE_FILE],
                                    key="input_source",
                                    default_value=data["input_source"],
                                    readonly=True,
                                    enable_events=True,
                                    size=INPUT_SOURCE_COMBO_SIZE,
                                ),
                                sg.Button(
                                    FILE_UI_TEXT["browse"],
                                    key="browse_audio_file",
                                    width=MEDIUM_ACTION_BUTTON_WIDTH,
                                    button_style="medium",
                                    visible=self.file_source_active,
                                ),
                                sg.Text(
                                    os.path.basename(self.file_input_path) or "—",
                                    key="file_input_name",
                                    size=FILE_NAME_SIZE,
                                    visible=self.file_source_active,
                                ),
                            ],
                            [
                                sg.Text(
                                    ui_text("input_device"),
                                    key="input_device_label",
                                    size=audio_device_label_size,
                                ),
                                sg.Combo(
                                    self.input_devices,
                                    key="sg_input_device",
                                    default_value=data.get("sg_input_device", ""),
                                    enable_events=True,
                                    size=DEVICE_COMBO_SIZE,
                                ),
                                sg.LevelMeter(
                                    key="input_level_meter",
                                    size=DEVICE_LEVEL_METER_SIZE,
                                    tooltip="入力信号レベル",
                                ),
                            ],
                            [
                                sg.Text(
                                    ui_text("output_device"),
                                    key="output_device_label",
                                    size=audio_device_label_size,
                                ),
                                sg.Combo(
                                    self.output_devices,
                                    key="sg_output_device",
                                    default_value=data.get("sg_output_device", ""),
                                    enable_events=True,
                                    size=DEVICE_COMBO_SIZE,
                                ),
                                sg.LevelMeter(
                                    key="output_level_meter",
                                    size=DEVICE_LEVEL_METER_SIZE,
                                    tooltip="変換後の出力信号レベル",
                                ),
                            ],
                            [
                                sg.Text(
                                    ui_text("monitor_device"),
                                    key="monitor_device_label",
                                    size=audio_device_label_size,
                                ),
                                sg.Combo(
                                    [MONITOR_DISABLED] + self.output_devices,
                                    key="sg_monitor_device",
                                    default_value=data.get(
                                        "sg_monitor_device", MONITOR_DISABLED
                                    ),
                                    enable_events=True,
                                    readonly=True,
                                    size=DEVICE_COMBO_SIZE,
                                    tooltip="変換後の音声を確認する追加の再生先",
                                ),
                                sg.LevelMeter(
                                    key="monitor_level_meter",
                                    size=DEVICE_LEVEL_METER_SIZE,
                                    tooltip="モニターへ送る出力信号レベル",
                                ),
                            ],
                            [
                                sg.Text(ui_text("active_rate")),
                                sg.Text("-- Hz", key="sr_stream"),
                                sg.Text("", size=(2, 1)),
                                sg.Checkbox(
                                    (
                                        "WASAPI排他モード（対応デバイスのみ）"
                                        if IS_JAPANESE_UI
                                        else "WASAPI exclusive mode (supported devices only)"
                                    ),
                                    key="sg_wasapi_exclusive",
                                    default=data.get(
                                        "sg_wasapi_exclusive", False
                                    ),
                                    enable_events=True,
                                    tooltip=(
                                        "対応しているWASAPI端点を排他モードで開きます"
                                        if IS_JAPANESE_UI
                                        else "Open supported WASAPI endpoints in exclusive mode"
                                    ),
                                ),
                            ],
                            [
                                sg.Column(
                                    key="file_input_container",
                                    layout=[
                                        [
                                            sg.Button(FILE_UI_TEXT["play"], key="play_audio_file", width=FILE_MEDIA_BUTTON_WIDTH, font_family="Segoe UI Symbol", button_style="small"),
                                            sg.Button(FILE_UI_TEXT["pause"], key="pause_audio_file", width=FILE_MEDIA_BUTTON_WIDTH, font_family="Segoe UI Symbol", button_style="small"),
                                            sg.Button(FILE_UI_TEXT["stop"], key="stop_audio_file", width=FILE_MEDIA_BUTTON_WIDTH, font_family="Segoe UI Symbol", button_style="small"),
                                            sg.Slider(
                                                range=(0, 1),
                                                default_value=0,
                                                resolution=0.01,
                                                key="file_seek",
                                                enable_events=True,
                                                size=FILE_SEEK_SIZE,
                                                show_value=False,
                                            ),
                                            sg.Text(
                                                "00:00",
                                                key="file_position",
                                                size=FILE_POSITION_SIZE,
                                                justification="center",
                                                height=26,
                                            ),
                                            sg.Text(
                                                "音量 (%)" if IS_JAPANESE_UI else "Volume (%)",
                                                height=26,
                                            ),
                                            sg.Slider(
                                                range=(0, 100),
                                                default_value=self.file_input_volume * 100,
                                                resolution=1,
                                                key="file_input_volume",
                                                enable_events=True,
                                                size=FILE_VOLUME_SLIDER_SIZE,
                                                show_value=True,
                                                value_pady=4,
                                                value_width=FILE_VOLUME_VALUE_WIDTH,
                                            ),
                                        ],
                                    ],
                                ),
                            ],
                        ],
                        title="AUDIO DEVICES",
                        key="audio_devices_frame",
                        size=(AUDIO_DEVICES_WIDTH, AUDIO_DEVICES_HEIGHT_FILE if self.file_source_active else AUDIO_DEVICES_HEIGHT_MIC),
                    ),
                    sg.Frame(
                        title="MODEL",
                        size=MODEL_FRAME_SIZE,
                        layout=[
                            [
                                sg.Image(
                                    self.model_image_path(data.get("model_name", "")),
                                    key="model_image",
                                    size=MODEL_IMAGE_SIZE,
                                    expand_x=True,
                                ),
                            ],
                            [
                                sg.Text(
                                    data.get("model_name", ""),
                                    key="model_image_name",
                                    size=MODEL_NAME_SIZE,
                                    justification="center",
                                )
                            ],
                        ],
                    ),
                ],
                [
                    sg.Frame(
                        layout=[
                            slider_row(ui_text("input_gain"), "input_gain_db", (-24, 24), 0.5, GENERAL_DEFAULTS["input_gain_db"]),
                            slider_row(ui_text("output_gain"), "output_gain_db", (-24, 24), 0.5, GENERAL_DEFAULTS["output_gain_db"]),
                            slider_row(ui_text("monitor_gain"), "monitor_gain_db", (-24, 24), 0.5, GENERAL_DEFAULTS["monitor_gain_db"]),
                            slider_row(ui_text("pitch"), "pitch", (-16, 16), 1, GENERAL_DEFAULTS["pitch"]),
                            slider_row(ui_text("formant"), "formant", (-2, 2), 0.05, GENERAL_DEFAULTS["formant"]),
                            slider_row(ui_text("index_rate"), "index_rate", (0.0, 1.0), 0.01, GENERAL_DEFAULTS["index_rate"]),
                            slider_row(ui_text("noise_gate"), "threhold", (-60, 0), 1, GENERAL_DEFAULTS["threhold"], "この音量未満の入力を無音として扱います"),
                        ],
                        title="GENERAL SETTINGS",
                        size=GENERAL_SETTINGS_SIZE,
                        header_button=(
                            ui_text("reset"),
                            "reset_general_settings",
                            72,
                            "small",
                        ),
                    ),
                    sg.Frame(
                                    layout=[
                                        slider_row(ui_text("chunk"), "block_time", (0.02, 1.5), 0.01, PERFORMANCE_DEFAULTS["block_time"]),
                                        slider_row(ui_text("crossfade"), "crossfade_length", (0.01, 0.15), 0.01, PERFORMANCE_DEFAULTS["crossfade_length"]),
                                        slider_row(ui_text("extra"), "extra_time", (0.05, 5.00), 0.01, PERFORMANCE_DEFAULTS["extra_time"]),
                                        slider_row(ui_text("rms_mix"), "rms_mix_rate", (0.0, 1.0), 0.01, GENERAL_DEFAULTS["rms_mix_rate"]),
                                        [
                                            sg.Text(ui_text("pitch_detector"), size=performance_label_size),
                                            sg.Radio("pm", "f0method", key="pm", default=data.get("pm", False), enable_events=True),
                                            sg.Radio("rmvpe", "f0method", key="rmvpe", default=data.get("rmvpe", True), enable_events=True),
                                            sg.Radio("fcpe", "f0method", key="fcpe", default=data.get("fcpe", False), enable_events=True),
                                        ],
                                        [
                                            sg.Checkbox(ui_text("input_denoise"), key="I_noise_reduce", default=data.get("I_noise_reduce", PERFORMANCE_DEFAULTS["I_noise_reduce"]), enable_events=True),
                                            sg.Checkbox(ui_text("output_denoise"), key="O_noise_reduce", default=data.get("O_noise_reduce", PERFORMANCE_DEFAULTS["O_noise_reduce"]), enable_events=True),
                                        ],
                                        [
                                            sg.Text(ui_text("gpu"), size=performance_label_size),
                                            sg.Combo(
                                                self.gpu_options,
                                                key="gpu_device",
                                                default_value=data["gpu_device"],
                                                readonly=True,
                                                enable_events=True,
                                                size=GPU_COMBO_SIZE,
                                            ),
                                        ],
                                    ],
                                    title="PERFORMANCE SETTINGS",
                                    size=PERFORMANCE_SETTINGS_SIZE,
                                    header_button=(
                                        ui_text("reset"),
                                        "reset_performance_settings",
                                        72,
                                        "small",
                                    ),
                    )
                ],
                [
                    sg.Frame(
                        title="RECORDING",
                        key="recording_frame",
                        size=RECORDING_FRAME_SIZE,
                        layout=[
                            [
                                sg.Button(
                                    ui_text("record"),
                                    key="toggle_recording",
                                    width=MEDIUM_ACTION_BUTTON_WIDTH,
                                    button_style="medium",
                                ),
                                sg.Combo(
                                    [
                                        ui_text("recording_separate"),
                                        ui_text("recording_mix"),
                                        ui_text("recording_stereo"),
                                    ],
                                    key="recording_mode",
                                    default_value=data.get("recording_mode", ui_text("recording_separate")),
                                    readonly=True,
                                    size=RECORDING_MODE_COMBO_SIZE,
                                ),
                                sg.Button(
                                    ui_text("change"),
                                    key="change_recording_folder",
                                    width=MEDIUM_ACTION_BUTTON_WIDTH,
                                    button_style="medium",
                                ),
                                sg.Button(
                                    ui_text("open_folder"),
                                    key="open_recording_folder",
                                    width=MEDIUM_ACTION_BUTTON_WIDTH,
                                    button_style="medium",
                                ),
                                sg.Text("", key="recording_status", size=RECORDING_STATUS_SIZE),
                            ],
                        ],
                    ),
                ],
                [
                    sg.Frame(
                        title="",
                        key="bottom_controls_frame",
                        size=BOTTOM_CONTROLS_FRAME_SIZE,
                        layout=[
                            [
                                sg.Button(
                                    ui_text("start"),
                                    key="start_vc",
                                    button_style="large",
                                    button_color="#2e8b57",
                                    hover_color="#267449",
                                ),
                                sg.Button(
                                    ui_text("audio_passthrough"),
                                    key="audio_passthrough",
                                    button_style="large",
                                ),
                                sg.Push(),
                                sg.Text(ui_text("algorithm_latency")),
                                sg.Text("0", key="delay_time"),
                                sg.Text("ms"),
                                sg.Text(ui_text("inference_time")),
                                sg.Text("0", key="infer_time"),
                                sg.Text("ms"),
                            ],
                            [
                                sg.Text("", key="run_status", size=RUN_STATUS_SIZE),
                                sg.Push(),
                                sg.Button(
                                    ui_text("runtime_log"),
                                    key="toggle_runtime_log",
                                    width=LOG_BUTTON_WIDTH,
                                    button_style="small",
                                ),
                            ],
                        ],
                    ),
                ],
                [
                    sg.Frame(
                        title="RUNTIME LOG",
                        size=RUNTIME_LOG_FRAME_SIZE,
                        key="runtime_log_frame",
                        header_buttons=(
                            (ui_text("save_log"), "save_log", LOG_BUTTON_WIDTH, "small"),
                            (ui_text("clear_log"), "clear_log", LOG_BUTTON_WIDTH, "small"),
                        ),
                        layout=[
                            [
                                sg.Multiline(
                                    "",
                                    key="log_output",
                                    size=LOG_TEXT_SIZE,
                                    pixel_size=RUNTIME_LOG_TEXT_SIZE,
                                    disabled=True,
                                    autoscroll=True,
                                    write_only=True,
                                    font=(sg.UI_FONT_FAMILY, 10),
                                    expand_x=True,
                                )
                            ],
                        ],
                    )
                ],
            ]
            root = self.startup_screen.take_root()
            if root is None:
                self.restore_console_streams()
                raise SystemExit
            self.window = sg.Window(
                APP_TITLE, layout=layout, finalize=True, root=root
            )
            self.window.refresh_appearance()
            # ModelGallery renders once while its selected name is still
            # empty.  Re-render with the configured model so the initial
            # card uses the same blue selected state as after a theme switch.
            self.window["model_gallery"].Update(
                cards=self.model_gallery_cards(),
                selected=data.get("model_name", ""),
            )
            self.startup_screen = None
            self.recording_folder = data.get("recording_folder", self.recording_folder)
            self.log_visible = False
            self.model_gallery_visible = False
            self.update_file_input_ui(self.file_source_active)
            if data.get("model_selector_mode") == "list":
                self.model_gallery_visible = True
            self.window["runtime_log_frame"].update(visible=False)
            self.window["model_gallery_container"].update(visible=self.model_gallery_visible)
            self.window["model_combo_container"].update(visible=not self.model_gallery_visible)
            self.window["inference_model_frame"].update(
                size=(MODEL_GALLERY_WIDTH, MODEL_GALLERY_HEIGHT_MENU if self.model_gallery_visible else MODEL_GALLERY_HEIGHT_COMBO)
            )
            self.resize_main_window()
            self.window.update_header_button(
                "toggle_model_selector",
                ui_text("model_combo" if self.model_gallery_visible else "model_list"),
            )
            self.window.update_header_button("toggle_theme", self.theme_button_text())
            self.restore_window_position()
            self.configure_audio_ui(data)
            self.log_startup_diagnostics(data)
            self.event_handler()

        def restore_window_position(self):
            try:
                state = json.loads(read_text(window_state_path))
                x, y = int(state["x"]), int(state["y"])
                if x >= -600 and y >= -300:
                    self.window.set_position(x, y)
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                pass

        def save_window_position(self):
            try:
                x, y = self.window.get_position()
                with open(window_state_path, "w", encoding="utf8") as state_file:
                    json.dump({"x": x, "y": y}, state_file)
            except OSError:
                pass

        def configure_audio_ui(self, values):
            del values

        def update_run_buttons(self):
            if not hasattr(self, "window"):
                return
            controls_locked = bool(flag_vc)
            self.window["input_source"].widget.configure(
                state="disabled" if controls_locked else "readonly"
            )
            self.window["sg_input_device"].widget.configure(
                state=(
                    "disabled"
                    if controls_locked or self.file_source_active
                    else "normal"
                )
            )
            self.window["sg_output_device"].widget.configure(
                state="disabled" if controls_locked else "normal"
            )
            self.window["sg_monitor_device"].widget.configure(
                state="disabled" if controls_locked else "readonly"
            )
            self.window["gpu_device"].widget.configure(
                state="disabled" if controls_locked else "readonly"
            )
            meter_color = "#d9822b" if flag_vc and self.function == "vc" else None
            for meter_key in (
                "input_level_meter",
                "output_level_meter",
                "monitor_level_meter",
            ):
                self.window[meter_key].set_color(meter_color)
            if flag_vc and self.function == "vc":
                self.window["start_vc"].update(
                    text=ui_text("converting"),
                    button_color="#d9822b",
                    hover_color="#b96b20",
                )
            else:
                self.window["start_vc"].update(
                    text=ui_text("start"),
                    button_color="#2e8b57",
                    hover_color="#267449",
                )
            if flag_vc and self.function == "im":
                self.window["audio_passthrough"].update(
                    text=ui_text("passthrough_active"),
                    button_color="#c44242",
                    hover_color="#a73535",
                )
            else:
                self.window["audio_passthrough"].update(
                    text=ui_text("audio_passthrough"),
                    button_color=("#3b8ed0", "#1f6aa5"),
                    hover_color=("#36719f", "#144870"),
                )

        def set_run_status(self, text):
            self.window["run_status"].update(text)
            self.window.refresh()

        def drain_log_queue(self):
            chunks = []
            for _ in range(500):
                try:
                    chunks.append(self.log_queue.get_nowait())
                except queue.Empty:
                    break
            if not chunks:
                return
            self.log_text += "".join(chunks)
            if len(self.log_text) > MAX_LOG_CHARS:
                self.log_text = self.log_text[-MAX_LOG_CHARS:]
            if self.log_visible:
                self.window["log_output"].update(self.log_text)

        def refresh_realtime_indicators(self):
            """Update GUI widgets on the GUI thread, never on the audio thread."""
            if not flag_vc:
                return
            self.window["input_level_meter"].update(self.latest_input_meter)
            self.window["output_level_meter"].update(self.latest_output_meter)
            self.window["monitor_level_meter"].update(self.latest_monitor_meter)
            self.window["infer_time"].update(self.latest_infer_time)

        def set_recording(self, enabled, values=None):
            if enabled:
                if not flag_vc:
                    sg.popup(
                        "変換を開始してから録音してください。"
                        if IS_JAPANESE_UI else "Start conversion before recording."
                    )
                    return
                labels = {
                    ui_text("recording_separate"): "separate",
                    ui_text("recording_mix"): "mix",
                    ui_text("recording_stereo"): "stereo",
                }
                mode = labels.get((values or {}).get("recording_mode"), "separate")
                try:
                    self.recorder.start(
                        self.recording_folder, self.gui_config.samplerate, mode
                    )
                except OSError as error:
                    sg.popup_error(str(error))
                    return
                self.window["toggle_recording"].update(
                    text="● REC", button_color="#c44242", hover_color="#a73535"
                )
                self.window["recording_mode"].widget.configure(state="disabled")
                self.set_run_status(ui_text("status_recording_started"))
            else:
                self.recorder.stop()
                saved_paths = getattr(self.recorder, "last_saved_paths", [])
                if saved_paths:
                    saved_name = os.path.basename(saved_paths[0])
                    self.set_run_status(
                        f"{ui_text('status_recording_saved')}: {saved_name}"
                    )
                    sg.popup(
                        (
                            "録音を保存しました。\n" + "\n".join(saved_paths)
                            if IS_JAPANESE_UI
                            else "Recording saved.\n" + "\n".join(saved_paths)
                        )
                    )
                self.window["toggle_recording"].update(
                    text=ui_text("record"),
                    button_color=("#3b8ed0", "#1f6aa5"),
                    hover_color=("#36719f", "#144870"),
                )
                self.window["recording_mode"].widget.configure(state="readonly")
                self.window["recording_status"].update("")

        def refresh_recording_status(self):
            if not self.recorder.active or self.recorder.started_at is None:
                return
            elapsed = (datetime.datetime.now() - self.recorder.started_at).total_seconds()
            total_seconds = int(elapsed)
            centiseconds = int((elapsed % 1) * 100)
            self.window["recording_status"].update(
                f"● REC {total_seconds // 3600:02}:{(total_seconds // 60) % 60:02}:{total_seconds % 60:02}:{centiseconds:02}"
            )
            return
            self.window["recording_status"].update(
                f"● REC {elapsed // 3600:02}:{(elapsed // 60) % 60:02}:{elapsed % 60:02}"
            )

        def clear_log(self):
            self.log_text = ""
            while True:
                try:
                    self.log_queue.get_nowait()
                except queue.Empty:
                    break
            self.window["log_output"].update("")

        def save_log(self):
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(logs_dir, f"RuntimeLog_{timestamp}.txt")
            try:
                os.makedirs(logs_dir, exist_ok=True)
                with open(path, "w", encoding="utf-8") as log_file:
                    log_file.write(self.log_text)
                self.set_run_status(
                    f"{ui_text('status_log_saved')}: {os.path.basename(path)}"
                )
                sg.popup(
                    (
                        f"ログを保存しました。\n{path}"
                        if IS_JAPANESE_UI
                        else f"Log saved.\n{path}"
                    )
                )
            except OSError as error:
                sg.popup_error(str(error))

        def log_startup_diagnostics(self, data):
            """Log release-relevant checks without opening any audio stream."""
            printt("=== Startup diagnostics ===")
            printt("FFmpeg bundled: %s", os.path.isfile(self.ffmpeg_path))
            printt("Models discovered: %s", len(self.model_names))
            printt("CUDA available: %s", torch.cuda.is_available())
            if torch.cuda.is_available():
                printt("CUDA devices: %s", torch.cuda.device_count())
                printt("Selected GPU: %s", data.get("gpu_device", "Automatic"))
                printt("CUDA Graph enabled: %s", cuda_graph_enabled(self.config.device))
            try:
                os.makedirs(self.recording_folder, exist_ok=True)
                printt("Recording folder writable: %s", os.access(self.recording_folder, os.W_OK))
            except OSError as error:
                printt("Recording folder unavailable: %s", error)
            printt(
                "Configured route: input=%s / output=%s / monitor=%s",
                data.get("sg_input_device", ""),
                data.get("sg_output_device", ""),
                data.get("sg_monitor_device", MONITOR_DISABLED),
            )
            printt("=== Startup diagnostics complete ===")

        def log_active_audio_route(self):
            requested_exclusive = bool(self.gui_config.sg_wasapi_exclusive)
            printt("=== Active audio route ===")
            printt(
                "Input=%s / Output=%s / Monitor=%s",
                self.gui_config.sg_input_hostapi or "File",
                self.gui_config.sg_output_hostapi,
                self.gui_config.sg_monitor_hostapi or "Disabled",
            )
            printt(
                "Rate=%s Hz / Chunk=%.3f sec / WASAPI exclusive requested=%s",
                self.gui_config.samplerate,
                self.gui_config.block_time,
                requested_exclusive,
            )
            printt(
                "WASAPI exclusive active: input=%s output=%s monitor=%s",
                self.input_wasapi_settings is not None,
                self.output_wasapi_settings is not None,
                self.monitor_wasapi_settings is not None,
            )
            if self.gui_config.sg_input_hostapi == "ASIO" or self.gui_config.sg_output_hostapi == "ASIO":
                printt(
                    "ASIO selectors: input=%s output=%s monitor=%s",
                    self.asio_input_selectors,
                    self.asio_output_selectors,
                    self.asio_monitor_selectors,
                )
            printt("=== Active audio route complete ===")

        def restore_console_streams(self):
            if sys.stdout is not self.original_stdout:
                sys.stdout = self.original_stdout
            if sys.stderr is not self.original_stderr:
                sys.stderr = self.original_stderr

        def save_config_updates(self, updates):
            try:
                data = json.loads(read_text(realtime_config_path))
            except Exception:
                data = {}
            data.update(updates)
            # GENERAL SETTINGS are stored beside each model.  Drop legacy
            # global copies whenever the shared UI configuration is updated.
            for key in MODEL_GENERAL_SETTING_KEYS:
                data.pop(key, None)
            data.pop("file_input_path", None)
            with open(realtime_config_path, "w", encoding="utf8") as config_file:
                json.dump(data, config_file, ensure_ascii=False)

        def reset_general_settings(self):
            for key in (
                "input_gain_db",
                "output_gain_db",
                "monitor_gain_db",
                "threhold",
                "pitch",
                "formant",
                "index_rate",
            ):
                self.window[key].update(GENERAL_DEFAULTS[key])
            self.gui_config.input_gain_db = GENERAL_DEFAULTS["input_gain_db"]
            self.gui_config.output_gain_db = GENERAL_DEFAULTS["output_gain_db"]
            self.gui_config.monitor_gain_db = GENERAL_DEFAULTS["monitor_gain_db"]
            self.gui_config.input_gain = db_to_linear(
                GENERAL_DEFAULTS["input_gain_db"]
            )
            self.gui_config.output_gain = db_to_linear(
                GENERAL_DEFAULTS["output_gain_db"]
            )
            self.gui_config.monitor_gain = db_to_linear(
                GENERAL_DEFAULTS["monitor_gain_db"]
            )
            self.gui_config.threhold = GENERAL_DEFAULTS["threhold"]
            self.gui_config.pitch = GENERAL_DEFAULTS["pitch"]
            self.gui_config.formant = GENERAL_DEFAULTS["formant"]
            self.gui_config.index_rate = GENERAL_DEFAULTS["index_rate"]

            if hasattr(self, "rvc"):
                self.rvc.change_key(GENERAL_DEFAULTS["pitch"])
                self.rvc.change_formant(GENERAL_DEFAULTS["formant"])
                self.rvc.change_index_rate(GENERAL_DEFAULTS["index_rate"])
            self.save_model_general_settings(self.window["model_name"].get())

        def reset_performance_settings(self):
            self.stop_stream()
            self.window["block_time"].update(PERFORMANCE_DEFAULTS["block_time"])
            self.window["crossfade_length"].update(
                PERFORMANCE_DEFAULTS["crossfade_length"]
            )
            self.window["extra_time"].update(PERFORMANCE_DEFAULTS["extra_time"])
            self.window["rms_mix_rate"].update(GENERAL_DEFAULTS["rms_mix_rate"])
            self.window["I_noise_reduce"].update(
                PERFORMANCE_DEFAULTS["I_noise_reduce"]
            )
            self.window["O_noise_reduce"].update(
                PERFORMANCE_DEFAULTS["O_noise_reduce"]
            )
            self.window["pm"].update(False)
            self.window["rmvpe"].update(True)
            self.window["fcpe"].update(False)

            self.gui_config.block_time = PERFORMANCE_DEFAULTS["block_time"]
            self.gui_config.crossfade_time = PERFORMANCE_DEFAULTS[
                "crossfade_length"
            ]
            self.gui_config.extra_time = PERFORMANCE_DEFAULTS["extra_time"]
            self.gui_config.rms_mix_rate = GENERAL_DEFAULTS["rms_mix_rate"]
            self.gui_config.I_noise_reduce = PERFORMANCE_DEFAULTS[
                "I_noise_reduce"
            ]
            self.gui_config.O_noise_reduce = PERFORMANCE_DEFAULTS[
                "O_noise_reduce"
            ]
            self.gui_config.f0method = GENERAL_DEFAULTS["f0method"]
            self.save_config_updates(
                {
                    **PERFORMANCE_DEFAULTS,
                    "rms_mix_rate": GENERAL_DEFAULTS["rms_mix_rate"],
                    "f0method": GENERAL_DEFAULTS["f0method"],
                }
            )
            self.set_run_status(ui_text("status_settings_changed"))

        def event_handler(self):
            global flag_vc
            while True:
                event, values = self.window.read(timeout=100)
                self.drain_log_queue()
                self.flush_model_general_settings_save()
                if event == sg.TIMEOUT_EVENT:
                    if flag_vc:
                        self.refresh_realtime_indicators()
                        self.refresh_recording_status()
                        duplex_active = (
                            self.stream is not None
                            and self.stream is not self.output_stream
                            and bool(getattr(self.stream, "active", False))
                        )
                        split_active = (
                            self.input_stream is not None
                            and self.output_stream is not None
                            and bool(getattr(self.input_stream, "active", False))
                            and bool(getattr(self.output_stream, "active", False))
                        )
                        # File input deliberately owns no PortAudio input
                        # stream: decoded blocks are fed into audio_callback
                        # by FileAudioSource.  The former two checks therefore
                        # treated every valid file conversion as an unexpected
                        # stop on the next GUI timer tick.
                        file_output_active = (
                            self.file_source_active
                            and self.output_stream is not None
                            and bool(getattr(self.output_stream, "active", False))
                        )
                        if not duplex_active and not split_active and not file_output_active:
                            printt(
                                "Audio stream stopped unexpectedly; "
                                "returning to the idle state."
                            )
                            self.stop_stream()
                    self.refresh_file_playback_ui()
                    continue
                if event == sg.WINDOW_CLOSED:
                    self.flush_model_general_settings_save(force=True)
                    self.save_window_position()
                    self.stop_stream()
                    self.restore_console_streams()
                    self.window.close()
                    exit()
                if event == "clear_log":
                    self.clear_log()
                    continue
                if event == "save_log":
                    self.save_log()
                    continue
                if event == "toggle_runtime_log":
                    self.log_visible = not self.log_visible
                    self.window["runtime_log_frame"].update(
                        visible=self.log_visible
                    )
                    self.window["toggle_runtime_log"].update(
                        text=ui_text(
                            "hide_runtime_log"
                            if self.log_visible
                            else "runtime_log"
                        )
                    )
                    self.resize_main_window()
                    if self.log_visible:
                        self.window["log_output"].update(self.log_text)
                    continue
                if event == "toggle_model_selector":
                    self.toggle_model_selector()
                    continue
                if event == "toggle_theme":
                    self.toggle_theme()
                    continue
                if event == "input_source":
                    self.stop_stream()
                    self.update_file_input_ui(
                        values.get("input_source") == INPUT_SOURCE_FILE
                    )
                    self.set_run_status(ui_text("status_settings_changed"))
                    self.save_config_updates(
                        {"input_source": values.get("input_source", INPUT_SOURCE_MICROPHONE)}
                    )
                    continue
                if event == "browse_audio_file":
                    self.choose_file_input()
                    continue
                if event == "play_audio_file":
                    self.start_file_playback()
                    continue
                if event == "pause_audio_file":
                    self.pause_file_playback()
                    continue
                if event == "stop_audio_file":
                    self.stop_file_playback(announce=True)
                    continue
                if event == "file_seek":
                    self.seek_file_playback(values.get("file_seek", 0))
                    continue
                if event == "file_input_volume":
                    self.file_input_volume = float(
                        values.get("file_input_volume", 100.0)
                    ) / 100.0
                    self.save_config_updates({"file_input_volume": self.file_input_volume})
                    continue
                if event == "change_recording_folder":
                    folder = sg.choose_folder(self.recording_folder)
                    if folder:
                        self.recording_folder = folder
                        self.save_config_updates({"recording_folder": folder})
                    continue
                if event == "open_recording_folder":
                    os.makedirs(self.recording_folder, exist_ok=True)
                    os.startfile(self.recording_folder)
                    continue
                if event == "toggle_recording":
                    self.set_recording(not self.recorder.active, values)
                    continue
                if event in (
                    "reload_devices",
                    "sg_input_device",
                    "sg_output_device",
                    "sg_monitor_device",
                ):
                    self.stop_stream()
                    self.gui_config.sg_input_device = values.get(
                        "sg_input_device", ""
                    )
                    self.gui_config.sg_output_device = values.get(
                        "sg_output_device", ""
                    )
                    self.gui_config.sg_monitor_device = values.get(
                        "sg_monitor_device", MONITOR_DISABLED
                    )
                    if event == "reload_devices":
                        self.update_devices(show_legacy=False)
                    if (
                        self.gui_config.sg_input_device not in self.input_devices
                        and len(self.input_devices) > 0
                    ):
                        self.gui_config.sg_input_device = self.input_devices[0]
                    self.window["sg_input_device"].Update(values=self.input_devices)
                    self.window["sg_input_device"].Update(
                        value=self.gui_config.sg_input_device
                    )
                    if self.gui_config.sg_output_device not in self.output_devices:
                        self.gui_config.sg_output_device = self.output_devices[0]
                    self.window["sg_output_device"].Update(values=self.output_devices)
                    self.window["sg_output_device"].Update(
                        value=self.gui_config.sg_output_device
                    )
                    if (
                        self.gui_config.sg_monitor_device
                        not in self.output_devices
                    ):
                        self.gui_config.sg_monitor_device = MONITOR_DISABLED
                    self.window["sg_monitor_device"].Update(
                        values=[MONITOR_DISABLED] + self.output_devices,
                        value=self.gui_config.sg_monitor_device,
                    )
                    values["sg_input_device"] = self.gui_config.sg_input_device
                    values["sg_output_device"] = self.gui_config.sg_output_device
                    values["sg_monitor_device"] = self.gui_config.sg_monitor_device
                    self.configure_audio_ui(values)
                    self.set_run_status(ui_text("status_settings_changed"))
                if event == "reload_models":
                    self.flush_model_general_settings_save(force=True)
                    previous_model = values.get("model_name", "")
                    self.refresh_models()
                    selected_model = (
                        previous_model
                        if previous_model in self.models_by_name
                        else (self.model_names[0] if self.model_names else "")
                    )
                    self.window["model_name"].Update(values=self.model_names)
                    self.update_selected_model_ui(selected_model)
                    self.apply_model_general_settings(selected_model)
                elif event == "model_name":
                    self.flush_model_general_settings_save(force=True)
                    selected_model = values.get("model_name", "")
                    self.update_selected_model_ui(
                        selected_model, refresh_gallery=False
                    )
                    self.apply_model_general_settings(selected_model)
                elif event in self.model_card_events:
                    self.flush_model_general_settings_save(force=True)
                    selected_model = self.model_card_events[event]
                    values["model_name"] = selected_model
                    self.update_selected_model_ui(
                        selected_model, refresh_gallery=False
                    )
                    self.apply_model_general_settings(selected_model)
                if event in ("start_vc", "audio_passthrough"):
                    requested_function = (
                        "im" if event == "audio_passthrough" else "vc"
                    )
                    if flag_vc and self.function == requested_function:
                        self.stop_stream()
                        self.set_run_status(
                            ui_text(
                                "status_passthrough_stopped"
                                if requested_function == "im"
                                else "status_conversion_stopped"
                            )
                        )
                        continue
                    if flag_vc:
                        self.stop_stream()
                    self.function = requested_function
                    self.set_run_status(
                        "起動準備中…" if IS_JAPANESE_UI else "Preparing…"
                    )
                    if self.set_values(values) == True:
                        printt("CUDA available: %s", torch.cuda.is_available())
                        try:
                            self.start_vc()
                        except Exception as error:
                            printt(traceback.format_exc())
                            self.stop_stream()
                            self.set_run_status(ui_text("status_audio_error"))
                            sg.popup_error(
                                (
                                    "音声デバイスを開始できませんでした。\n\n"
                                    if IS_JAPANESE_UI
                                    else "Could not start the audio devices.\n\n"
                                )
                                + str(error)
                            )
                            continue
                        self.set_run_status(
                            ui_text(
                                "status_passthrough_started"
                                if requested_function == "im"
                                else "status_conversion_started"
                            )
                        )
                        self.update_run_buttons()
                    else:
                        self.set_run_status(ui_text("status_audio_error"))
                    if flag_vc:
                        settings = {
                            "model_name": values["model_name"],
                            "recording_folder": self.recording_folder,
                            "recording_mode": values.get(
                                "recording_mode", ui_text("recording_separate")
                            ),
                            "input_source": values.get("input_source", INPUT_SOURCE_MICROPHONE),
                            "file_input_volume": self.file_input_volume,
                            "model_selector_mode": "list" if self.model_gallery_visible else "combo",
                            "theme_mode": self.theme_mode,
                            "gpu_device": values["gpu_device"],
                            "sg_wasapi_exclusive": values["sg_wasapi_exclusive"],
                            "sg_show_legacy_devices": False,
                            "sg_input_device": values["sg_input_device"],
                            "sg_output_device": values["sg_output_device"],
                            "sg_monitor_device": values["sg_monitor_device"],
                            "sr_type": "auto",
                            "rms_mix_rate": values["rms_mix_rate"],
                            # "device_latency": values["device_latency"],
                            "block_time": values["block_time"],
                            "crossfade_length": values["crossfade_length"],
                            "extra_time": values["extra_time"],
                            "I_noise_reduce": values["I_noise_reduce"],
                            "O_noise_reduce": values["O_noise_reduce"],
                            "f0method": ["pm", "rmvpe", "fcpe"][
                                [values["pm"], values["rmvpe"], values["fcpe"]].index(True)
                            ],
                        }
                        with open(realtime_config_path, "w", encoding="utf8") as j:
                            json.dump(settings, j)
                        if self.stream is not None:
                            stream_latency = self.stream.latency
                            if isinstance(stream_latency, (tuple, list)):
                                stream_latency = stream_latency[-1]
                            self.delay_time = (
                                stream_latency
                                + values["block_time"]
                                + values["crossfade_length"]
                                + 0.01
                            )
                        if values["I_noise_reduce"]:
                            self.delay_time += min(values["crossfade_length"], 0.04)
                        self.window["sr_stream"].update(
                            f"{self.gui_config.samplerate:,} Hz"
                        )
                        self.window["delay_time"].update(
                            int(np.round(self.delay_time * 1000))
                        )
                # Parameter hot update
                if event == "threhold":
                    self.gui_config.threhold = values["threhold"]
                elif event == "input_gain_db":
                    self.gui_config.input_gain_db = values["input_gain_db"]
                    self.gui_config.input_gain = db_to_linear(values["input_gain_db"])
                elif event == "output_gain_db":
                    self.gui_config.output_gain_db = values["output_gain_db"]
                    self.gui_config.output_gain = db_to_linear(values["output_gain_db"])
                elif event == "monitor_gain_db":
                    self.gui_config.monitor_gain_db = values["monitor_gain_db"]
                    self.gui_config.monitor_gain = db_to_linear(
                        values["monitor_gain_db"]
                    )
                elif event == "pitch":
                    self.gui_config.pitch = values["pitch"]
                    if hasattr(self, "rvc"):
                        self.rvc.change_key(values["pitch"])
                elif event == "formant":
                    self.gui_config.formant = values["formant"]
                    if hasattr(self, "rvc"):
                        self.rvc.change_formant(values["formant"])
                elif event == "index_rate":
                    self.gui_config.index_rate = values["index_rate"]
                    if hasattr(self, "rvc"):
                        self.rvc.change_index_rate(values["index_rate"])
                elif event == "rms_mix_rate":
                    self.gui_config.rms_mix_rate = values["rms_mix_rate"]
                elif event in ["pm", "rmvpe", "fcpe"]:
                    self.gui_config.f0method = event
                elif event == "I_noise_reduce":
                    self.gui_config.I_noise_reduce = values["I_noise_reduce"]
                    if self.stream is not None:
                        self.delay_time += (
                            1 if values["I_noise_reduce"] else -1
                        ) * min(values["crossfade_length"], 0.04)
                        self.window["delay_time"].update(
                            int(np.round(self.delay_time * 1000))
                        )
                elif event == "O_noise_reduce":
                    self.gui_config.O_noise_reduce = values["O_noise_reduce"]
                elif event == "reset_general_settings":
                    self.reset_general_settings()
                elif event == "reset_performance_settings":
                    self.reset_performance_settings()
                elif event not in (
                    "start_vc",
                    "audio_passthrough",
                ):
                    # Other parameters do not support hot update
                    self.stop_stream()
                    self.set_run_status(ui_text("status_settings_changed"))

                if event in MODEL_GENERAL_SETTING_KEYS:
                    self.schedule_model_general_settings_save()

        def set_values(self, values):
            # Use the actual control value at start time.  This also keeps
            # startup robust if the source-selection event is still queued.
            self.file_source_active = (
                values.get("input_source") == INPUT_SOURCE_FILE
            )
            model_name = values.get("model_name", "")
            model = self.models_by_name.get(model_name)
            if model is None:
                sg.popup(
                    "modelsフォルダー内のモデルを選択してください"
                    if IS_JAPANESE_UI
                    else "Select a model from the models folder."
                )
                return False
            if not model.model_path.is_file():
                prefix = (
                    "モデルファイルが見つかりません"
                    if IS_JAPANESE_UI
                    else "Model file not found"
                )
                sg.popup(f"{prefix}: {model.model_path}")
                return False
            if values["index_rate"] > 0 and model.index_path is None:
                sg.popup(
                    (
                        "選択したモデルに.indexファイルがありません。"
                        "Index Rateを0にするか、モデルフォルダーへ.indexを追加してください。"
                    )
                    if IS_JAPANESE_UI
                    else (
                        "The selected model has no .index file. "
                        "Set Index to 0 or add an .index file to its model folder."
                    )
                )
                return False
            try:
                self.apply_selected_gpu(values["gpu_device"])
            except ValueError as error:
                sg.popup_error(str(error))
                return False
            if values.get("input_source") == INPUT_SOURCE_FILE:
                if not self.file_input_path:
                    sg.popup(
                        "音声ファイルを選択してください。"
                        if IS_JAPANESE_UI
                        else "Select an audio file first."
                    )
                    return False
                if not os.path.isfile(self.ffmpeg_path):
                    sg.popup_error(
                        "同梱FFmpegが見つかりません。"
                        if IS_JAPANESE_UI
                        else "Bundled FFmpeg was not found."
                    )
                    return False
            try:
                self.set_devices(
                    values["sg_input_device"],
                    values["sg_output_device"],
                    values["sg_monitor_device"],
                )
            except ValueError as error:
                sg.popup_error(str(error))
                return False
            # self.device_latency = values["device_latency"]
            self.gui_config.sg_wasapi_exclusive = bool(
                values["sg_wasapi_exclusive"]
            )
            self.gui_config.show_legacy_devices = False
            self.gui_config.sg_input_device = values["sg_input_device"]
            self.gui_config.sg_output_device = values["sg_output_device"]
            self.gui_config.sg_monitor_device = values["sg_monitor_device"]
            self.gui_config.model_name = model.name
            self.gui_config.pth_path = str(model.model_path)
            self.gui_config.index_path = (
                str(model.index_path) if model.index_path is not None else ""
            )
            self.gui_config.sr_type = "auto"
            self.gui_config.threhold = values["threhold"]
            self.gui_config.pitch = values["pitch"]
            self.gui_config.formant = values["formant"]
            self.gui_config.block_time = values["block_time"]
            self.gui_config.crossfade_time = values["crossfade_length"]
            self.gui_config.extra_time = values["extra_time"]
            self.gui_config.I_noise_reduce = values["I_noise_reduce"]
            self.gui_config.O_noise_reduce = values["O_noise_reduce"]
            self.gui_config.rms_mix_rate = values["rms_mix_rate"]
            self.gui_config.index_rate = values["index_rate"]
            self.gui_config.input_gain_db = values["input_gain_db"]
            self.gui_config.output_gain_db = values["output_gain_db"]
            self.gui_config.monitor_gain_db = values["monitor_gain_db"]
            self.gui_config.input_gain = db_to_linear(values["input_gain_db"])
            self.gui_config.output_gain = db_to_linear(values["output_gain_db"])
            self.gui_config.monitor_gain = db_to_linear(
                values["monitor_gain_db"]
            )
            self.gui_config.f0method = ["pm", "rmvpe", "fcpe"][
                [values["pm"], values["rmvpe"], values["fcpe"]].index(True)
            ]
            return True

        def start_vc(self):
            self.set_run_status(
                "モデルを読み込んでいます…"
                if IS_JAPANESE_UI
                else "Loading model…"
            )
            torch.cuda.empty_cache()
            self.rvc = rvc_for_realtime.RVC(
                self.gui_config.pitch,
                self.gui_config.formant,
                self.gui_config.pth_path,
                self.gui_config.index_path,
                self.gui_config.index_rate,
                self.config,
                self.rvc if hasattr(self, "rvc") else None,
            )
            # Decoded files are always supplied as mono float32 blocks.
            # Do not inherit a disabled or ASIO input endpoint's channel
            # layout when the input source is a file.
            self.gui_config.channels = (
                1 if self.file_source_active else self.get_device_channels()
            )
            self.gui_config.output_channels = self.get_output_channels()
            self.gui_config.samplerate = self.get_automatic_samplerate(
                self.rvc.tgt_sr
            )
            self.zc = self.gui_config.samplerate // 100
            self.block_frame = (
                int(
                    np.round(
                        self.gui_config.block_time
                        * self.gui_config.samplerate
                        / self.zc
                    )
                )
                * self.zc
            )
            self.block_frame_16k = 160 * self.block_frame // self.zc
            self.crossfade_frame = (
                int(
                    np.round(
                        self.gui_config.crossfade_time
                        * self.gui_config.samplerate
                        / self.zc
                    )
                )
                * self.zc
            )
            self.sola_buffer_frame = min(self.crossfade_frame, 4 * self.zc)
            self.sola_search_frame = self.zc
            self.extra_frame = (
                int(
                    np.round(
                        self.gui_config.extra_time
                        * self.gui_config.samplerate
                        / self.zc
                    )
                )
                * self.zc
            )
            self.input_wav = torch.zeros(
                self.extra_frame
                + self.crossfade_frame
                + self.sola_search_frame
                + self.block_frame,
                device=self.config.device,
                dtype=torch.float32,
            )
            self.input_wav_denoise = self.input_wav.clone()
            self.input_wav_res = torch.zeros(
                160 * self.input_wav.shape[0] // self.zc,
                device=self.config.device,
                dtype=torch.float32,
            )
            self.rms_buffer = np.zeros(4 * self.zc, dtype="float32")
            self.sola_buffer = torch.zeros(
                self.sola_buffer_frame, device=self.config.device, dtype=torch.float32
            )
            self.sola_den_kernel = torch.ones(
                1,
                1,
                self.sola_buffer_frame,
                device=self.config.device,
                dtype=torch.float32,
            )
            self.nr_buffer = self.sola_buffer.clone()
            self.output_buffer = self.input_wav.clone()
            self.skip_head = self.extra_frame // self.zc
            self.return_length = (
                self.block_frame + self.sola_buffer_frame + self.sola_search_frame
            ) // self.zc
            self.fade_in_window = (
                torch.sin(
                    0.5
                    * np.pi
                    * torch.linspace(
                        0.0,
                        1.0,
                        steps=self.sola_buffer_frame,
                        device=self.config.device,
                        dtype=torch.float32,
                    )
                )
                ** 2
            )
            self.fade_out_window = 1 - self.fade_in_window
            self.resampler = tat.Resample(
                orig_freq=self.gui_config.samplerate,
                new_freq=16000,
                dtype=torch.float32,
            ).to(self.config.device)
            if self.rvc.tgt_sr != self.gui_config.samplerate:
                self.resampler2 = tat.Resample(
                    orig_freq=self.rvc.tgt_sr,
                    new_freq=self.gui_config.samplerate,
                    dtype=torch.float32,
                ).to(self.config.device)
            else:
                self.resampler2 = None
            self.tg = TorchGate(
                sr=self.gui_config.samplerate, n_fft=4 * self.zc, prop_decrease=0.9
            ).to(self.config.device)
            self.set_run_status(
                "推論を準備しています…"
                if IS_JAPANESE_UI
                else "Preparing inference…"
            )
            self.prewarm_cuda_graph()
            self.set_run_status(
                "音声デバイスを開始しています…"
                if IS_JAPANESE_UI
                else "Starting audio devices…"
            )
            if self.output_stream is not None:
                self.stop_stream()
            self.start_stream()

        def prewarm_cuda_graph(self):
            if not cuda_graph_enabled(self.config.device):
                return
            try:
                samples = self.input_wav_res.shape[0]
                phase = torch.arange(
                    samples, device=self.config.device, dtype=torch.float32
                )
                probe = 0.05 * torch.sin(2 * np.pi * 220.0 * phase / 16000.0)
                self.input_wav_res.copy_(probe)

                if self.gui_config.I_noise_reduce:
                    short = self.input_wav[
                        -self.sola_buffer_frame - self.block_frame :
                    ].unsqueeze(0)
                    self.tg(short, self.input_wav.unsqueeze(0))

                resample_input = self.input_wav[-self.block_frame - 2 * self.zc :]
                run_cuda_graph(
                    self.resampler,
                    "realtime-input-resample",
                    lambda audio: self.resampler(audio),
                    resample_input,
                )

                inferred = self.rvc.infer(
                    self.input_wav_res,
                    self.block_frame_16k,
                    self.skip_head,
                    self.return_length,
                    self.gui_config.f0method,
                )
                if self.resampler2 is not None:
                    inferred = run_cuda_graph(
                        self.resampler2,
                        "realtime-output-resample",
                        lambda audio: self.resampler2(audio),
                        inferred,
                    )
                if self.gui_config.O_noise_reduce:
                    self.tg(inferred.unsqueeze(0), self.output_buffer.unsqueeze(0))
                torch.cuda.synchronize(self.config.device)
            except Exception:
                printt(traceback.format_exc())
            finally:
                self.input_wav.zero_()
                self.input_wav_denoise.zero_()
                self.input_wav_res.zero_()
                self.output_buffer.zero_()
                self.sola_buffer.zero_()
                self.nr_buffer.zero_()
                self.rvc.cache_pitch.zero_()
                self.rvc.cache_pitchf.zero_()

        def start_stream(self):
            global flag_vc
            if not flag_vc:
                flag_vc = True
                self.log_active_audio_route()
                if self.file_source_active:
                    self.start_file_stream()
                    return
                if self.gui_config.sg_input_hostapi == "ASIO":
                    self.start_asio_input_route()
                    return

                input_extra = None
                output_extra = None
                input_channels = self.gui_config.channels
                output_channels = self.gui_config.output_channels
                if (
                    "WASAPI" in self.gui_config.sg_input_hostapi
                    and self.gui_config.sg_wasapi_exclusive
                ):
                    input_extra = self.input_wasapi_settings
                if self.gui_config.sg_output_hostapi == "ASIO":
                    output_selectors = (
                        self.asio_output_selectors + self.asio_monitor_selectors
                    )
                    output_extra = sd.AsioSettings(
                        channel_selectors=output_selectors
                    )
                    output_channels = len(output_selectors)
                elif (
                    "WASAPI" in self.gui_config.sg_output_hostapi
                    and self.gui_config.sg_wasapi_exclusive
                ):
                    output_extra = self.output_wasapi_settings
                self.output_queue = (
                    AudioFrameFifo(1, max_frames=self.block_frame * 4)
                    if self.gui_config.sg_output_hostapi == "ASIO"
                    else queue.Queue(maxsize=3)
                )
                self.output_stream = sd.OutputStream(
                    callback=self.output_audio_callback,
                    blocksize=(
                        0
                        if self.gui_config.sg_output_hostapi == "ASIO"
                        else self.block_frame
                    ),
                    samplerate=self.gui_config.samplerate,
                    channels=output_channels,
                    device=sd.default.device[1],
                    dtype="float32",
                    extra_settings=output_extra,
                )
                self.input_stream = sd.InputStream(
                    callback=self.audio_callback,
                    blocksize=self.block_frame,
                    samplerate=self.gui_config.samplerate,
                    channels=input_channels,
                    device=sd.default.device[0],
                    dtype="float32",
                    extra_settings=input_extra,
                )
                self.output_stream.start()
                self.input_stream.start()
                self.stream = self.output_stream
                if self.gui_config.sg_monitor_hostapi != "ASIO":
                    self.start_monitor_stream()

        def start_file_stream(self):
            """Start only the output side; file decoding feeds audio_callback."""
            output_extra = None
            output_channels = self.gui_config.output_channels
            if self.gui_config.sg_output_hostapi == "ASIO":
                selectors = self.asio_output_selectors + self.asio_monitor_selectors
                output_extra = sd.AsioSettings(channel_selectors=selectors)
                output_channels = len(selectors)
            elif (
                "WASAPI" in self.gui_config.sg_output_hostapi
                and self.gui_config.sg_wasapi_exclusive
            ):
                output_extra = self.output_wasapi_settings
            # Match the ordinary microphone/WASAPI path.  ASIO still needs a
            # frame FIFO because its callback size is driver-owned; all other
            # output paths use the same bounded block queue as microphone
            # conversion.
            self.output_queue = (
                AudioFrameFifo(1, max_frames=self.block_frame * 4)
                if self.gui_config.sg_output_hostapi == "ASIO"
                else queue.Queue(maxsize=3)
            )
            self.output_stream = sd.OutputStream(
                callback=self.output_audio_callback,
                blocksize=0 if self.gui_config.sg_output_hostapi == "ASIO" else self.block_frame,
                samplerate=self.gui_config.samplerate,
                channels=output_channels,
                device=sd.default.device[1],
                dtype="float32",
                extra_settings=output_extra,
            )
            self.output_stream.start()
            self.stream = self.output_stream
            if self.gui_config.sg_monitor_hostapi != "ASIO":
                self.start_monitor_stream()

        def start_asio_input_route(self):
            """Keep ASIO's native callback size separate from the RVC chunk."""
            input_device = sd.default.device[0]
            output_on_asio = self.gui_config.sg_output_hostapi == "ASIO"
            monitor_uses_asio_driver = (
                self.gui_config.sg_monitor_hostapi == "ASIO"
            )
            monitor_on_asio = (
                monitor_uses_asio_driver and bool(self.asio_monitor_selectors)
            )
            if output_on_asio and sd.default.device[1] != input_device:
                raise ValueError(
                    "Native ASIO input and output must use the same ASIO driver. "
                    "Use a Windows/WASAPI endpoint for mixed-driver output."
                )
            if (
                monitor_uses_asio_driver
                and self.monitor_device_index != input_device
            ):
                raise ValueError(
                    "Native ASIO input and monitor must use the same ASIO driver."
                )

            self.asio_duplex_main_channels = (
                len(self.asio_output_selectors) if output_on_asio else 0
            )
            self.asio_duplex_monitor_channels = (
                len(self.asio_monitor_selectors) if monitor_on_asio else 0
            )
            output_selectors = []
            if output_on_asio:
                output_selectors.extend(self.asio_output_selectors)
            if monitor_on_asio:
                output_selectors.extend(self.asio_monitor_selectors)

            # These are capacity limits, not an added latency preset.  ASIO
            # callbacks feed their native 64/128/256-frame blocks into the
            # input FIFO; the worker consumes exact RVC chunks.
            fifo_capacity = self.block_frame * 4
            self.asio_input_fifo = AudioFrameFifo(
                len(self.asio_input_selectors), max_frames=fifo_capacity
            )
            self.output_queue = AudioFrameFifo(1, max_frames=fifo_capacity)
            self.monitor_queue = (
                AudioFrameFifo(1, max_frames=fifo_capacity)
                if self.monitor_device_index is not None
                else None
            )
            self.asio_worker_stop = threading.Event()
            self.asio_worker_wakeup = threading.Event()
            self.asio_worker = threading.Thread(
                target=self.asio_inference_worker,
                name="rvc-asio-inference",
                daemon=True,
            )

            if not output_on_asio:
                output_extra = (
                    self.output_wasapi_settings
                    if (
                        "WASAPI" in self.gui_config.sg_output_hostapi
                        and self.gui_config.sg_wasapi_exclusive
                    )
                    else None
                )
                self.output_stream = sd.OutputStream(
                    callback=self.output_audio_callback,
                    blocksize=0,
                    samplerate=self.gui_config.samplerate,
                    channels=self.gui_config.output_channels,
                    device=sd.default.device[1],
                    dtype="float32",
                    extra_settings=output_extra,
                )
                self.output_stream.start()

            if not monitor_uses_asio_driver:
                self.start_monitor_stream()

            if output_selectors:
                self.input_stream = sd.Stream(
                    callback=self.asio_fifo_duplex_callback,
                    blocksize=0,
                    samplerate=self.gui_config.samplerate,
                    channels=(len(self.asio_input_selectors), len(output_selectors)),
                    device=(input_device, input_device),
                    dtype="float32",
                    extra_settings=(
                        sd.AsioSettings(
                            channel_selectors=self.asio_input_selectors
                        ),
                        sd.AsioSettings(channel_selectors=output_selectors),
                    ),
                )
            else:
                self.input_stream = sd.InputStream(
                    callback=self.asio_fifo_input_callback,
                    blocksize=0,
                    samplerate=self.gui_config.samplerate,
                    channels=len(self.asio_input_selectors),
                    device=input_device,
                    dtype="float32",
                    extra_settings=sd.AsioSettings(
                        channel_selectors=self.asio_input_selectors
                    ),
                )
            self.asio_worker.start()
            self.input_stream.start()
            self.stream = self.input_stream

        def asio_inference_worker(self):
            while not self.asio_worker_stop.is_set():
                self.asio_worker_wakeup.wait(0.05)
                self.asio_worker_wakeup.clear()
                while not self.asio_worker_stop.is_set():
                    input_block = self.asio_input_fifo.read(
                        self.block_frame, exact=True
                    )
                    if input_block is None:
                        break
                    try:
                        self.audio_callback(
                            input_block, self.block_frame, None, None
                        )
                    except Exception:
                        printt(traceback.format_exc())
                        self.asio_worker_stop.set()
                        return

        def asio_fifo_input_callback(self, indata, frames, times, status):
            self.asio_input_fifo.write(indata)
            self.asio_worker_wakeup.set()

        def asio_fifo_duplex_callback(self, indata, outdata, frames, times, status):
            outdata.fill(0)
            main = self.read_audio_target(self.output_queue, frames)
            monitor = self.read_audio_target(self.monitor_queue, frames)
            main_channels = self.asio_duplex_main_channels
            monitor_channels = self.asio_duplex_monitor_channels
            if main is not None and main_channels:
                outdata[: main.shape[0], :main_channels] = main[:, :1]
            if monitor is not None and monitor_channels:
                start = main_channels
                outdata[: monitor.shape[0], start : start + monitor_channels] = (
                    monitor[:, :1]
                )
            # Record the block that is actually delivered to the output driver,
            # not the earlier inference result.  That keeps its real buffering
            # delay relative to the input timeline.
            if main is None:
                self.recorder.enqueue("output", np.zeros(frames, dtype=np.float32))
            else:
                self.recorder.enqueue("output", main[:, 0])
            self.asio_input_fifo.write(indata)
            self.asio_worker_wakeup.set()

        def output_audio_callback(self, outdata, frames, times, status):
            block = self.read_audio_target(self.output_queue, frames)
            self.write_output_block(outdata, block)
            # Use the real device callback timeline for recording.  The output
            # can be delayed by RVC's buffers, which is intentionally preserved.
            if block is None:
                self.recorder.enqueue("output", np.zeros(frames, dtype=np.float32))
            else:
                self.recorder.enqueue("output", block[:, 0])

        @staticmethod
        def read_audio_target(target, frames):
            if target is None:
                return None
            if isinstance(target, AudioFrameFifo):
                return target.read(frames)
            try:
                block = target.get_nowait()
            except queue.Empty:
                return None
            if block.ndim == 1:
                block = block[:, None]
            return block

        def write_output_block(self, outdata, block):
            outdata.fill(0)
            if block is None:
                return
            sample_count = min(outdata.shape[0], block.shape[0])
            main_channels = (
                len(self.asio_output_selectors)
                if self.gui_config.sg_output_hostapi == "ASIO"
                else outdata.shape[1]
            )
            mono = block[:sample_count, 0] if block.ndim == 2 else block[:sample_count]
            outdata[:sample_count, :main_channels] = mono[:, None]
            if outdata.shape[1] > main_channels:
                outdata[:sample_count, main_channels:] = (
                    mono[:, None] * self.gui_config.monitor_gain
                )

        def write_monitor_block(self, outdata, block):
            outdata.fill(0)
            if block is None:
                return
            sample_count = min(outdata.shape[0], block.shape[0])
            mono = block[:sample_count, 0] if block.ndim == 2 else block[:sample_count]
            outdata[:sample_count, :] = mono[:, None]

        def start_monitor_stream(self):
            self.monitor_stream = None
            if self.monitor_device_index is None:
                self.monitor_queue = None
                return

            try:
                monitor_extra = (
                    self.monitor_wasapi_settings
                    if (
                        "WASAPI" in self.gui_config.sg_monitor_hostapi
                        and self.gui_config.sg_wasapi_exclusive
                    )
                    else None
                )
                device_info = sd.query_devices(self.monitor_device_index)
                self.monitor_channels = min(
                    int(device_info["max_output_channels"]),
                    2,
                )
                sd.check_output_settings(
                    device=self.monitor_device_index,
                    channels=self.monitor_channels,
                    dtype="float32",
                    samplerate=self.gui_config.samplerate,
                    extra_settings=monitor_extra,
                )
                self.monitor_queue = AudioFrameFifo(
                    1, max_frames=self.block_frame * 4
                )
                self.monitor_stream = sd.OutputStream(
                    device=self.monitor_device_index,
                    callback=self.monitor_audio_callback,
                    blocksize=0,
                    samplerate=self.gui_config.samplerate,
                    channels=self.monitor_channels,
                    dtype="float32",
                    extra_settings=monitor_extra,
                )
                self.monitor_stream.start()
            except Exception as error:
                if self.monitor_stream is not None:
                    self.monitor_stream.close()
                self.monitor_stream = None
                self.monitor_queue = None
                sg.popup_error(
                    "モニターデバイスを開始できませんでした。"
                    "通常の出力のみで続行します。\n\n"
                    f"{error}"
                )

        def monitor_audio_callback(self, outdata, frames, times, status):
            outdata.fill(0)
            block = self.read_audio_target(self.monitor_queue, frames)
            if block is None:
                return
            sample_count = min(frames, block.shape[0])
            mono = block[:sample_count, 0] if block.ndim == 2 else block[:sample_count]
            outdata[:sample_count, :] = mono[:, None]

        def stop_stream(self):
            global flag_vc
            flag_vc = False
            self.stop_file_playback()
            if self.recorder.active:
                self.set_recording(False)
            if self.asio_worker_stop is not None:
                self.asio_worker_stop.set()
            if self.asio_worker_wakeup is not None:
                self.asio_worker_wakeup.set()
            duplex_stream = (
                self.stream
                if self.stream is not None
                and self.stream is not self.input_stream
                and self.stream is not self.output_stream
                else None
            )
            for stream_name in ("input_stream", "output_stream"):
                stream = getattr(self, stream_name, None)
                if stream is not None:
                    stream.abort()
                    stream.close()
                    setattr(self, stream_name, None)
            if duplex_stream is not None:
                duplex_stream.abort()
                duplex_stream.close()
            self.stream = None
            self.output_queue = None
            self.asio_input_fifo = None
            if self.asio_worker is not None and self.asio_worker.is_alive():
                self.asio_worker.join(timeout=0.5)
            self.asio_worker = None
            self.asio_worker_stop = None
            self.asio_worker_wakeup = None
            self.asio_duplex_main_channels = 0
            self.asio_duplex_monitor_channels = 0
            if hasattr(self, "window"):
                self.window["input_level_meter"].update(0.0)
                self.window["output_level_meter"].update(0.0)
                self.window["monitor_level_meter"].update(0.0)
            if self.monitor_stream is not None:
                self.monitor_stream.abort()
                self.monitor_stream.close()
                self.monitor_stream = None
            self.monitor_queue = None
            self.update_run_buttons()

        def audio_callback(self, indata, frames, times, status):
            """Process one input-audio callback block."""
            global flag_vc
            start_time = time.perf_counter()
            indata = librosa.to_mono(indata.T)
            indata *= np.float32(self.gui_config.input_gain)
            np.clip(indata, -1.0, 1.0, out=indata)
            self.recorder.enqueue("input", indata)
            meter_now = time.perf_counter()
            if meter_now - self.last_input_meter_update >= 0.1:
                peak = float(np.max(np.abs(indata))) if indata.size else 0.0
                peak_db = 20.0 * np.log10(max(peak, 1e-6))
                meter_value = np.clip((peak_db + 60.0) / 60.0, 0.0, 1.0)
                self.latest_input_meter = float(meter_value)
                self.last_input_meter_update = meter_now
            if self.gui_config.threhold > -60:
                indata = np.append(self.rms_buffer, indata)
                rms = librosa.feature.rms(
                    y=indata, frame_length=4 * self.zc, hop_length=self.zc
                )[:, 2:]
                self.rms_buffer[:] = indata[-4 * self.zc :]
                indata = indata[2 * self.zc - self.zc // 2 :]
                db_threhold = (
                    librosa.amplitude_to_db(rms, ref=1.0)[0] < self.gui_config.threhold
                )
                for i in range(db_threhold.shape[0]):
                    if db_threhold[i]:
                        indata[i * self.zc : (i + 1) * self.zc] = 0
                indata = indata[self.zc // 2 :]
            self.input_wav[: -self.block_frame] = self.input_wav[
                self.block_frame :
            ].clone()
            self.input_wav[-indata.shape[0] :] = torch.from_numpy(indata).to(
                self.config.device
            )
            self.input_wav_res[: -self.block_frame_16k] = self.input_wav_res[
                self.block_frame_16k :
            ].clone()
            # input noise reduction and resampling
            if self.gui_config.I_noise_reduce:
                self.input_wav_denoise[: -self.block_frame] = self.input_wav_denoise[
                    self.block_frame :
                ].clone()
                input_wav = self.input_wav[-self.sola_buffer_frame - self.block_frame :]
                input_wav = self.tg(
                    input_wav.unsqueeze(0), self.input_wav.unsqueeze(0)
                ).squeeze(0)
                input_wav[: self.sola_buffer_frame] *= self.fade_in_window
                input_wav[: self.sola_buffer_frame] += (
                    self.nr_buffer * self.fade_out_window
                )
                self.input_wav_denoise[-self.block_frame :] = input_wav[
                    : self.block_frame
                ]
                self.nr_buffer[:] = input_wav[self.block_frame :]
                resample_input = self.input_wav_denoise[
                    -self.block_frame - 2 * self.zc :
                ]
                self.input_wav_res[-self.block_frame_16k - 160 :] = run_cuda_graph(
                    self.resampler,
                    "realtime-input-resample",
                    lambda audio: self.resampler(audio),
                    resample_input,
                )[160:]
            else:
                resample_input = self.input_wav[-indata.shape[0] - 2 * self.zc :]
                self.input_wav_res[-160 * (indata.shape[0] // self.zc + 1) :] = run_cuda_graph(
                    self.resampler,
                    "realtime-input-resample",
                    lambda audio: self.resampler(audio),
                    resample_input,
                )[160:]
            # infer
            if self.function == "vc":
                infer_wav = self.rvc.infer(
                    self.input_wav_res,
                    self.block_frame_16k,
                    self.skip_head,
                    self.return_length,
                    self.gui_config.f0method,
                )
                if self.resampler2 is not None:
                    infer_wav = run_cuda_graph(
                        self.resampler2,
                        "realtime-output-resample",
                        lambda audio: self.resampler2(audio),
                        infer_wav,
                    )
            elif self.gui_config.I_noise_reduce:
                infer_wav = self.input_wav_denoise[self.extra_frame :].clone()
            else:
                infer_wav = self.input_wav[self.extra_frame :].clone()
            # output noise reduction
            if self.gui_config.O_noise_reduce and self.function == "vc":
                self.output_buffer[: -self.block_frame] = self.output_buffer[
                    self.block_frame :
                ].clone()
                self.output_buffer[-self.block_frame :] = infer_wav[-self.block_frame :]
                infer_wav = self.tg(
                    infer_wav.unsqueeze(0), self.output_buffer.unsqueeze(0)
                ).squeeze(0)
            # volume envelop mixing
            if self.gui_config.rms_mix_rate < 1 and self.function == "vc":
                if self.gui_config.I_noise_reduce:
                    input_wav = self.input_wav_denoise[self.extra_frame :]
                else:
                    input_wav = self.input_wav[self.extra_frame :]
                rms1 = librosa.feature.rms(
                    y=input_wav[: infer_wav.shape[0]].cpu().numpy(),
                    frame_length=4 * self.zc,
                    hop_length=self.zc,
                )
                rms1 = torch.from_numpy(rms1).to(self.config.device)
                rms1 = F.interpolate(
                    rms1.unsqueeze(0),
                    size=infer_wav.shape[0] + 1,
                    mode="linear",
                    align_corners=True,
                )[0, 0, :-1]
                rms2 = librosa.feature.rms(
                    y=infer_wav[:].cpu().numpy(),
                    frame_length=4 * self.zc,
                    hop_length=self.zc,
                )
                rms2 = torch.from_numpy(rms2).to(self.config.device)
                rms2 = F.interpolate(
                    rms2.unsqueeze(0),
                    size=infer_wav.shape[0] + 1,
                    mode="linear",
                    align_corners=True,
                )[0, 0, :-1]
                rms2 = torch.max(rms2, torch.zeros_like(rms2) + 1e-3)
                infer_wav *= torch.pow(
                    rms1 / rms2, 1.0 - self.gui_config.rms_mix_rate
                )
            # SOLA algorithm from https://github.com/yxlllc/DDSP-SVC
            conv_input = infer_wav[
                None, None, : self.sola_buffer_frame + self.sola_search_frame
            ]
            cor_nom = F.conv1d(conv_input, self.sola_buffer[None, None, :])
            cor_den = torch.sqrt(
                F.conv1d(
                    conv_input**2,
                    self.sola_den_kernel,
                )
                + 1e-8
            )
            if sys.platform == "darwin":
                _, sola_offset = torch.max(cor_nom[0, 0] / cor_den[0, 0])
                sola_offset = sola_offset.item()
            else:
                sola_offset = torch.argmax(cor_nom[0, 0] / cor_den[0, 0])
            infer_wav = infer_wav[sola_offset:]
            infer_wav[: self.sola_buffer_frame] *= self.fade_in_window
            infer_wav[: self.sola_buffer_frame] += (
                self.sola_buffer * self.fade_out_window
            )
            self.sola_buffer[:] = infer_wav[
                self.block_frame : self.block_frame + self.sola_buffer_frame
            ]
            output_block = torch.clamp(
                infer_wav[: self.block_frame] * self.gui_config.output_gain,
                -1.0,
                1.0,
            )
            output_mono = output_block.cpu().numpy()
            # RVC can restore the source loudness internally (for example
            # through volume-envelope mixing).  Apply the file-player volume
            # after inference so each 1% step controls the audible result.
            if self.file_source_active:
                output_mono *= np.float32(
                    np.clip(self.file_input_volume, 0.0, 1.0)
                )
            monitor_mono = np.clip(
                output_mono * np.float32(self.gui_config.monitor_gain),
                -1.0,
                1.0,
            )
            meter_now = time.perf_counter()
            if meter_now - self.last_output_meter_update >= 0.1:
                peak = float(np.max(np.abs(output_mono))) if output_mono.size else 0.0
                peak_db = 20.0 * np.log10(max(peak, 1e-6))
                meter_value = np.clip((peak_db + 60.0) / 60.0, 0.0, 1.0)
                self.latest_output_meter = float(meter_value)
                if self.monitor_device_index is None:
                    self.latest_monitor_meter = 0.0
                else:
                    monitor_peak = (
                        float(np.max(np.abs(monitor_mono)))
                        if monitor_mono.size
                        else 0.0
                    )
                    monitor_db = 20.0 * np.log10(max(monitor_peak, 1e-6))
                    monitor_value = np.clip(
                        (monitor_db + 60.0) / 60.0, 0.0, 1.0
                    )
                    self.latest_monitor_meter = float(monitor_value)
                self.last_output_meter_update = meter_now
            self.enqueue_audio_target(self.output_queue, output_mono)
            self.enqueue_audio_target(self.monitor_queue, monitor_mono)
            total_time = time.perf_counter() - start_time
            if flag_vc:
                self.latest_infer_time = int(total_time * 1000)
            return output_mono

        @staticmethod
        def enqueue_audio_target(target, block):
            if target is None:
                return
            if isinstance(target, AudioFrameFifo):
                target.write(block)
            else:
                enqueue_latest(target, block.copy())

        @staticmethod
        def friendly_device_label(api_name, device_name, direction):
            lower_name = device_name.lower()
            if "voicemeeter" in lower_name:
                if api_name == "ASIO":
                    return f"[Voicemeeter ASIO] {device_name}"
                if direction == "input":
                    return f"[Voicemeeter] {device_name} → RVC入力"
                return f"[Voicemeeter] {device_name} ← RVC出力"
            api_label = "WASAPI" if api_name == "Windows WASAPI" else api_name
            return f"[{api_label}] {device_name}"

        @staticmethod
        def device_sort_key(label):
            lower_label = label.lower()
            if "voicemeeter" in lower_label:
                priority = 0
            elif " ASIO" in label or "ASIO Link Pro Native" in label:
                priority = 1
            elif label.startswith("[WASAPI]"):
                priority = 2
            else:
                priority = 3
            return priority, lower_label

        def update_devices(self, hostapi_name=None, show_legacy=False):
            """すべてのAPIから入出力デバイスを列挙する。"""
            global flag_vc
            flag_vc = False
            sd._terminate()
            sd._initialize()
            devices = sd.query_devices()
            hostapis = sd.query_hostapis()
            for hostapi in hostapis:
                for device_idx in hostapi["devices"]:
                    devices[device_idx]["hostapi_name"] = hostapi["name"]
            self.hostapis = [hostapi["name"] for hostapi in hostapis]
            self.device_hostapis = {
                index: devices[index]["hostapi_name"] for index in range(len(devices))
            }
            self.input_device_map = {}
            self.output_device_map = {}
            self.input_asio_selectors = {}
            self.output_asio_selectors = {}
            self.device_names = {}
            asio_link_inputs = []
            asio_link_outputs = []
            for endpoint in devices:
                if endpoint["hostapi_name"] != "Windows WASAPI":
                    continue
                endpoint_name = endpoint["name"]
                if "asiovadpro" not in endpoint_name.lower():
                    continue
                input_match = re.match(r"Mix\s*0*(\d+)", endpoint_name, re.I)
                output_match = re.match(
                    r"Speakers\s*0*(\d+)", endpoint_name, re.I
                )
                if input_match and endpoint["max_input_channels"] > 0:
                    asio_link_inputs.append(
                        (int(input_match.group(1)), endpoint_name)
                    )
                if output_match and endpoint["max_output_channels"] > 0:
                    asio_link_outputs.append(
                        (int(output_match.group(1)), endpoint_name)
                    )
            asio_link_inputs.sort()
            asio_link_outputs.sort()
            for index, device in enumerate(devices):
                api_name = device["hostapi_name"]
                if not show_legacy and api_name not in ("ASIO", "Windows WASAPI"):
                    continue
                self.device_names[index] = device["name"]
                if api_name == "ASIO":
                    is_asio_link = "asio link pro" in device["name"].lower()
                    if is_asio_link and asio_link_inputs:
                        for endpoint_number, endpoint_name in asio_link_inputs:
                            first_channel = 2 * (endpoint_number - 1)
                            if first_channel + 1 >= device["max_input_channels"]:
                                continue
                            label = f"{endpoint_name.split(' (', 1)[0]} — ASIO Link Pro Native"
                            self.input_device_map[label] = index
                            self.input_asio_selectors[label] = [
                                first_channel,
                                first_channel + 1,
                            ]
                    else:
                        for pair in self.channel_pairs(
                            device["max_input_channels"]
                        ):
                            label = f"Input {pair} — {device['name']}"
                            self.input_device_map[label] = index
                            self.input_asio_selectors[label] = (
                                self.parse_channel_pair(pair)
                            )
                    if is_asio_link and asio_link_outputs:
                        for endpoint_number, endpoint_name in asio_link_outputs:
                            first_channel = 2 * (endpoint_number - 1)
                            if first_channel + 1 >= device["max_output_channels"]:
                                continue
                            label = f"{endpoint_name.split(' (', 1)[0]} — ASIO Link Pro Native"
                            self.output_device_map[label] = index
                            self.output_asio_selectors[label] = [
                                first_channel,
                                first_channel + 1,
                            ]
                    else:
                        for pair in self.channel_pairs(
                            device["max_output_channels"]
                        ):
                            label = f"Output {pair} — {device['name']}"
                            self.output_device_map[label] = index
                            self.output_asio_selectors[label] = (
                                self.parse_channel_pair(pair)
                            )
                    continue
                if device["max_input_channels"] > 0:
                    label = self.friendly_device_label(
                        api_name, device["name"], "input"
                    )
                    self.input_device_map[label] = index
                if device["max_output_channels"] > 0:
                    label = self.friendly_device_label(
                        api_name, device["name"], "output"
                    )
                    self.output_device_map[label] = index
            self.input_devices = sorted(
                self.input_device_map, key=self.device_sort_key
            )
            self.output_devices = sorted(
                self.output_device_map, key=self.device_sort_key
            )
            self.input_devices_indices = list(self.input_device_map.values())
            self.output_devices_indices = list(self.output_device_map.values())
        def normalize_device_choice(self, saved_value, direction, saved_api=""):
            choices = (
                self.input_device_map
                if direction == "input"
                else self.output_device_map
            )
            if saved_value in choices:
                return saved_value
            if saved_value:
                preferred = f"[{saved_api}] {saved_value}" if saved_api else ""
                if preferred in choices:
                    return preferred
                saved_name = saved_value.split("] ", 1)[-1]
                saved_name = saved_name.removesuffix(" → RVC入力")
                saved_name = saved_name.removesuffix(" ← RVC出力")
                match = next(
                    (
                        label
                        for label, index in choices.items()
                        if self.device_names.get(index) == saved_name
                        and (
                            not saved_api
                            or self.device_hostapis.get(index) == saved_api
                            or saved_api.replace("Windows ", "")
                            in label.split("]", 1)[0]
                        )
                    ),
                    None,
                )
                if match:
                    return match
            default_index = sd.default.device[0 if direction == "input" else 1]
            return next(
                (label for label, index in choices.items() if index == default_index),
                next(iter(choices), ""),
            )

        def selected_device_api(self, label, direction):
            mapping = (
                self.input_device_map
                if direction == "input"
                else self.output_device_map
            )
            index = mapping.get(label)
            return self.device_hostapis.get(index, "") if index is not None else ""

        @staticmethod
        def channel_pairs(channel_count):
            pairs = []
            for first in range(0, int(channel_count), 2):
                second = min(first + 1, int(channel_count) - 1)
                pairs.append(f"{first + 1} / {second + 1}")
            return pairs or ["1 / 1"]

        @staticmethod
        def parse_channel_pair(value):
            return [int(part.strip()) - 1 for part in value.split("/")]

        def set_devices(
            self,
            input_device,
            output_device,
            monitor_device,
        ):
            """選択されたAPIを問わず入出力を設定する。"""
            output_index = self.output_device_map[output_device]
            if self.file_source_active:
                # A decoded file has no PortAudio input endpoint.  Binding
                # the unused input side to the output endpoint prevents a
                # stale/disabled microphone or ASIO driver from vetoing
                # conversion startup.
                input_index = output_index
                input_api = "File"
            else:
                input_index = self.input_device_map[input_device]
                input_api = self.device_hostapis[input_index]
            output_api = self.device_hostapis[output_index]
            if (
                not self.file_source_active
                and input_api == "ASIO"
                and output_api == "ASIO"
                and input_index != output_index
            ):
                raise ValueError(
                    "異なるASIOドライバーを同時には使用できません。"
                    if IS_JAPANESE_UI
                    else "Two different ASIO drivers cannot be used at the same time."
                )
            sd.default.device = (input_index, output_index)
            self.gui_config.sg_input_hostapi = input_api
            self.gui_config.sg_output_hostapi = output_api
            self.asio_input_selectors = (
                []
                if self.file_source_active
                else self.input_asio_selectors.get(input_device, [])
            )
            self.asio_output_selectors = self.output_asio_selectors.get(
                output_device, []
            )
            self.monitor_device_index = (
                None
                if monitor_device == MONITOR_DISABLED
                else self.output_device_map[monitor_device]
            )
            if self.monitor_device_index == output_index:
                printt(
                    "Monitor output is the same as the main output; "
                    "the duplicate stream was omitted."
                )
                self.monitor_device_index = None
            self.gui_config.sg_monitor_hostapi = (
                ""
                if self.monitor_device_index is None
                else self.device_hostapis[self.monitor_device_index]
            )
            printt(
                "Audio route: Input [%s] %s / Output [%s] %s / Monitor [%s] %s",
                input_api,
                input_device,
                output_api,
                output_device,
                self.gui_config.sg_monitor_hostapi or "Disabled",
                monitor_device,
            )
            if input_api == "ASIO" or output_api == "ASIO":
                printt(
                    "ASIO driver open: input=%s output=%s",
                    input_device if input_api == "ASIO" else "None",
                    output_device if output_api == "ASIO" else "None",
                )
            self.asio_monitor_selectors = self.output_asio_selectors.get(
                monitor_device, []
            )
            if self.asio_monitor_selectors == self.asio_output_selectors:
                self.asio_monitor_selectors = []
            if (
                self.monitor_device_index is not None
                and self.gui_config.sg_monitor_hostapi == "ASIO"
                and self.monitor_device_index != output_index
                and not (
                    not self.file_source_active
                    and input_api == "ASIO"
                    and self.monitor_device_index == input_index
                )
            ):
                raise ValueError(
                    "ASIOモニターは、ASIO入力またはASIO出力と同じドライバーを選んでください。"
                    if IS_JAPANESE_UI
                    else "ASIO monitoring requires the same driver as the ASIO input or output."
                )
            printt("Input device: %s:%s", str(sd.default.device[0]), input_device)
            printt("Output device: %s:%s", str(sd.default.device[1]), output_device)
            if self.monitor_device_index is not None:
                printt(
                    "モニターデバイス：%s:%s",
                    str(self.monitor_device_index),
                    monitor_device,
                )

        def get_device_samplerate(self):
            return int(
                sd.query_devices(device=sd.default.device[0])["default_samplerate"]
            )

        def get_automatic_samplerate(self, model_rate):
            """Use the active audio route's clock; RVC resamples as needed.

            Virtual ASIO drivers such as ASIO Link Pro bridge Windows audio,
            which commonly runs at 44.1 or 48 kHz.  Starting that driver at a
            model's 40 kHz rate can work syntactically yet glitch when a
            Windows audio source is active.  Prefer the route's actual common
            rate; the model rate is only considered as a final fallback.
            """
            return self.get_routing_samplerate(preferred_rates=[model_rate])

        def get_routing_samplerate(self, preferred_rates=()):
            """Find a sample rate that every active stream can actually open.

            A mixed ASIO/WASAPI route cannot use the input device's rate
            blindly: virtual outputs frequently default to 48 kHz while an
            interface input defaults to 44.1 kHz.  The streams still share one
            RVC processing clock, so negotiate a common supported rate first.
            """
            input_info = sd.query_devices(device=sd.default.device[0])
            output_info = sd.query_devices(device=sd.default.device[1])

            def check_endpoint(
                checker,
                device,
                channels,
                api_name,
                rate,
                asio_selectors=None,
            ):
                if api_name == "ASIO":
                    extra = sd.AsioSettings(
                        channel_selectors=asio_selectors or []
                    )
                    checker(
                        device=device,
                        channels=channels,
                        dtype="float32",
                        samplerate=rate,
                        extra_settings=extra,
                    )
                    return extra, False

                if (
                    "WASAPI" in api_name
                    and self.gui_config.sg_wasapi_exclusive
                ):
                    exclusive = sd.WasapiSettings(exclusive=True)
                    try:
                        checker(
                            device=device,
                            channels=channels,
                            dtype="float32",
                            samplerate=rate,
                            extra_settings=exclusive,
                        )
                        return exclusive, False
                    except sd.PortAudioError:
                        # Some Windows drivers expose a WASAPI endpoint but no
                        # usable exclusive PCM format.  Keep the route usable
                        # by falling back only that endpoint to shared mode.
                        checker(
                            device=device,
                            channels=channels,
                            dtype="float32",
                            samplerate=rate,
                            extra_settings=None,
                        )
                        return None, True

                checker(
                    device=device,
                    channels=channels,
                    dtype="float32",
                    samplerate=rate,
                    extra_settings=None,
                )
                return None, False

            candidates = []
            for rate in (
                *( () if self.file_source_active else (input_info["default_samplerate"],) ),
                output_info["default_samplerate"],
                48000,
                44100,
                *preferred_rates,
                40000,
            ):
                rate = int(round(rate))
                if rate > 0 and rate not in candidates:
                    candidates.append(rate)

            errors = []
            for rate in candidates:
                try:
                    if self.file_source_active:
                        input_extra, input_fallback = None, False
                    else:
                        input_extra, input_fallback = check_endpoint(
                            sd.check_input_settings,
                            sd.default.device[0],
                            self.gui_config.channels,
                            self.gui_config.sg_input_hostapi,
                            rate,
                            self.asio_input_selectors,
                        )
                    output_extra, output_fallback = check_endpoint(
                        sd.check_output_settings,
                        sd.default.device[1],
                        self.gui_config.output_channels,
                        self.gui_config.sg_output_hostapi,
                        rate,
                        self.asio_output_selectors,
                    )
                    monitor_extra = None
                    monitor_fallback = False
                    if self.monitor_device_index is not None:
                        monitor_info = sd.query_devices(self.monitor_device_index)
                        if self.gui_config.sg_monitor_hostapi == "ASIO":
                            # Selecting the same ASIO output for both Output
                            # and Monitor is represented by no extra selectors;
                            # it is already covered by the output check above.
                            if self.asio_monitor_selectors:
                                monitor_channels = len(
                                    self.asio_monitor_selectors
                                )
                                monitor_extra, monitor_fallback = check_endpoint(
                                    sd.check_output_settings,
                                    self.monitor_device_index,
                                    monitor_channels,
                                    self.gui_config.sg_monitor_hostapi,
                                    rate,
                                    self.asio_monitor_selectors,
                                )
                        else:
                            monitor_channels = min(
                                int(monitor_info["max_output_channels"]), 2
                            )
                            monitor_extra, monitor_fallback = check_endpoint(
                                sd.check_output_settings,
                                self.monitor_device_index,
                                monitor_channels,
                                self.gui_config.sg_monitor_hostapi,
                                rate,
                            )

                    self.input_wasapi_settings = (
                        input_extra
                        if "WASAPI" in self.gui_config.sg_input_hostapi
                        else None
                    )
                    self.output_wasapi_settings = (
                        output_extra
                        if "WASAPI" in self.gui_config.sg_output_hostapi
                        else None
                    )
                    self.monitor_wasapi_settings = (
                        monitor_extra
                        if "WASAPI" in self.gui_config.sg_monitor_hostapi
                        else None
                    )
                    printt("Selected common sample rate: %s", rate)
                    for fallback, device in (
                        (input_fallback, sd.default.device[0]),
                        (output_fallback, sd.default.device[1]),
                        (monitor_fallback, self.monitor_device_index),
                    ):
                        if fallback and device is not None:
                            printt(
                                "WASAPI exclusive unavailable; shared fallback: %s",
                                sd.query_devices(device)["name"],
                            )
                    return rate
                except sd.PortAudioError as error:
                    errors.append(f"{rate} Hz: {error}")
                    continue

            raise ValueError(
                "The selected input, output, and monitor devices have no common sample rate. "
                "Set the devices to the same rate (usually 48 kHz or 44.1 kHz).\n"
                + "\n".join(errors[-3:])
            )

        def get_device_channels(self):
            if self.gui_config.sg_input_hostapi == "ASIO":
                return len(self.asio_input_selectors)
            return min(
                int(sd.query_devices(device=sd.default.device[0])["max_input_channels"]),
                2,
            )

        def get_output_channels(self):
            if self.gui_config.sg_output_hostapi == "ASIO":
                return len(self.asio_output_selectors)
            return min(
                int(sd.query_devices(device=sd.default.device[1])["max_output_channels"]),
                2,
            )

    gui = GUI()
