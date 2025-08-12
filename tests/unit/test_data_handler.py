import pytest
from unittest.mock import patch
from src.data_handler import MoexDataHandler, TinkoffDataHandler

class TestDataHandler:
    @patch('src.data_handler.requests.get')
    def test_moex_data_loading(self, mock_get, sample_candles):
        mock_response = MagicMock()
        mock_response.json.return_value = {'candles': sample_candles.to_dict('records')}
        mock_get.return_value = mock_response

        handler = MoexDataHandler()
        data = handler.get_candles('SBER', '1min', 100)
        assert not data.empty
        assert 'close' in data.columns

    @patch('src.data_handler.TinkoffApiClient')
    def test_tinkoff_data_loading(self, mock_client, sample_candles):
        mock_client.return_value.get_candles.return_value = sample_candles
        handler = TinkoffDataHandler(api_client=mock_client())
        data = handler.get_candles('SBER', '1min', 100)
        assert not data.empty
        assert len(data) == 100