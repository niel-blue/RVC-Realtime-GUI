"""FFmpeg-backed audio-file source for the real-time RVC path."""

from __future__ import annotations

import os
import queue
import re
import subprocess
import threading
import time

import numpy as np


class FileAudioSource:
    """Decode audio off the inference thread and feed fixed realtime blocks."""

    def __init__(self, ffmpeg_path, path, sample_rate, block_frames, on_block, tail_blocks=0):
        self.ffmpeg_path = ffmpeg_path
        self.path = path
        self.sample_rate = int(sample_rate)
        self.block_frames = int(block_frames)
        self.on_block = on_block
        self.tail_blocks = max(0, int(tail_blocks))
        self.duration = self.probe_duration(ffmpeg_path, path)
        self.position = 0.0
        self.playing = False
        self.finished = False
        self.error = None
        self._blocks = queue.Queue(maxsize=32)
        self._stop = threading.Event()
        self._playing = threading.Event()
        self._restart = threading.Event()
        self._lock = threading.Lock()
        self._seek_to = 0.0
        self._decoder_process = None
        self._decoder = None
        self._feeder = threading.Thread(target=self._feed_loop, name="rvc-file-feed", daemon=True)
        self._start_decoder()
        self._feeder.start()

    @staticmethod
    def probe_duration(ffmpeg_path, path):
        try:
            completed = subprocess.run(
                [ffmpeg_path, "-hide_banner", "-i", path],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=15,
            )
            match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", completed.stderr)
            if match:
                hours, minutes, seconds = match.groups()
                return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        except (OSError, subprocess.SubprocessError):
            pass
        return 0.0

    def play(self):
        if self.finished:
            self.seek(0.0)
        self.playing = True
        self._playing.set()

    def pause(self):
        self.playing = False
        self._playing.clear()

    def seek(self, seconds):
        seconds = max(0.0, min(float(seconds), self.duration or float("inf")))
        with self._lock:
            self._seek_to = seconds
            self.position = seconds
            self.finished = False
        self._restart.set()
        self._terminate_decoder()
        self._clear_blocks()
        if self._decoder is None or not self._decoder.is_alive():
            self._start_decoder()

    def _start_decoder(self):
        self._decoder = threading.Thread(
            target=self._decode_loop, name="rvc-file-decode", daemon=True
        )
        self._decoder.start()

    def stop(self):
        self.playing = False
        self._playing.clear()
        self._stop.set()
        self._terminate_decoder()
        self._clear_blocks()

    def _clear_blocks(self):
        while True:
            try:
                self._blocks.get_nowait()
            except queue.Empty:
                return

    def _terminate_decoder(self):
        process = self._decoder_process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass

    def _decode_loop(self):
        while not self._stop.is_set():
            with self._lock:
                start_at = self._seek_to
            self._restart.clear()
            command = [
                self.ffmpeg_path,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{start_at:.6f}",
                "-i",
                self.path,
                "-vn",
                "-ac",
                "1",
                "-ar",
                str(self.sample_rate),
                "-f",
                "f32le",
                "pipe:1",
            ]
            try:
                self._decoder_process = subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            except OSError as error:
                self._put(("error", str(error)))
                return
            try:
                bytes_per_block = self.block_frames * 4
                while not self._stop.is_set() and not self._restart.is_set():
                    raw = self._decoder_process.stdout.read(bytes_per_block)
                    if not raw:
                        break
                    samples = np.frombuffer(raw, dtype="<f4").copy()
                    if samples.size < self.block_frames:
                        samples = np.pad(samples, (0, self.block_frames - samples.size))
                    self._put(("audio", samples))
                    if len(raw) < bytes_per_block:
                        break
            finally:
                self._terminate_decoder()
                self._decoder_process = None
            if self._stop.is_set():
                return
            if self._restart.is_set():
                continue
            for _ in range(self.tail_blocks):
                self._put(("audio", np.zeros(self.block_frames, dtype=np.float32)))
            self._put(("eof", None))
            return

    def _put(self, item):
        while not self._stop.is_set() and not self._restart.is_set():
            try:
                self._blocks.put(item, timeout=0.1)
                return
            except queue.Full:
                continue

    def _feed_loop(self):
        next_tick = time.perf_counter()
        duration = self.block_frames / self.sample_rate
        while not self._stop.is_set():
            if not self._playing.wait(0.1):
                next_tick = time.perf_counter()
                continue
            try:
                kind, payload = self._blocks.get(timeout=0.1)
            except queue.Empty:
                continue
            if kind == "error":
                self.error = payload
                self.finished = True
                self.pause()
                continue
            if kind == "eof":
                self.finished = True
                self.pause()
                continue
            try:
                self.on_block(payload)
            except Exception:
                self.finished = True
                self.pause()
                continue
            with self._lock:
                self.position = min(self.position + duration, self.duration or float("inf"))
            next_tick += duration
            sleep_for = next_tick - time.perf_counter()
            if sleep_for > 0:
                time.sleep(sleep_for)
            else:
                next_tick = time.perf_counter()
