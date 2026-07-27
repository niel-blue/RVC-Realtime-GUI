import unittest
import queue
import io

from app.realtime_gui import (
    GENERAL_DEFAULTS,
    PERFORMANCE_DEFAULTS,
    QueueTextWriter,
    db_to_linear,
    enqueue_latest,
)


class GainConversionTest(unittest.TestCase):
    def test_unity_gain(self):
        self.assertEqual(db_to_linear(0), 1.0)

    def test_positive_gain(self):
        self.assertAlmostEqual(db_to_linear(6), 1.9952623149688795)

    def test_negative_gain(self):
        self.assertAlmostEqual(db_to_linear(-6), 0.5011872336272722)


class MonitorQueueTest(unittest.TestCase):
    def test_full_queue_discards_oldest_block(self):
        blocks = queue.Queue(maxsize=2)
        enqueue_latest(blocks, "oldest")
        enqueue_latest(blocks, "middle")
        enqueue_latest(blocks, "latest")

        self.assertEqual(blocks.get_nowait(), "middle")
        self.assertEqual(blocks.get_nowait(), "latest")


class SettingsDefaultsTest(unittest.TestCase):
    def test_index_rate_default_matches_original_realtime_rvc(self):
        self.assertEqual(GENERAL_DEFAULTS["index_rate"], 0.0)

    def test_rms_mix_default_matches_original_realtime_rvc(self):
        self.assertEqual(GENERAL_DEFAULTS["rms_mix_rate"], 0.0)

    def test_performance_defaults_are_valid(self):
        self.assertGreater(PERFORMANCE_DEFAULTS["block_time"], 0)
        self.assertGreater(PERFORMANCE_DEFAULTS["crossfade_length"], 0)
        self.assertGreater(PERFORMANCE_DEFAULTS["extra_time"], 0)

class QueueTextWriterTest(unittest.TestCase):
    def test_writes_to_queue_and_console_mirror(self):
        text_queue = queue.Queue()
        mirror = io.StringIO()
        writer = QueueTextWriter(text_queue, mirror)

        writer.write("startup complete\n")
        writer.flush()

        self.assertEqual(text_queue.get_nowait(), "startup complete\n")
        self.assertEqual(mirror.getvalue(), "startup complete\n")


if __name__ == "__main__":
    unittest.main()
