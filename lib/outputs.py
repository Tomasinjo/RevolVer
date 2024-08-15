import logging
import pandas as pd
import sqlite3
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger('revol_ver')

class OutputsDB:
    def __init__(self, db_file: str):
        self.conn = self.connect_to_db(db_file)
    
    def connect_to_db(self, db_file: str) -> sqlite3.Connection:
        c = sqlite3.connect(db_file)
        logger.info(f'Connected to database: {c}')
        return c
    
    def to_db(self, trans: list[dict]) -> None:
        df = pd.DataFrame(trans) 
        result = df.to_sql('raw_transactions', self.conn, if_exists='append', index=False)
        logger.info(f'Saved {result} records to DB!')

    def read_existing_records(self) -> list[str]:
        '''
        Returns list of legIds which should be global unique and
        are used to avoid writing duplicated values to outputs
        '''
        try:
            df = pd.read_sql('SELECT legId FROM raw_transactions', self.conn)
        except pd.errors.DatabaseError as e:
            logger.warning('Cannot find database file, will create new.')
            return []
        return df['legId'].tolist()
    
class OutputsExcel:
    @classmethod
    def generate_excel_filename(cls, date_arg: str, period: str) -> str:
        if period == 'all':
            date = period
        else:
            date = 'month_' + date_arg.replace('.', '_')
        now = re.sub(r'\W', '_', str(datetime.now()))
        return f'{now}_export_{date}.xlsx'

    @classmethod
    def to_excel(cls, trans: list[dict], date_arg: str, period: str, path: Path) -> None:
        filename = cls.generate_excel_filename(date_arg, period)
        df = pd.DataFrame(trans)
        file_location = path / 'exports' / filename
        df.to_excel(file_location, index=False)
        logger.info(f'Saved {len(df)} rows to file {filename}')