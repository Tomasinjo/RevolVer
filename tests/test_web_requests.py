import pytest
from unittest.mock import patch, MagicMock, mock_open
from lib.web_requests import WebRequests
import sys
from datetime import datetime

class TestWebRequests:

    def test_load_headers_from_curl(self):
        curl_content = """curl 'https://app.revolut.com/api/retail/user/current/transactions/last?count=50' \\
  -H 'accept: application/json, text/plain, */*' \\
  -H 'accept-language: en-US,en;q=0.9' \\
  -H 'priority: u=1, i' \\
  -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0' \\
"""

        with patch('builtins.open', mock_open(read_data=curl_content)):
            headers = WebRequests.load_headers_from_curl()
            assert len(headers) == 4
            assert headers['accept'] == 'application/json, text/plain, */*'
            assert headers['accept-language'] == 'en-US,en;q=0.9'
            assert headers['priority'] == 'u=1, i'
            assert headers['user-agent'] == 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0'

    def test_load_headers_from_curl_file_not_found(self):
        with patch('builtins.open', side_effect=FileNotFoundError):
            headers = WebRequests.load_headers_from_curl()
            assert headers == {}

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
    def test_fetch_month_pages_back_to_month_start(self, mock_fetch):
        # July 2026; each page stops short of the 1st until the third
        epoch = int(datetime(2026, 7, 31, 23, 59, 59).timestamp()) * 1000
        day = lambda d: int(datetime(2026, 7, d, 12).timestamp()) * 1000
        june = int(datetime(2026, 6, 30, 12).timestamp()) * 1000
        mock_fetch.side_effect = [
            [{'id': 'a', 'legId': 'a1', 'startedDate': day(20)}, {'id': 'b', 'legId': 'b1', 'startedDate': day(8)}],
            [{'id': 'b', 'legId': 'b1', 'startedDate': day(8)}, {'id': 'c', 'legId': 'c1', 'startedDate': day(4)}],
            [{'id': 'd', 'legId': 'd1', 'startedDate': day(1)}, {'id': 'e', 'legId': 'e1', 'startedDate': june}],
        ]
        trans = WebRequests.fetch_month('c', 'd', epoch)
        assert [t['id'] for t in trans] == ['a', 'b', 'c', 'd', 'e']
        assert [c.kwargs['to_param'] for c in mock_fetch.call_args_list] == [epoch, day(8), day(4)]

    @patch('lib.web_requests.WebRequests.fetch_trans')
    def test_fetch_month_stops_when_no_progress(self, mock_fetch):
        epoch = int(datetime(2026, 7, 31, 23, 59, 59).timestamp()) * 1000
        page = [{'id': 'a', 'legId': 'a1', 'startedDate': int(datetime(2026, 7, 20).timestamp()) * 1000}]
        mock_fetch.return_value = page
        trans = WebRequests.fetch_month('c', 'd', epoch)
        assert trans == page
        assert mock_fetch.call_count == 2

    @patch('lib.web_requests.WebRequests.fetch_trans')
    def test_fetch_month_without_dates(self, mock_fetch):
        mock_fetch.return_value = [{'id': 'a'}]
        assert WebRequests.fetch_month('c', 'd', 1785535199000) == [{'id': 'a'}]
        assert mock_fetch.call_count == 1

    @patch('lib.web_requests.WebRequests.fetch_trans')
    def test_fetch_month_page_limit(self, mock_fetch):
        epoch = int(datetime(2026, 7, 31, 23, 59, 59).timestamp()) * 1000
        n = iter(range(10**6))
        mock_fetch.side_effect = lambda **kw: [{'id': next(n), 'startedDate': kw['to_param'] - 1000}]
        with patch.object(WebRequests, 'MAX_PAGES_PER_MONTH', 3):
            trans = WebRequests.fetch_month('c', 'd', epoch)
        assert len(trans) == 3

    @patch('lib.web_requests.WebRequests.fetch_month')
    @patch('lib.web_requests.WebRequests.generate_dates')
    def test_get_all_transactions(self, mock_gen_dates, mock_fetch):
        mock_gen_dates.return_value = [1000, 2000]
        mock_fetch.side_effect = [[{'id': 1, 'legId': 'x'}], [{'id': 1, 'legId': 'x'}, {'id': 2, 'legId': 'y'}]]
        trans = WebRequests.get_all_transactions('c', 'd')
        # The same leg fetched for two months is kept once
        assert trans == [{'id': 1, 'legId': 'x'}, {'id': 2, 'legId': 'y'}]

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

    def test_fetch_pockets_returns_every_pocket_id(self):
        'The wallet endpoint supplies the ids one request cannot reach.'
        with patch('lib.web_requests.WebRequests.load_headers_from_curl', return_value={}):
            with patch('lib.web_requests.requests.get') as mock_get:
                mock_get.return_value.json.return_value = {'pockets': [
                    {'id': 'p1', 'type': 'CURRENT', 'currency': 'CHF', 'state': 'ACTIVE'},
                    {'id': 'p2', 'type': 'SAVINGS', 'currency': 'EUR', 'state': 'INACTIVE'},
                    {'type': 'SAVINGS', 'currency': 'USD'},
                ]}
                pockets = WebRequests.fetch_pockets(cookie='c', device_id='d')
        assert [p['id'] for p in pockets] == ['p1', 'p2']

    def test_fetch_pockets_error_response_exits(self, caplog):
        'An error payload stops the run instead of exporting nothing silently.'
        with patch('lib.web_requests.WebRequests.load_headers_from_curl', return_value={}):
            with patch('lib.web_requests.requests.get') as mock_get:
                mock_get.return_value.json.return_value = {'message': 'Access token expired',
                                                           'code': 9039}
                with pytest.raises(SystemExit) as exc:
                    WebRequests.fetch_pockets(cookie='c', device_id='d')
        assert exc.value.code == 1
        assert 'Access token expired' in caplog.text

    def test_fetch_trans_flattens_card_fields(self):
        'Card details from #20 are flattened onto the row.'
        with patch('lib.web_requests.WebRequests.load_headers_from_curl', return_value={}):
            with patch('lib.web_requests.requests.get') as mock_get:
                mock_get.return_value.json.return_value = [
                    {'id': '1', 'card': {'lastFour': '4321', 'label': 'Main card'}},
                    {'id': '2'},
                ]
                rows = WebRequests.fetch_trans(cookie='c', device_id='d', wallet_id='w')
        assert rows[0]['cardLastFour'] == '4321'
        assert 'cardLastFour' not in rows[1]
