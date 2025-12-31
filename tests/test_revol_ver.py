import pytest
import revol_ver
from pathlib import Path
from unittest.mock import MagicMock
from datetime import datetime
import sys

def test_read_inputs_web_request_month(mocker):
    mocker.patch('revol_ver.Inputs.get_auth_data', return_value=(True, 'c', 'd', 'p', 'w', 'a'))
    mocker.patch('revol_ver.WebRequests.get_monthly_transactions', return_value=[{'id': '1'}])
    
    trans, count = revol_ver.read_inputs('web_request', 'month', 12345)
    assert count == 1
    assert trans == [{'id': '1'}]

def test_read_inputs_web_request_all(mocker):
    mocker.patch('revol_ver.Inputs.get_auth_data', return_value=(True, 'c', 'd', 'p', 'w', 'a'))
    mocker.patch('revol_ver.WebRequests.get_all_transactions', return_value=[{'id': '1'}])
    
    trans, count = revol_ver.read_inputs('web_request', 'all', 0)
    assert count == 1

def test_read_inputs_web_request_not_found(mocker):
    # Coverage for line 21 in revol_ver.py
    mocker.patch('revol_ver.Inputs.get_auth_data', return_value=(False, '', '', '', '', ''))
    trans, count = revol_ver.read_inputs('web_request', 'month', 12345)
    assert count == 0
    assert trans == []

def test_read_inputs_file(mocker):
    mocker.patch('revol_ver.Inputs.read_json_file', return_value=[{'id': '1'}])
    trans, count = revol_ver.read_inputs('file', 'month', 0)
    assert count == 1

def test_process(mocker):
    class MockTransaction:
        def __init__(self, leg_id, month):
            self.legId = leg_id
            self.startedDate = datetime(2023, month, 1)
        @property
        def __dict__(self):
            return {'legId': self.legId, 'startedDate': self.startedDate}
            
    mocker.patch('revol_ver.TransactionModel', side_effect=lambda **kwargs: MockTransaction('l1', 12))
    mocker.patch('revol_ver.Logging.log_process')
    
    # Test with existing_ids=None to cover line 42
    trans = [{'some': 'data'}]
    processed, count = revol_ver.process(trans, 'month', 12, existing_ids=None)
    assert count == 1
    assert processed[0]['legId'] == 'l1'

def test_process_duplicate(mocker):
    class MockTransaction:
        def __init__(self):
            self.legId = 'l1'
    mocker.patch('revol_ver.TransactionModel', return_value=MockTransaction())
    mocker.patch('revol_ver.Logging.log_process')
    
    trans = [{'some': 'data'}]
    processed, count = revol_ver.process(trans, 'month', 12, existing_ids=['l1'])
    assert count == 0

def test_process_wrong_month(mocker):
    class MockTransaction:
        def __init__(self):
            self.legId = 'l1'
            self.startedDate = datetime(2023, 11, 1)
    mocker.patch('revol_ver.TransactionModel', return_value=MockTransaction())
    mocker.patch('revol_ver.Logging.log_process')
    
    trans = [{'some': 'data'}]
    processed, count = revol_ver.process(trans, 'month', 12, existing_ids=[])
    assert count == 0

def test_write_outputs(mocker):
    mock_options = MagicMock(output=['excel', 'csv', 'db'], date='2023.12', period='month', escape_newlines=False, filename='test')
    mocker.patch('revol_ver.OutputsExcel.to_file')
    mocker.patch('revol_ver.OutputsCsv.to_file')
    mock_db = MagicMock()
    
    revol_ver.write_outputs([{}], mock_options, mock_db, 'test')
    revol_ver.OutputsExcel.to_file.assert_called_once()
    revol_ver.OutputsCsv.to_file.assert_called_once()
    mock_db.to_db.assert_called_once()

def test_db_instance_dont_deduplicate(mocker):
    revol_ver.logger = MagicMock()
    ids, db = revol_ver.db_instance_and_existing_records(True, ['excel'])
    assert ids == []
    assert db is None

def test_db_instance_needed(mocker, tmp_path):
    revol_ver.abs_root_path = tmp_path
    mocker.patch('revol_ver.OutputsDB')
    ids, db = revol_ver.db_instance_and_existing_records(False, ['db'])
    revol_ver.OutputsDB.assert_called_once()

def test_db_instance_not_needed(mocker, tmp_path):
    revol_ver.abs_root_path = tmp_path
    ids, db = revol_ver.db_instance_and_existing_records(False, ['excel'])
    assert ids == []
    assert db is None

def test_main_flow(mocker):
    mock_options = MagicMock(source='file', period='month', epoch=123, month=12, dont_deduplicate=True, output=['excel'], filename='f', date='d', escape_newlines=False)
    mocker.patch('revol_ver.Inputs.get_options', return_value=mock_options)
    mocker.patch('revol_ver.read_inputs', return_value=([{'id': '1'}], 1))
    mocker.patch('revol_ver.db_instance_and_existing_records', return_value=([], None))
    mocker.patch('revol_ver.process', return_value=([{'id': '1'}], 1))
    mocker.patch('revol_ver.write_outputs')
    
    revol_ver.main()
    revol_ver.write_outputs.assert_called_once()

def test_main_no_inputs(mocker):
    mock_options = MagicMock(source='file', period='month')
    mocker.patch('revol_ver.Inputs.get_options', return_value=mock_options)
    mocker.patch('revol_ver.read_inputs', return_value=([], 0))
    revol_ver.main()

def test_main_no_success_process(mocker):
    mock_options = MagicMock(source='file', period='month', epoch=123, month=12, dont_deduplicate=True, output=['excel'])
    mocker.patch('revol_ver.Inputs.get_options', return_value=mock_options)
    mocker.patch('revol_ver.read_inputs', return_value=([{'id': '1'}], 1))
    mocker.patch('revol_ver.db_instance_and_existing_records', return_value=([], None))
    mocker.patch('revol_ver.process', return_value=([], 0))
    revol_ver.main()

def test_run(mocker):
    mocker.patch('revol_ver.Logging.setup_logging')
    mocker.patch('revol_ver.main')
    revol_ver.run()
    revol_ver.Logging.setup_logging.assert_called_once()
