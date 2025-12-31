import pytest
import logging
from lib.logg import Logging

def test_setup_logging(mocker):
    mocker.patch('lib.inputs.Inputs.get_ini_config', return_value={'loglevel': 'DEBUG'})
    logger = Logging.setup_logging()
    assert logger.level == logging.DEBUG
    assert logger.name == 'revol_ver'

def test_setup_logging_default(mocker):
    mocker.patch('lib.inputs.Inputs.get_ini_config', return_value={})
    logger = Logging.setup_logging()
    assert logger.level == logging.INFO

def test_log_process(mocker):
    logger = logging.getLogger('revol_ver')
    mock_warning = mocker.patch.object(logger, 'warning')
    mock_info = mocker.patch.object(logger, 'info')
    
    Logging.log_process(duplicates=['id1'], not_correct_month=['id2'], count_all=10, count_success=8)
    mock_warning.assert_any_call('Skipped 1 out of 10 transactions because they are already in the database')
    mock_warning.assert_any_call('Skipped 1 out of 10 transactions because they are outside of target period')
    mock_info.assert_called_with('Found 8 transactions')

def test_log_process_no_success(mocker):
    logger = logging.getLogger('revol_ver')
    mock_warning = mocker.patch.object(logger, 'warning')
    Logging.log_process(duplicates=[], not_correct_month=[], count_all=0, count_success=0)
    mock_warning.assert_called_with('No transactions to save, quitting..')