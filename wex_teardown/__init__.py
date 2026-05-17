import sys
from pathlib import Path


def _bootstrap_vendor_libs():
    vendor_path = Path(__file__).resolve().parent / "vendor"
    if vendor_path.exists():
        vendor_str = str(vendor_path)
        if vendor_str not in sys.path:
            sys.path.insert(0, vendor_str)


_bootstrap_vendor_libs()

from . import models
from . import wizard
