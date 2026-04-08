import pytest
from unittest.mock import patch, MagicMock
import logging
from lib.logg import Logging

class TestLogging:
    @patch('lib.inputs.Inputs.get_ini_config')
    def test_setup_logging(self, mock_get_ini):
        mock_get_ini.return_value = {'loglevel': 'DEBUG'}
        # We need to reload logging or just check the logger returned.
        # basicConfig might have already run in other tests or main.
        # But setup_logging calls it.
        
        logger = Logging.setup_logging()
        assert logger.name == 'revol_ver'
        # The level is set on the logger instance
        assert logger.level == logging.DEBUG
        mock_get_ini.assert_called_with('other')

    @patch('logging.getLogger')
    def test_log_process(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        Logging.log_process(
            duplicates=['d1', 'd2'],
            not_correct_month=['n1'],
            count_all=10,
            count_success=7
        )
        
        # Verify calls
        # duplicates warning
        assert any("Skipped 2 out of 10" in str(c) for c in mock_logger.warning.call_args_list)
        # duplicates debug
        assert any("Duplicated legIds" in str(c) for c in mock_logger.debug.call_args_list)
        
        # not_correct_month warning
        assert any("Skipped 1 out of 10" in str(c) for c in mock_logger.warning.call_args_list)
        
        mock_logger.info.assert_called_with('Found 7 transactions')

    @patch('logging.getLogger')
    def test_log_process_zero_success(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        Logging.log_process([], [], 10, 0)
        
        mock_logger.warning.assert_called_with('No transactions to save, quitting..')
