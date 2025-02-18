import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_database_service():
    return AsyncMock()

@pytest.fixture
def mock_external_api_service():
    return AsyncMock()

@pytest.fixture
def mock_notifier_service():
    return AsyncMock()
