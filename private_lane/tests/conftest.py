from __future__ import annotations

import sys
from pathlib import Path

PRIVATE_LANE_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PRIVATE_LANE_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
