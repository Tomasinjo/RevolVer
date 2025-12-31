import pytest
import pandas as pd
import sqlite3
import os
from pathlib import Path
from lib.outputs import OutputsDB, OutputsExcel, OutputsCsv, FileOutput

def test_outputs_db(tmp_path):
    db_file = str(tmp_path / 'test.db')
    out = OutputsDB(db_file)
    assert isinstance(out.conn, sqlite3.Connection)
    
    trans = [{'id': '1', 'legId': 'l1', 'amount': 10.0}]
    out.to_db(trans)
    
    records = out.read_existing_records()
    assert records == ['l1']

def test_outputs_db_no_table(tmp_path):
    db_file = str(tmp_path / 'test_empty.db')
    out = OutputsDB(db_file)
    records = out.read_existing_records()
    assert records == []

def test_outputs_excel(tmp_path, mocker):
    exports_dir = tmp_path / 'exports'
    exports_dir.mkdir()
    
    trans = [{'id': '1', 'legId': 'l1', 'amount': 10.0}]
    
    mock_to_excel = mocker.patch('pandas.DataFrame.to_excel')
    OutputsExcel.to_file(trans, '2023.12', 'month', tmp_path, False, 'my_export')
    mock_to_excel.assert_called_once()
    # Check filename
    args, kwargs = mock_to_excel.call_args
    file_path = args[0]
    assert str(file_path).endswith('my_export.xlsx')

def test_outputs_csv(tmp_path):
    exports_dir = tmp_path / 'exports'
    exports_dir.mkdir()
    
    trans = [{'id': '1', 'legId': 'l1', 'amount': 10.0, 'comment': 'line1\nline2'}]
    
    # Test with escape_newlines
    OutputsCsv.to_file(trans, '2023.12', 'month', tmp_path, True, 'my_csv')
    csv_file = exports_dir / 'my_csv.csv'
    assert csv_file.exists()
    content = csv_file.read_text()
    assert 'line1 line2' in content

def test_generate_filename_all():
    filename = OutputsCsv._generate_filename('any', 'all', None)
    assert '_export_all.csv' in filename

def test_generate_filename_month():
    filename = OutputsCsv._generate_filename('2023.12', 'month', None)
    assert '_export_month_2023_12.csv' in filename

def test_file_output_abstract():
    with pytest.raises(NotImplementedError):
        FileOutput.to_file([], 'd', 'p', Path('.'), False)