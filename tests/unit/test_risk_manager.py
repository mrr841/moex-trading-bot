import pytest
from src.risk_manager import RiskManager
from unittest.mock import MagicMock

class TestRiskManager:
    @pytest.fixture
    def risk_manager(self, mock_config):
        return RiskManager(mock_config['risk_management'])

    def test_stop_loss_calculation(self, risk_manager):
        entry_price = 100
        stop_loss = risk_manager.calculate_stop_loss(entry_price)
        assert stop_loss == 95  # 5% от 100

    def test_trailing_stop_update(self, risk_manager):
        current_price = 110
        highest_price = 115
        trailing_stop = risk_manager.update_trailing_stop(current_price, highest_price)
        expected = 115 * (1 - 0.03)  # 3% trailing stop
        assert trailing_stop == pytest.approx(expected)

    def test_leverage_check(self, risk_manager):
        time_to_close = timedelta(hours=1)
        volume_ratio = 1.5
        atr_ratio = 0.02
        probability = risk_manager.calculate_leverage_probability(time_to_close, volume_ratio, atr_ratio)
        assert 0 <= probability <= 1