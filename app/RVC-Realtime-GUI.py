"""User-facing launcher for RVC-Realtime-GUI.

The import-friendly realtime_gui.py module remains the implementation entry
point for tests and internal imports.
"""

from pathlib import Path
import runpy


runpy.run_path(
    str(Path(__file__).with_name("realtime_gui.py")), run_name="__main__"
)
