import logging
import json
import argparse
import calendar
import configparser
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import sys

logger = logging.getLogger('revol_ver')

class Inputs:

    @classmethod
    def read_json_file(cls, abs_root_path: Path, filename: str) -> list[dict]:
        json_file = abs_root_path / 'consume' / filename
        logger.info(f'Reading JSON from {json_file}')
        if not json_file.exists():
            print('')
            logger.error(f'Both methods of providing authentication data failed. Please refer to readme to understand how use curl or HAR method.')
            sys.exit(1)
        
        with open(json_file, 'r', encoding='utf8') as f:
            file_contents = f.read()
            contents = json.loads(file_contents)
        return contents

    @classmethod
    def get_auth_data(cls, abs_root_path: Path) -> tuple[bool, str, str, str, str, str]:
        'Detects input format and parses authentication data from either HAR or curl command'
        
        # First, try to read curlcmd.txt to see if it contains a curl command
        input_file = abs_root_path / 'curlcmd.txt'
        logger.info(f'Reading curl command from {input_file}')
        if input_file.exists() and input_file.stat().st_size > 0:
            try:
                with open(input_file, 'r', encoding='utf8') as f:
                    content = f.read().strip()
                    content_commentless = '\n'.join([
                        line for line in content.split('\n')
                        if line.strip()
                        and not line.startswith('#')
                    ])
                    if content_commentless.startswith('curl'):
                        logger.info('Detected curl command in curlcmd.txt')
                        return cls.get_auth_data_from_curl(curl_content=content_commentless)

            except Exception as e:
                logger.warning(f'Error reading curlcmd.txt: {e}')
        
        # Fall back to HAR file parsing
        logger.info('Using HAR file for authentication data')
        found, cookie, device_id, pocket_id, wallet_id, account_type = cls.get_auth_data_from_har(abs_root_path)
        return found, cookie, device_id, pocket_id, wallet_id, account_type

    @classmethod
    def get_auth_data_from_curl(cls, curl_content: str) -> tuple[bool, str, str, str, str, str]:
        'Parses curl command from curlcmd.txt and extracts authentication data'
        # Remove all ^ characters (Windows CMD line continuation)
        curl_content = curl_content.replace('^\\^"', '"')
        curl_content = curl_content.replace('^"', "'")
        curl_content = curl_content.replace(' ^', '')
        
        cookie: str = ''
        device_id: str = ''
        pocket_id: str = ''
        wallet_id: str = ''
        account_type: str = ''
        
        # Extract URL - works for both bash ('url') and cmd ("url")
        url_match = re.search(r"curl\s+['\"]([^'\"]+)", curl_content)
        if not url_match:
            logger.error('Could not find URL in curl command')
            return False, '', '', '', '', ''
        
        url = url_match.group(1)
        
        # Extract pocket_id from URL query parameters
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        if 'internalPocketId' in query_params:
            pocket_id = query_params['internalPocketId'][0]
        if 'walletId' in query_params:
            wallet_id = query_params['walletId'][0]

        # Extract cookie data using -b flag (takes precedence over -H Cookie)
        # cookie = re.compile(r"-b\s+'([^']+)" )
        if cookie_match := re.search(r"-b\s+'([^']+)'", curl_content):
            cookie = cookie_match.group(1)
        elif cookie_match := re.search(r"'Cookie:\s+([^']+)", curl_content): # fallback for linux/firefox combo
            cookie = cookie_match.group(1)

        # Extract device_id from -H headers
        device_id_match = re.search(r"x-device-id:\s+([^']+)", curl_content)
        if device_id_match:
            device_id = device_id_match.group(1)

        # Extract accountType from referer header
        referer_match = re.search(r"referer:\s+'[^?]+\?accountType=([^&]+)", curl_content)
        if referer_match:
            account_type = referer_match.group(1)
        
        if cookie and device_id and (pocket_id or wallet_id):
            logger.info('Authentication data parsed successfully from curl command')
            logger.debug(f'Authentication data: \ncookie length: {len(cookie)}\ndevice_id: {device_id}\npocket_id: {pocket_id}\nwallet_id: {wallet_id}\naccount_type: {account_type}')
            return True, cookie, device_id, pocket_id, wallet_id, account_type
        
        logger.error(f'Could not find all required authentication data from curl command. Found: cookie={bool(cookie)}, device_id={bool(device_id)}, pocket_id={bool(pocket_id)}, wallet_id={bool(wallet_id)}')
        return False, cookie, device_id, pocket_id, wallet_id, account_type

    @classmethod
    def get_auth_data_from_har(cls, abs_root_path: Path) -> tuple[bool, str, str, str, str, str]:
        'Parses HAR file and finds authentication data'
        har = cls.read_json_file(abs_root_path, 'app.revolut.com.har')
        cookie: str = ''
        device_id: str = ''
        pocket_id: str = ''
        wallet_id: str = ''
        account_type: str = ''
        found = False
        for entr in har.get('log', {}).get('entries', []):
            request = entr.get('request', {})
            if 'current/transactions/last' in request.get('url', ''):
                for header in request.get('headers', []):
                    if header.get('name') in ('Cookie', 'cookie'): # depends on browser
                        cookie = header.get('value')
                    if header.get('name') == 'x-device-id':
                        device_id = header.get('value')
                    if header.get('name') == 'Referer':
                        referer_url = header.get('value')
                        parsed_referer = urlparse(referer_url)
                        referer_query_params = parse_qs(parsed_referer.query)
                        if 'accountType' in referer_query_params:
                            account_type = referer_query_params['accountType'][0]

                for q in request.get('queryString'):
                    if q.get('name') == 'internalPocketId':
                        pocket_id = q.get('value')
                    if q.get('name') == 'walletId':
                        wallet_id = q.get('value')

                if cookie and device_id and (pocket_id or wallet_id):
                    found = True
                    logger.info('Authentication data parsed successfully')
                    logger.debug(f'Authentication data: \ncookie: {cookie}\ndevice_id: {device_id}\npocket_id: {pocket_id}\nwallet_id: {wallet_id}\naccount_type: {account_type}')
                    return found, cookie, device_id, pocket_id, wallet_id, account_type
        logger.error('Could not find authentication data from HAR file.')
        return found, cookie, device_id, pocket_id, wallet_id, account_type

    @classmethod
    def get_options(cls) -> argparse.Namespace:
        parser = argparse.ArgumentParser(
                        prog='revol_ver.py',
                        description='Saves transactions from Revolut to database or Excel')
        parser.add_argument('-p', '--period', choices=['month', 'all'], default='month')
        parser.add_argument('-s', '--source', choices=['web_request', 'file'], default='web_request')
        parser.add_argument('-d', '--date', help='Month and year (YYYY.MM), required for period "month"')
        parser.add_argument('-o', '--output', choices=['db', 'excel', 'csv', 'all'], default='all', help='Output destinations')
        parser.add_argument('-f', '--filename', help='Specify the output filename (without extension)')
        parser.add_argument('-dd', '--dont_deduplicate', action='store_true', help='Don\'t use database for deduplication')
        parser.add_argument('-en', '--escape-newlines', action='store_true', help='Escape newlines in CSV output')

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
            args.output = ['db', 'excel', 'csv']
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
            return message, epoch, 0
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
