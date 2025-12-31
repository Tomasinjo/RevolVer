import pytest
from lib.inputs import Inputs
from pathlib import Path
import json
import os
import argparse
import sys

def test_get_ini_config(mocker):
    mock_config = {
        'other': {'allimportlookbackyears': '3', 'loglevel': 'DEBUG'},
        'custom.categories': {'uuid-1': 'Food'}
    }
    def mock_getitem(self, key): return mock_config[key]
    mocker.patch('configparser.ConfigParser.read', return_value=None)
    mocker.patch('configparser.ConfigParser.__getitem__', side_effect=mock_getitem, autospec=True)
    config = Inputs.get_ini_config('other')
    assert config['allimportlookbackyears'] == '3'

def test_month_to_epoch():
    message, epoch, month = Inputs.month_to_epoch('2023.12')
    assert message == ''
    assert month == 12
    assert epoch == 1704067199000

def test_month_to_epoch_invalid_format():
    message, epoch, month = Inputs.month_to_epoch('2023-12')
    assert 'is not in valid format' in message
    assert epoch == 0

def test_get_auth_data_from_curl_personal():
    curl_content = Path('tests/curlcmd_personal.txt').read_text()
    found, cookie, device_id, pocket_id, wallet_id, account_type = Inputs.get_auth_data_from_curl(curl_content)
    assert found is True
    assert pocket_id == '7b46c548-f696-4dd4-832b-3aefb424856c'
    assert account_type == ''

def test_get_auth_data_from_curl_joint():
    curl_content = Path('tests/curlcmd_joint.txt').read_text()
    found, cookie, device_id, pocket_id, wallet_id, account_type = Inputs.get_auth_data_from_curl(curl_content)
    assert found is True
    assert wallet_id == 'a87f1ba3-2225-464d-8b43-f2b5c63dd164'
    assert account_type == 'joint'

def test_get_auth_data_from_curl():
    curl_content = "curl 'https://app.revolut.com/api/transactions/last?walletId=w1' -H 'Cookie: c1' -H 'x-device-id: d1' -H 'referer: https://app.revolut.com/?accountType=joint'"
    found, cookie, device_id, pocket_id, wallet_id, account_type = Inputs.get_auth_data_from_curl(curl_content)
    assert found is True
    assert cookie == 'c1'
    assert account_type == 'joint'

def test_get_auth_data_from_curl_windows(mocker):
    curl_content = 'curl "https://app.revolut.com/api/transactions/last?internalPocketId=p1" ^\n -H "Cookie: c1" ^\n -H "x-device-id: d1"'
    found, cookie, device_id, pocket_id, wallet_id, account_type = Inputs.get_auth_data_from_curl(curl_content)
    assert found is True
    assert cookie == 'c1'
    assert pocket_id == 'p1'

def test_get_auth_data_from_curl_no_url():
    found, *args = Inputs.get_auth_data_from_curl("no curl here")
    assert found is False

def test_get_auth_data_from_curl_missing_data():
    curl_content = "curl 'https://example.com'" 
    found, *args = Inputs.get_auth_data_from_curl(curl_content)
    assert found is False

def test_get_auth_data_from_curl_linux_fallback():
    curl_content = "curl 'https://example.com?walletId=w1' -b 'c1' -H 'x-device-id: d1'"
    found, cookie, *args = Inputs.get_auth_data_from_curl(curl_content)
    assert cookie == 'c1'

def test_get_auth_data_from_har(mocker):
    mock_har = {
        "log": {
            "entries": [
                {
                    "request": {
                        "url": "https://app.revolut.com/api/current/transactions/last",
                        "headers": [
                            {"name": "cookie", "value": "c1"},
                            {"name": "x-device-id", "value": "d1"},
                            {"name": "Referer", "value": "https://app.revolut.com/?accountType=personal"}
                        ],
                        "queryString": [
                            {"name": "internalPocketId", "value": "p1"},
                            {"name": "walletId", "value": "w1"}
                        ]
                    }
                }
            ]
        }
    }
    mocker.patch('lib.inputs.Inputs.read_json_file', return_value=mock_har)
    found, cookie, device_id, pocket_id, wallet_id, account_type = Inputs.get_auth_data_from_har(Path('.'))
    assert found is True
    assert pocket_id == 'p1'
    assert account_type == 'personal'

def test_get_auth_data_from_har_no_match(mocker):
    mock_har = {"log": {"entries": []}}
    mocker.patch('lib.inputs.Inputs.read_json_file', return_value=mock_har)
    found, *args = Inputs.get_auth_data_from_har(Path('.'))
    assert found is False

def test_read_json_file(tmp_path):
    consume_dir = tmp_path / 'consume'
    consume_dir.mkdir()
    json_file = consume_dir / 'test.json'
    data = [{"test": "value"}]
    json_file.write_text(json.dumps(data))
    content = Inputs.read_json_file(tmp_path, 'test.json')
    assert content == data

def test_read_json_file_not_found(tmp_path, mocker):
    mocker.patch('sys.exit', side_effect=SystemExit(1))
    with pytest.raises(SystemExit):
        Inputs.read_json_file(tmp_path, 'nonexistent.json')

def test_get_auth_data_curl_success(tmp_path, mocker):
    curl_file = tmp_path / 'curlcmd.txt'
    curl_file.write_text("curl 'https://example.com?walletId=w1' -H 'Cookie: c1' -H 'x-device-id: d1'")
    found, cookie, device_id, pocket_id, wallet_id, account_type = Inputs.get_auth_data(tmp_path)
    assert found is True

def test_get_auth_data_har_fallback(tmp_path, mocker):
    # This triggers the failure case in read_json_file when HAR is not found
    mocker.patch('sys.exit', side_effect=SystemExit(1))
    with pytest.raises(SystemExit):
        Inputs.get_auth_data(tmp_path)

def test_get_auth_data_curl_exception(tmp_path, mocker):
    curl_file = tmp_path / 'curlcmd.txt'
    curl_file.write_text("curl ...")
    mocker.patch('lib.inputs.open', side_effect=Exception("err"))
    mocker.patch('lib.inputs.Inputs.get_auth_data_from_har', return_value=(False, '', '', '', '', ''))
    Inputs.get_auth_data(tmp_path)

def test_get_options_all(mocker):
    mocker.patch('sys.argv', ['revol_ver.py', '-p', 'all', '-o', 'all', '-d', '2023.12'])
    args = Inputs.get_options()
    assert 'db' in args.output

def test_get_options_month_fail_epoch(mocker):
    mocker.patch('sys.argv', ['revol_ver.py', '-p', 'month', '-d', 'invalid', '-o', 'csv'])
    with pytest.raises(SystemExit):
        Inputs.get_options()

def test_get_options_db_no_dedup(mocker):
    mocker.patch('sys.argv', ['revol_ver.py', '-o', 'db', '-dd', '-d', '2023.12'])
    with pytest.raises(SystemExit):
        Inputs.get_options()

def test_get_options_month_no_date(mocker):
    mocker.patch('sys.argv', ['revol_ver.py', '-p', 'month'])
    with pytest.raises(SystemExit):
        Inputs.get_options()
