"""Shared utility modules for the Crucible platform"""

import os
import re
from datetime import datetime, timezone


def generate_evaluation_id() -> str:
    """Generate a unique evaluation ID with format: YYYYMMDD_HHMMSS_<hex>"""
    return f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"


def is_valid_evaluation_id(eval_id: str) -> bool:
    """Check if a string matches the evaluation ID format"""
    # Pattern: YYYYMMDD_HHMMSS_[8 hex chars]
    pattern = r'^\d{8}_\d{6}_[a-f0-9]{8}$'
    return bool(re.match(pattern, eval_id))