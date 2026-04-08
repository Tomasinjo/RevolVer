import pytest
from unittest.mock import patch, MagicMock
from lib.outputs import OutputsDB, OutputsExcel, OutputsCsv
import pandas as pd
from pathlib import Path
import re

class TestOutputsDB:
    @patch('sqlite3.connect')
    def test_connect(self, mock_connect):
        db = OutputsDB('test.db')
        mock_connect.assert_called_with('test.db')

    @patch('sqlite3.connect')
    @patch('pandas.DataFrame.to_sql')
    def test_to_db(self, mock_to_sql, mock_connect):
        db = OutputsDB('test.db')
        trans = [{'id': 1}]
        db.to_db(trans)
        mock_to_sql.assert_called()
        args, kwargs = mock_to_sql.call_args
        assert args[0] == 'raw_transactions'
        assert kwargs['if_exists'] == 'append'

    @patch('sqlite3.connect')
    @patch('pandas.read_sql')
    def test_read_existing_records(self, mock_read_sql, mock_connect):
        db = OutputsDB('test.db')
        mock_df = pd.DataFrame({'legId': ['l1', 'l2']})
        mock_read_sql.return_value = mock_df
        
        ids = db.read_existing_records()
        assert ids == ['l1', 'l2']

    @patch('sqlite3.connect')
    @patch('pandas.read_sql')
    def test_read_existing_records_error(self, mock_read_sql, mock_connect):
        db = OutputsDB('test.db')
        mock_read_sql.side_effect = pd.errors.DatabaseError
        
        ids = db.read_existing_records()
        assert ids == []

class TestOutputsExcel:
    @patch('pandas.DataFrame.to_excel')
    def test_to_file(self, mock_to_excel):
        trans = [{'id': 1}]
        path = MagicMock()
        path.__truediv__.return_value = path
        
        OutputsExcel.to_file(trans, '2023.01', 'month', path, False, 'myfile')
        mock_to_excel.assert_called()
    
    @patch('pandas.DataFrame.to_excel')
    def test_filename_generation(self, mock_to_excel):
        trans = [{'id': 1}]
        path = MagicMock()
        path.__truediv__.return_value = path
        
        # Test with explicit filename
        OutputsExcel.to_file(trans, '2023.01', 'month', path, False, 'explicit')
        
        # Test period=all
        OutputsExcel.to_file(trans, '2023.01', 'all', path, False, None)
        
        # Test period=month
        OutputsExcel.to_file(trans, '2023.01', 'month', path, False, None)

    def test_abstract_method(self):
        from lib.outputs import FileOutput
        # Since it's abstract, we can't instantiate it. 
        # But we can call the method on the class if it's not strictly requiring instance (it is classmethod).
        # However, abstractmethod decorator might not enforce check on direct call, but on instantiation of subclass.
        # Wait, if I define a subclass that calls super().
        
        class Concrete(FileOutput):
            @classmethod
            def to_file(cls, trans, date, period, path, esc, fname=None):
                super().to_file(trans, date, period, path, esc, fname)
                
        with pytest.raises(NotImplementedError):
            Concrete.to_file([], '', '', MagicMock(), False)

class TestOutputsCsv:
    @patch('pandas.DataFrame.to_csv')
    def test_to_file(self, mock_to_csv):
        trans = [{'id': 'a\nb'}]
        path = MagicMock()
        path.__truediv__.return_value = path
        
        # Test escape newlines
        OutputsCsv.to_file(trans, '2023.01', 'month', path, escape_newlines=True, output_filename='mycsv')
        mock_to_csv.assert_called()
        
        # Test no escape
        OutputsCsv.to_file(trans, '2023.01', 'month', path, escape_newlines=False, output_filename='mycsv')
        
