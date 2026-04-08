import pytest
from unittest.mock import patch, MagicMock
from lib.web_requests import WebRequests
import sys
from datetime import datetime

class TestWebRequests:

    @patch('requests.get')
    def test_fetch_trans(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = [{'id': 1}]
        mock_get.return_value = mock_response
        
        res = WebRequests.fetch_trans(
            cookie='c', device_id='d', pocket_id='p', wallet_id='w', account_type='a'
        )
        assert res == [{'id': 1}]
        
        args, kwargs = mock_get.call_args
        # Check logic: if wallet_id provided, it takes precedence in params
        assert kwargs['params']['walletId'] == 'w'
        assert 'internalPocketId' not in kwargs['params'] 

    @patch('requests.get')
    def test_fetch_trans_pocket_only(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        WebRequests.fetch_trans('c', 'd', pocket_id='p')
        
        args, kwargs = mock_get.call_args
        assert kwargs['params']['internalPocketId'] == 'p'
        assert 'walletId' not in kwargs['params']

    @patch('requests.get')
    def test_fetch_trans_no_ids(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        WebRequests.fetch_trans('c', 'd')
        
        args, kwargs = mock_get.call_args
        assert 'internalPocketId' not in kwargs['params']
        assert 'walletId' not in kwargs['params']

    @patch('requests.get')
    def test_fetch_trans_fail(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {'error': 'failed'}
        mock_get.return_value = mock_response
        
        with patch('sys.exit') as mock_exit:
             WebRequests.fetch_trans('c', 'd')
             mock_exit.assert_called_with(1)

    @patch('requests.get')
    def test_fetch_trans_with_to(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        WebRequests.fetch_trans('c', 'd', to_param=123)
        
        args, kwargs = mock_get.call_args
        assert kwargs['params']['to'] == 123

    @patch('requests.get')
    def test_fetch_trans_wallet_no_pocket(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        WebRequests.fetch_trans('c', 'd', wallet_id='w1')
        
        args, kwargs = mock_get.call_args
        assert kwargs['params']['walletId'] == 'w1'
        assert 'pocketId' not in kwargs['params'].get('referer', '') 

    @patch('lib.web_requests.WebRequests.fetch_trans')
    def test_get_monthly_transactions(self, mock_fetch):
        mock_fetch.return_value = []
        WebRequests.get_monthly_transactions('c', 'd', 12345)
        mock_fetch.assert_called_with(cookie='c', device_id='d', pocket_id='', wallet_id='', account_type='', to_param=12345)

    @patch('lib.web_requests.WebRequests.fetch_trans')
    @patch('lib.web_requests.WebRequests.generate_dates')
    def test_get_all_transactions(self, mock_gen_dates, mock_fetch):
        mock_gen_dates.return_value = [1000, 2000]
        mock_fetch.return_value = [{'id': 1}]
        
        trans = WebRequests.get_all_transactions('c', 'd')
        # fetch_trans called twice. 
        # returns [{'id':1}] each time.
        # trans += ...
        # Result should be [{'id':1}, {'id':1}]
        assert len(trans) == 2
        assert trans == [{'id': 1}, {'id': 1}]

    def test_generate_dates(self):
        with patch('lib.inputs.Inputs.get_ini_config', return_value={'allimportlookbackyears': 1}):
             # Patch datetime in lib.web_requests so .now() is controlled
             with patch('lib.web_requests.datetime') as mock_datetime:
                 # mock_datetime must also implement year, month etc or return a mock that does
                 # Using a real datetime object for return value
                 fixed_now = datetime(2023, 1, 15)
                 mock_datetime.now.return_value = fixed_now

                 dates = WebRequests.generate_dates()
                 # 2022: 12 months.
                 # 2023: Jan is included (current month)
                 assert len(dates) == 13
