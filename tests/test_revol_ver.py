import pytest
from unittest.mock import patch, MagicMock
import revol_ver
import argparse

from pathlib import Path

# Setup globals required by revol_ver functions
# Use a real-looking path but mock it if necessary in specific tests.
# Using /tmp or similar is safer than MagicMock string conversion.
revol_ver.abs_root_path = Path("/tmp/revol_ver_test")
revol_ver.logger = MagicMock()

class TestRevolVer:
    
    @patch('lib.inputs.Inputs.get_auth_data')
    @patch('lib.web_requests.WebRequests.get_monthly_transactions')
    def test_read_inputs_web_monthly(self, mock_get_monthly, mock_get_auth):
        mock_get_auth.return_value = (True, 'c', 'd', 'p', 'w', 'a')
        mock_get_monthly.return_value = [{'id': 1}]
        
        trans, count = revol_ver.read_inputs('web_request', 'month', 123)
        
        assert count == 1
        assert trans == [{'id': 1}]
        mock_get_monthly.assert_called_with(cookie='c', device_id='d', pocket_id='p', wallet_id='w', account_type='a', epoch=123)

    @patch('lib.inputs.Inputs.get_auth_data')
    @patch('lib.web_requests.WebRequests.get_all_transactions')
    def test_read_inputs_web_all(self, mock_get_all, mock_get_auth):
        mock_get_auth.return_value = (True, 'c', 'd', 'p', 'w', 'a')
        mock_get_all.return_value = [{'id': 1}, {'id': 2}]
        
        trans, count = revol_ver.read_inputs('web_request', 'all', 0)
        
        assert count == 2
        mock_get_all.assert_called()

    @patch('lib.inputs.Inputs.get_auth_data')
    def test_read_inputs_web_auth_fail(self, mock_get_auth):
        mock_get_auth.return_value = (False, '', '', '', '', '')
        
        trans, count = revol_ver.read_inputs('web_request', 'month', 123)
        assert count == 0

    @patch('lib.inputs.Inputs.read_json_file')
    def test_read_inputs_file(self, mock_read_json):
        mock_read_json.return_value = [{'id': 1}]
        
        trans, count = revol_ver.read_inputs('file', 'month', 0)
        assert count == 1

    @patch('lib.logg.Logging.log_process')
    def test_process(self, mock_log):
        # We need actual TransactionModel logic or mock it?
        # process() creates TransactionModel(**t).
        # Better to use real dicts that satisfy TransactionModel
        # BUT TransactionModel uses validation.
        
        # startedDate must be > 0 to be converted to datetime.
        raw_trans = [{
            'id': '1', 'legId': 'l1', 'type': 'T', 'state': 'S', 
            'currency': 'C', 'amount': 10, 'tag': 't', 'category': 'c', 
            'account': {'id': 'a'}, 'startedDate': 1000
        }]
        
        # Test dedup
        existing_ids = ['l1']
        
        processed, count = revol_ver.process(raw_trans, 'month', 1, existing_ids)
        assert count == 0 # Duplicate
        
        # Test valid
        raw_trans[0]['legId'] = 'l2'
        # Test month filter
        # startedDate 1000 -> 1970-01-01 00:00:01 (UTC) -> Month 1.
        # if period='month' and month=1. Should match.
        processed, count = revol_ver.process(raw_trans, 'month', 1, existing_ids)
        assert count == 1
        assert processed[0]['legId'] == 'l2'
        assert 'l2' in existing_ids

        # Test month filter mismatch
        # startedDate 1000 is Jan. if month=2?
        processed, count = revol_ver.process(raw_trans, 'month', 2, existing_ids)
        assert count == 0

    @patch('lib.outputs.OutputsExcel.to_file')
    @patch('lib.outputs.OutputsCsv.to_file')
    def test_write_outputs(self, mock_csv, mock_excel):
        options = argparse.Namespace(
            output=['excel', 'csv', 'db'], 
            date='2023.01', period='month', 
            escape_newlines=False, filename=None
        )
        db_output = MagicMock()
        
        revol_ver.write_outputs([{'id':1}], options, db_output, None)
        
        mock_excel.assert_called()
        mock_csv.assert_called()
        db_output.to_db.assert_called()

    @patch('revol_ver.OutputsDB')
    def test_db_instance_and_existing_records(self, mock_outputs_db):
        # case 1: dont_deduplicate
        res = revol_ver.db_instance_and_existing_records(True, ['file'])
        assert res == ([], None)
        
        # case 2: db file not exists and 'db' not in output
        # mock exists?
        with patch('pathlib.Path.exists', return_value=False):
             res = revol_ver.db_instance_and_existing_records(False, ['file'])
             assert res == ([], None)

        # case 3: normal
        mock_db_instance = MagicMock()
        mock_outputs_db.return_value = mock_db_instance
        mock_db_instance.read_existing_records.return_value = ['l1']
        
        with patch('pathlib.Path.exists', return_value=True):
            ids, db = revol_ver.db_instance_and_existing_records(False, ['db'])
            assert ids == ['l1']
            assert db == mock_db_instance

    @patch('revol_ver.Inputs.get_options')
    @patch('revol_ver.read_inputs')
    @patch('revol_ver.db_instance_and_existing_records')
    @patch('revol_ver.process')
    @patch('revol_ver.write_outputs')
    def test_main(self, mock_write, mock_process, mock_db_func, mock_read, mock_opts):
        mock_opts.return_value = argparse.Namespace(
            source='s', period='p', epoch=0, month=0, 
            dont_deduplicate=False, output=['o'], filename='f'
        )
        mock_read.return_value = ([{}], 1)
        mock_db_func.return_value = ([], MagicMock())
        mock_process.return_value = ([{}], 1)
        
        revol_ver.main()
        
        mock_write.assert_called()

    @patch('lib.logg.Logging.log_process')
    def test_process_incorrect_month(self, mock_log):
        # Transaction in month 2, but we want month 1
        raw_trans = [{
            'id': '1', 'legId': 'l1', 'type': 'T', 'state': 'S', 
            'currency': 'C', 'amount': 10, 'tag': 't', 'category': 'c', 
            'account': {'id': 'a'}, 
            'startedDate': 2678400000000 # ~Feb 1970 approx
        }]
        
        # 2678400000000 is way in future? 
        # 1 month in ms = 30 * 24 * 3600 * 1000 = 2,592,000,000.
        # Let's use simpler math. 1970-02-01 is 31 days after epoch.
        # 31 * 24 * 3600 * 1000 = 2678400000.
        
        feb_ts = 2678400000 + 1000 # Feb 1st 1970 00:00:01
        
        raw_trans[0]['startedDate'] = feb_ts
        
        processed, count = revol_ver.process(raw_trans, 'month', 1, [])
        assert count == 0

    @patch('lib.logg.Logging.log_process')
    def test_process_none_existing_ids(self, mock_log):
        raw_trans = [{
            'id': '1', 'legId': 'l1', 'type': 'T', 'state': 'S', 
            'currency': 'C', 'amount': 10, 'tag': 't', 'category': 'c', 
            'account': {'id': 'a'}, 'startedDate': 1000
        }]
        processed, count = revol_ver.process(raw_trans, 'month', 1, None)
        assert count == 1
        
    @patch('lib.outputs.OutputsExcel.to_file')
    @patch('lib.outputs.OutputsCsv.to_file')
    def test_write_outputs_partial(self, mock_csv, mock_excel):
        # Test only db
        options = argparse.Namespace(
            output=['db'], 
            date='2023.01', period='month', 
            escape_newlines=False, filename=None
        )
        db_output = MagicMock()
        revol_ver.write_outputs([{'id':1}], options, db_output, None)
        mock_excel.assert_not_called()
        mock_csv.assert_not_called()
        db_output.to_db.assert_called()

        # Test only excel
        options.output = ['excel']
        revol_ver.write_outputs([{'id':1}], options, db_output, None)
        mock_excel.assert_called()
        
    def test_read_inputs_unknown_period(self):
        # Defensive test
        with patch('lib.inputs.Inputs.get_auth_data', return_value=(True,'','','','','')):
            trans, count = revol_ver.read_inputs('web_request', 'unknown', 0)
            assert count == 0

    def test_read_inputs_unknown_source(self):
        trans, count = revol_ver.read_inputs('unknown', 'month', 0)
        assert count == 0

    @patch('revol_ver.Inputs.get_options')
    @patch('revol_ver.read_inputs')
    @patch('revol_ver.db_instance_and_existing_records')
    @patch('revol_ver.process')
    @patch('revol_ver.write_outputs')
    def test_main_process_returns_zero(self, mock_write, mock_process, mock_db_func, mock_read, mock_opts):
        mock_opts.return_value = argparse.Namespace(
            source='s', period='p', epoch=0, month=0, 
            dont_deduplicate=False, output=['o'], filename='f'
        )
        mock_read.return_value = ([{}], 1)
        mock_db_func.return_value = ([], MagicMock())
        mock_process.return_value = ([], 0) # Zero count
        
        revol_ver.main()
        
        mock_write.assert_not_called()

    @patch('revol_ver.Inputs.get_options')
    @patch('revol_ver.read_inputs')
    def test_main_no_inputs(self, mock_read, mock_opts):
        mock_opts.return_value = argparse.Namespace(source='s', period='p', epoch=0)
        mock_read.return_value = ([], 0)
        
        revol_ver.main()
        # Should return early
