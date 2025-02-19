import pytest
from unittest.mock import AsyncMock
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

@pytest.fixture
def mock_database_service():
    return AsyncMock()

@pytest.fixture
def mock_external_api_service():
    return AsyncMock()

@pytest.fixture
def mock_notifier_service():
    return AsyncMock()
