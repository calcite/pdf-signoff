"""Capture the URL passed to a configured browser command and exit."""

import os
import sys
from pathlib import Path

Path(os.environ["PDF_SIGNOFF_BROWSER_CAPTURE"]).write_text(
    sys.argv[-1], encoding="utf-8"
)
