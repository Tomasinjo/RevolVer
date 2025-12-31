import pytest
import requests
import sys
from lib.web_requests import WebRequests

def test_fetch_trans_success(mocker):
    mock_response = mocker.Mock()
    mock_response.json.return_value = [{'id': 't1'}]
    mocker.patch('requests.get', return_value=mock_response)
    
    # Test with to_param and account_type to cover lines 34 and 38
    res = WebRequests.fetch_trans(cookie='c', device_id='d', wallet_id='w1', account_type='personal', to_param=123)
    assert res == [{'id': 't1'}]
    
    args, kwargs = requests.get.call_args
    assert kwargs['params']['to'] == 123
    assert 'accountType=personal' in kwargs['headers']['referer']

def test_fetch_trans_pocket_id(mocker):
    mock_response = mocker.Mock()
    mock_response.json.return_value = []
    mocker.patch('requests.get', return_value=mock_response)
    
    WebRequests.fetch_trans(cookie='c', device_id='d', pocket_id='p1')
    args, kwargs = requests.get.call_args
    assert kwargs['params']['internalPocketId'] == 'p1'
    assert 'accountId=p1' in kwargs['headers']['referer']

def test_fetch_trans_both_ids(mocker):
    mock_response = mocker.Mock()
    mock_response.json.return_value = []
    mocker.patch('requests.get', return_value=mock_response)
    
    WebRequests.fetch_trans(cookie='c', device_id='d', pocket_id='p1', wallet_id='w1')
    args, kwargs = requests.get.call_args
    assert 'walletId=w1&pocketId=p1' in kwargs['headers']['referer']

def test_fetch_trans_failure(mocker):
    mock_response = mocker.Mock()
    mock_response.json.return_value = {'error': 'unauthorized'}
    mocker.patch('requests.get', return_value=mock_response)
    mocker.patch('sys.exit', side_effect=SystemExit(1))
    
    with pytest.raises(SystemExit):
        WebRequests.fetch_trans(cookie='c', device_id='d')

def test_get_monthly_transactions(mocker):
    # Don't mock fetch_trans here to get coverage if we want, 
    # but we already covered it in test_fetch_trans_success
    mock_fetch = mocker.patch('lib.web_requests.WebRequests.fetch_trans', return_value=[])
    WebRequests.get_monthly_transactions('c', 'd', 123456)
    mock_fetch.assert_called_with(cookie='c', device_id='d', pocket_id='', wallet_id='', account_type='', to_param=123456)

def test_generate_dates(mocker):
    mocker.patch('lib.inputs.Inputs.get_ini_config', return_value={'allimportlookbackyears': '1'})
    import datetime as dt_mod
    mock_now = mocker.patch('lib.web_requests.datetime')
    mock_now.now.return_value = dt_mod.datetime(2024, 2, 1)
    
    mocker.patch('lib.inputs.Inputs.month_to_epoch', side_effect=lambda x: ('', 1000, int(x.split('.')[1])))
    
    dates = WebRequests.generate_dates()
    assert len(dates) == 13

def test_get_all_transactions(mocker):
    mocker.patch('lib.web_requests.WebRequests.generate_dates', return_value=[1, 2])
    mock_fetch = mocker.patch('lib.web_requests.WebRequests.fetch_trans', side_effect=[[{'id': '1'}], [{'id': '2'}]])
    
    res = WebRequests.get_all_transactions('c', 'd')
    assert len(res) == 2
    assert mock_fetch.call_count == 2