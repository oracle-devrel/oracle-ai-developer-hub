#!/usr/bin/env python

import sys
from pathlib import Path

# Add the source directory to the path so we can import the modules
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(src_dir / "oraviz_mcp"))

# Import server module for direct access
import oraviz_mcp.server  # noqa: E402,F401
