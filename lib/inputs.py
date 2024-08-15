import logging
import json
import argparse
import calendar
import configparser
from datetime import datetime
from pathlib import Path

logger = logging.getLogger('revol_ver')

class Inputs:
    
    @classmethod
    def read_json_file(cls, abs_root_path: Path, filename: str) -> list[dict]:
        json_file = abs_root_path / 'consume' / filename
        logger.info(f'Reading JSON from {json_file}')
        with open(json_file, 'r', encoding='utf8') as f:
            file_contents = f.read()
            contents = json.loads(file_contents)
        return contents

    @classmethod
    def get_auth_data_from_har(cls, abs_root_path: Path) -> tuple[bool, str, str, str]:
        'Parses HAR file and finds authentication data'
        har = cls.read_json_file(abs_root_path, 'app.revolut.com.har')
        cookie: str = ''
        device_id: str = ''
        pocket_id: str = ''
        found = False
        for entr in har.get('log', {}).get('entries', []):
            request = entr.get('request', {})
            if 'current/transactions/last' in request.get('url', ''):
                for header in request.get('headers', []):
                    if header.get('name') == 'cookie':
                        cookie = header.get('value')
                    if header.get('name') == 'x-device-id':
                        device_id = header.get('value')
                for q in request.get('queryString'):
                    if q.get('name') == 'internalPocketId':
                        pocket_id = q.get('value')
                if cookie and device_id and pocket_id:
                    found = True
                    logger.info('Authentication data parsed successfully')
                    logger.debug(f'Authentication data: \ncookie: {cookie}\ndevice_id: {device_id}\npocket_id: {pocket_id}')
                    return found, cookie, device_id, pocket_id
        logger.error('Could not find authentication data from HAR file.')
        return found, cookie, device_id, pocket_id
    
    @classmethod
    def get_options(cls) -> argparse.Namespace:
        parser = argparse.ArgumentParser(
                        prog='revol_ver.py',
                        description='Saves transactions from Revolut to database or Excel')
        parser.add_argument('-p', '--period', choices=['month', 'all'], default='month')
        parser.add_argument('-s', '--source', choices=['web_request', 'file'], default='web_request')
        parser.add_argument('-d', '--date', help='Month and year (YYYY.MM), required for period "month"')
        parser.add_argument('-o', '--output', choices=['db', 'excel', 'all'], default='all', help='Output destinations')
        parser.add_argument('-dd', '--dont_deduplicate', action='store_true', help='Don\'t use database for deduplication')

        args = parser.parse_args()
        args.epoch = 0
        args.pocket_id = ''
        args.month = 0

        if args.period == 'month':
            if args.date is None:
                parser.error('--date must be specified when --source is "web_request".')
            message, epoch, month = cls.month_to_epoch(args.date)
            if epoch == 0:
                parser.error(message)
            args.epoch = epoch
            args.month = month

        if args.output == 'all':
            args.output = ['db', 'excel']
        else:
            args.output = [args.output]

        if 'db' in args.output and args.dont_deduplicate is True:
            parser.error('Cannot write to database without deduplication!')
        logger.debug(f'Parsed command line arguments: {args}')
        return args
    
    @classmethod
    def month_to_epoch(cls, i: str) -> tuple[str, int, int]:
        '''
        Takes date/month in format yyyy.mm and returns epoch of
        the last day of provided month
        '''
        message = ''
        epoch = 0
        try:
            year, month = i.split('.')
            month_i = int(month)
            year_i = int(year)
        except:
            message = '"{i}" is not in valid format (YYYY.MM)!'
            return message, epoch
        res = calendar.monthrange(year_i, month_i)
        last_day = res[1]
        dt_last_day = datetime(year_i, month_i, last_day, 23, 59, 59)
        return message, int(dt_last_day.timestamp()) * 1000, month_i
    
    @staticmethod
    def get_ini_config(cat: str) -> dict:
        config = configparser.ConfigParser()
        abs_root_path = Path(__file__).parent.parent / 'config.ini'
        config.read(abs_root_path)
        c = dict(config[cat])
        return c
