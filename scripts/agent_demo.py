"""已迁移至 scripts/demos/agent_demo.py。"""

import runpy
import sys
from pathlib import Path

_TARGET = Path(__file__).resolve().parent / "demos" / "agent_demo.py"
if __name__ == "__main__":
    sys.argv[0] = str(_TARGET)
    runpy.run_path(str(_TARGET), run_name="__main__")
