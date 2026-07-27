import unittest

import numpy as np

from tools.audio_fifo import AudioFrameFifo


class AudioFrameFifoTest(unittest.TestCase):
    def test_reassembles_driver_sized_callbacks_into_rvc_chunk(self):
        fifo = AudioFrameFifo(channels=2, max_frames=2048)
        for start in range(0, 960, 128):
            stop = min(start + 128, 960)
            fifo.write(np.full((stop - start, 2), start, dtype=np.float32))

        block = fifo.read(960, exact=True)

        self.assertEqual(block.shape, (960, 2))
        self.assertEqual(fifo.available_frames, 0)

    def test_exact_read_waits_for_complete_rvc_chunk(self):
        fifo = AudioFrameFifo(channels=1)
        fifo.write(np.zeros(127, dtype=np.float32))

        self.assertIsNone(fifo.read(128, exact=True))
        self.assertEqual(fifo.available_frames, 127)

    def test_preserves_remainder_for_next_driver_callback(self):
        fifo = AudioFrameFifo(channels=1)
        fifo.write(np.arange(300, dtype=np.float32))

        first = fifo.read(128)
        second = fifo.read(128)

        np.testing.assert_array_equal(first[:, 0], np.arange(128))
        np.testing.assert_array_equal(second[:, 0], np.arange(128, 256))
        self.assertEqual(fifo.available_frames, 44)

    def test_drops_oldest_frames_when_bounded(self):
        fifo = AudioFrameFifo(channels=1, max_frames=5)
        fifo.write(np.arange(8, dtype=np.float32))

        remaining = fifo.read(5, exact=True)

        np.testing.assert_array_equal(remaining[:, 0], np.arange(3, 8))


if __name__ == "__main__":
    unittest.main()
