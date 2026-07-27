from collections import deque
import threading

import numpy as np


class AudioFrameFifo:
    """Thread-safe, bounded FIFO measured in audio frames."""

    def __init__(self, channels=1, max_frames=None):
        self.channels = int(channels)
        self.max_frames = None if max_frames is None else int(max_frames)
        self._chunks = deque()
        self._frames = 0
        self._lock = threading.Lock()

    @property
    def available_frames(self):
        with self._lock:
            return self._frames

    def clear(self):
        with self._lock:
            self._chunks.clear()
            self._frames = 0

    def write(self, data):
        array = np.asarray(data, dtype=np.float32)
        if array.ndim == 1:
            array = array[:, None]
        if array.ndim != 2 or array.shape[1] != self.channels:
            raise ValueError(
                f"Expected (frames, {self.channels}) audio, got {array.shape}"
            )
        if not array.shape[0]:
            return
        with self._lock:
            self._chunks.append(array.copy())
            self._frames += array.shape[0]
            if self.max_frames is not None and self._frames > self.max_frames:
                self._discard_locked(self._frames - self.max_frames)

    def read(self, frames, exact=False):
        frames = int(frames)
        with self._lock:
            if exact and self._frames < frames:
                return None
            take = min(frames, self._frames)
            if take <= 0:
                return None
            parts = []
            remaining = take
            while remaining:
                chunk = self._chunks[0]
                count = min(remaining, chunk.shape[0])
                parts.append(chunk[:count])
                if count == chunk.shape[0]:
                    self._chunks.popleft()
                else:
                    self._chunks[0] = chunk[count:]
                self._frames -= count
                remaining -= count
        return parts[0] if len(parts) == 1 else np.concatenate(parts, axis=0)

    def _discard_locked(self, frames):
        remaining = int(frames)
        while remaining > 0 and self._chunks:
            chunk = self._chunks[0]
            count = min(remaining, chunk.shape[0])
            if count == chunk.shape[0]:
                self._chunks.popleft()
            else:
                self._chunks[0] = chunk[count:]
            self._frames -= count
            remaining -= count
