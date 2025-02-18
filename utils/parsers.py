from typing import List, Set, Union
import logging

logger = logging.getLogger(__name__)

def parse_kinds(kinds: Union[List[int], str]) -> List[int]:
    """Parse kinds from either a list or comma-separated string."""
    if isinstance(kinds, list):
        return kinds
    elif isinstance(kinds, str):
        try:
            return [int(k.strip()) for k in kinds.split(',') if k.strip().isdigit()]
        except ValueError as e:
            logger.error(f"Error parsing kinds string: {e}")
            return []
    else:
        logger.warning(f"Unexpected type for 'kinds': {type(kinds)}")
        return []

def parse_current_kinds(kinds_str: str) -> Set[int]:
    """Parse current kinds from a comma-separated string."""
    if not kinds_str:
        return set()
    try:
        return set(int(k.strip()) for k in kinds_str.split(',') if k.strip().isdigit())
    except ValueError as e:
        logger.error(f"Error parsing current kinds: {e}")
        return set()

def extract_id_from_stdout(stdout: str) -> str:
    """Extract ID from JSON stdout."""
    try:
        data = json.loads(stdout)
        return data.get('id', None)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON from stdout: {e}. Data: {stdout}")
        return None

# Add imports at the top
import json
