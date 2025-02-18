import pytest
from unittest.mock import AsyncMock
from ..services.cyberherd_manager import CyberHerdManager
from ..config import MAX_HERD_SIZE
from ..models import HookData

@pytest.mark.asyncio
async def test_calculate_payout():
    manager = CyberHerdManager(None, None, None)
    assert manager.calculate_payout(100) == 1.0
    assert manager.calculate_payout(10) == 0.3
    assert manager.calculate_payout(50) == 0.5

@pytest.mark.asyncio
async def test_process_new_member_success():
    database_mock = AsyncMock()
    notifier_mock = AsyncMock()
    manager = CyberHerdManager(database_mock, None, notifier_mock)
    member_data = {"pubkey": "test_pubkey", "amount": 100}
    kinds_int = [9734]
    database_mock.add_cyber_herd_member.return_value = None
    notifier_mock.send_cyberherd_notification.return_value = None

    success, message = await manager.process_new_member(member_data, kinds_int, 0)
    
    assert success is True
    assert message is None
    database_mock.add_cyber_herd_member.assert_called_once_with(member_data)
    notifier_mock.send_cyberherd_notification.assert_called_once()

@pytest.mark.asyncio
async def test_process_new_member_herd_full():
    database_mock = AsyncMock()
    notifier_mock = AsyncMock()
    manager = CyberHerdManager(database_mock, None, notifier_mock)
    member_data = {"pubkey": "test_pubkey", "amount": 100}
    kinds_int = [9734]

    success, message = await manager.process_new_member(member_data, kinds_int, MAX_HERD_SIZE)
    
    assert success is False
    assert message == "Herd is full"
    database_mock.add_cyber_herd_member.assert_not_called()
    notifier_mock.send_cyberherd_notification.assert_not_called()

@pytest.mark.asyncio
async def test_process_existing_member_success():
    database_mock = AsyncMock()
    manager = CyberHerdManager(database_mock, None, None)
    member_data = {"pubkey": "test_pubkey", "amount": 100}
    kinds_int = [9734]
    current_kinds = []
    database_mock.update_cyber_herd_member.return_value = None

    success, message = await manager.process_existing_member(member_data, kinds_int, current_kinds)
    
    assert success is True
    assert message is None
    database_mock.update_cyber_herd_member.assert_called_once()

@pytest.mark.asyncio
async def test_distribute_rewards_success():
    database_mock = AsyncMock()
    external_api_mock = AsyncMock()
    notifier_mock = AsyncMock()
    manager = CyberHerdManager(database_mock, external_api_mock, notifier_mock)
    members = [{"lud16": "test@example.com", "payouts": 0.5}]
    database_mock.get_cyber_herd_members.return_value = members
    external_api_mock.make_lnurl_payment.return_value = None
    notifier_mock.send_cyberherd_notification.return_value = None

    await manager.distribute_rewards(1000)
    
    database_mock.get_cyber_herd_members.assert_called_once()
    external_api_mock.make_lnurl_payment.assert_called_once()
    notifier_mock.send_cyberherd_notification.assert_called_once()

@pytest.mark.asyncio
async def test_process_payment_data_success():
    database_mock = AsyncMock()
    notifier_mock = AsyncMock()
    manager = CyberHerdManager(database_mock, None, notifier_mock)
    hook_data = HookData(payment_hash="test_event_id", amount=100)
    database_mock.fetch_one.return_value = {"pubkey": "test_pubkey"}
    database_mock.update_notified_field.return_value = None
    notifier_mock.send_sats_received_notification.return_value = None

    await manager.process_payment_data(hook_data)

    database_mock.fetch_one.assert_called_once_with(
        "SELECT * FROM cyber_herd WHERE event_id = :payment_hash",
        {"payment_hash": "test_event_id"}
    )
    database_mock.update_notified_field.assert_called_once_with("test_pubkey", "success")
    notifier_mock.send_sats_received_notification.assert_called_once_with(
        sats_received=100, difference=0
    )
