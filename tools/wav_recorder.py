"""Asynchronous WAV recording for the real-time audio path."""

from __future__ import annotations

import datetime as dt
import os
import queue
import threading
import time
import wave


class WavRecorder:
    """Receives short PCM blocks and writes them outside the audio callback."""

    def __init__(self):
        self._queue = queue.Queue(maxsize=512)
        self._stop = threading.Event()
        self._thread = None
        self.mode = "separate"
        self.sample_rate = 48000
        self.started_at = None
        self.last_saved_paths = []

    @property
    def active(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, folder, sample_rate, mode):
        self.stop()
        os.makedirs(folder, exist_ok=True)
        self.mode = mode
        self.sample_rate = int(sample_rate)
        self.started_at = dt.datetime.now()
        timestamp = self.started_at.strftime("%Y-%m-%d_%H%M%S")
        paths = {"folder": folder, "timestamp": timestamp}
        if mode == "separate":
            paths["input"] = os.path.join(folder, f"{timestamp}_input.wav")
            paths["output"] = os.path.join(folder, f"{timestamp}_output.wav")
        elif mode == "mix":
            paths["combined"] = os.path.join(folder, f"{timestamp}_mix.wav")
        else:
            paths["combined"] = os.path.join(folder, f"{timestamp}_stereo.wav")
        self.last_saved_paths = [
            path for key, path in paths.items() if key in ("input", "output", "combined")
        ]
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._writer, args=(paths,), name="rvc-wav-recorder", daemon=True
        )
        self._thread.start()

    def enqueue(self, kind, samples):
        if not self.active or kind not in ("input", "output"):
            return
        try:
            # Copying a short block is the only work done in the audio path.
            self._queue.put_nowait((kind, time.perf_counter(), samples.copy()))
        except queue.Full:
            # Dropping a recording block is preferable to blocking inference.
            pass

    def stop(self):
        self._stop.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=2.0)
        self._thread = None

    def _open_writer(self, path, channels=1):
        writer = wave.open(path, "wb")
        writer.setnchannels(channels)
        writer.setsampwidth(2)
        writer.setframerate(self.sample_rate)
        return writer

    @staticmethod
    def _pcm16(samples):
        import numpy as np

        return (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")

    def _writer(self, paths):
        import numpy as np

        writers = {}
        temp_paths = {}
        starts = {}
        try:
            # Keep both capture timelines in temporary tracks first.  Separate
            # WAV files also need this: their first callbacks can occur at
            # different real times (especially with file playback), and direct
            # writes would silently discard that offset.
            for kind in ("input", "output"):
                path = os.path.join(
                    paths["folder"], f".{paths['timestamp']}_{kind}.tmp.wav"
                )
                temp_paths[kind] = path
                writers[kind] = self._open_writer(path)

            while not self._stop.is_set() or not self._queue.empty():
                try:
                    kind, captured_at, samples = self._queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                if kind not in starts:
                    starts[kind] = captured_at
                writers[kind].writeframes(self._pcm16(samples).tobytes())
        finally:
            for writer in writers.values():
                writer.close()

        try:
            if self.mode == "separate":
                self._write_aligned_separate(temp_paths, starts, paths)
            else:
                self._combine_tracks(temp_paths, starts, paths["combined"])
        finally:
            for path in temp_paths.values():
                try:
                    os.remove(path)
                except OSError:
                    pass

    def _write_aligned_separate(self, temp_paths, starts, paths):
        """Write two WAVs on one common clock without latency correction."""
        readers = {kind: wave.open(path, "rb") for kind, path in temp_paths.items()}
        try:
            frames = {kind: reader.getnframes() for kind, reader in readers.items()}
            if not any(frames.values()):
                return
            origin = min(starts.values()) if starts else time.perf_counter()
            offsets = {
                kind: max(
                    0,
                    round((starts.get(kind, origin) - origin) * self.sample_rate),
                )
                for kind in readers
            }
            total = max(offsets[kind] + frames[kind] for kind in readers)
            silence = b"\x00\x00" * 8192
            for kind, reader in readers.items():
                writer = self._open_writer(paths[kind])
                try:
                    remaining = offsets[kind]
                    while remaining:
                        count = min(remaining, 8192)
                        writer.writeframes(silence[: count * 2])
                        remaining -= count
                    remaining = frames[kind]
                    while remaining:
                        count = min(remaining, 8192)
                        writer.writeframes(reader.readframes(count))
                        remaining -= count
                    remaining = total - offsets[kind] - frames[kind]
                    while remaining:
                        count = min(remaining, 8192)
                        writer.writeframes(silence[: count * 2])
                        remaining -= count
                finally:
                    writer.close()
        finally:
            for reader in readers.values():
                reader.close()

    def _combine_tracks(self, paths, starts, output_path):
        """Create a mono mix or stereo file without delay compensation."""
        import numpy as np

        readers = {kind: wave.open(path, "rb") for kind, path in paths.items()}
        try:
            frames = {kind: reader.getnframes() for kind, reader in readers.items()}
            if not any(frames.values()):
                return
            origin = min(starts.values()) if starts else time.perf_counter()
            offsets = {
                kind: max(
                    0,
                    round(
                        (starts.get(kind, origin) - origin) * self.sample_rate
                    ),
                )
                for kind in readers
            }
            total = max(offsets[kind] + frames[kind] for kind in readers)
            channels = 2 if self.mode == "stereo" else 1
            writer = self._open_writer(output_path, channels)
            try:
                block_size = 8192
                for position in range(0, total, block_size):
                    count = min(block_size, total - position)
                    tracks = {}
                    for kind, reader in readers.items():
                        data = np.zeros(count, dtype=np.int16)
                        source_pos = position - offsets[kind]
                        if source_pos < frames[kind] and source_pos + count > 0:
                            read_at = max(0, source_pos)
                            dest_at = max(0, -source_pos)
                            read_count = min(count - dest_at, frames[kind] - read_at)
                            reader.setpos(read_at)
                            data[dest_at : dest_at + read_count] = np.frombuffer(
                                reader.readframes(read_count), dtype="<i2"
                            )
                        tracks[kind] = data
                    if self.mode == "mix":
                        # Both tracks are already placed on the same real-time
                        # clock above.  Do not shift either one: the audible
                        # offset is the actual RVC/output-buffer delay.  Scale
                        # their sum instead of clipping it, so neither track
                        # disappears when their peaks overlap.
                        mixed = (
                            (
                                tracks["input"].astype(np.int32)
                                + tracks["output"].astype(np.int32)
                            )
                            // 2
                        ).astype("<i2")
                        writer.writeframes(mixed.tobytes())
                    else:
                        stereo = np.column_stack((tracks["input"], tracks["output"])).astype("<i2")
                        writer.writeframes(stereo.tobytes())
            finally:
                writer.close()
        finally:
            for reader in readers.values():
                reader.close()
