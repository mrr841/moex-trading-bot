import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import pandas as pd
from src.data_handler import MoexDataHandler, TinkoffDataHandler
from src.trade_executor import TradeExecutor

class TestBrokerIntegration:
    @pytest.fixture
    def mock_moex_response(self):
        return {
            "candles": [
                {"open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 1000, "end": "2023-01-01T10:00:00Z"},
                {"open": 100.5, "high": 102, "low": 100, "close": 101.5, "volume": 1500, "end": "2023-01-01T10:01:00Z"}
            ]
        }

    @pytest.fixture
    def mock_tinkoff_portfolio(self):
        return {
            "total_amount_shares": 10000,
            "positions": [
                {"ticker": "SBER", "balance": 10, "average_price": 250},
                {"ticker": "GAZP", "balance": 5, "average_price": 180}
            ]
        }

    @patch('src.data_handler.requests.get')
    def test_moex_api_integration(self, mock_get, mock_moex_response):
        mock_get.return_value.json.return_value = mock_moex_response
        
        handler = MoexDataHandler()
        data = handler.get_candles('SBER', '1min', 2)
        
        assert not data.empty
        assert data.iloc[0]['close'] == 100.5
        assert len(data) == 2
        mock_get.assert_called_once()

    @patch('src.trade_executor.TinkoffApiClient')
    def test_tinkoff_trade_execution(self, mock_client, mock_tinkoff_portfolio):
        mock_client.return_value.get_portfolio.return_value = mock_tinkoff_portfolio
        mock_client.return_value.send_order.return_value = {"order_id": "12345", "status": "filled"}
        
        executor = TradeExecutor(api_client=mock_client())
        portfolio = executor.get_portfolio()
        order_result = executor.send_order(ticker="SBER", operation="buy", quantity=5)
        
        assert portfolio['total_amount_shares'] == 10000
        assert len(portfolio['positions']) == 2
        assert order_result['order_id'] == "12345"
        mock_client.return_value.send_order.assert_called_once()

    @patch('src.trade_executor.TinkoffApiClient')
    def test_overnight_position_closing(self, mock_client):
        mock_client.return_value.get_orders.return_value = []
        mock_client.return_value.send_order.return_value = {"order_id": "67890", "status": "filled"}
        
        executor = TradeExecutor(api_client=mock_client())
        executor.close_leveraged_positions()
        
        assert mock_client.return_value.send_order.call_count == 0  # Нет позиций с плечом
        
        # Добавляем мок позиции с плечом
        mock_client.return_value.get_portfolio.return_value = {
            "positions": [{"ticker": "SBER", "balance": 10, "leveraged": True}]
        }
        executor.close_leveraged_positions()
        mock_client.return_value.send_order.assert_called_once()