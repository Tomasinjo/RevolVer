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
from .models import AuthData


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
    def get_auth_data(cls, abs_root_path: Path) -> AuthData|None:
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
                        auth_data = cls.get_auth_data_from_curl(curl_content=content_commentless)
                        if auth_data: # IMPORTANT: Return here if successful
                            return auth_data

            except Exception as e:
                logger.warning(f'Error reading curlcmd.txt: {e}')
        
        # Fall back to HAR file parsing
        logger.info('Using HAR file for authentication data')
        auth_data = cls.get_auth_data_from_har(abs_root_path)
        return auth_data

    @classmethod
    def get_auth_data_from_curl(cls, curl_content: str) -> AuthData|None:
        'Parses curl command from curlcmd.txt and extracts authentication data'
        # Remove all ^ characters (Windows CMD line continuation)
        curl_content = curl_content.replace('^\\^"', '"').replace('^"', "'")
        curl_content = re.sub(r'\^\s+', '', curl_content)
        print(curl_content)

        # Extract URL - works for both bash ('url') and cmd ("url")
        url_match = re.search(r"curl\s+['\"]([^'\"]+)", curl_content)
        if not url_match:
            logger.error('Could not find URL in curl command')
            return None

        # Extract pocket_id from URL query parameters
        parsed_url = urlparse(url_match.group(1))
        query_params = parse_qs(parsed_url.query)

        data = {
            "pocket_id": query_params.get('internalPocketId', [''])[0],
            "wallet_id": query_params.get('walletId', [''])[0], # only joint accounts
            "cookie": "",
            "device_id": "",
            "account_type": ""
        }

        # Extract cookie data using -b flag (takes precedence over -H Cookie)
        # cookie = re.compile(r"-b\s+'([^']+)" )
        if cookie_match := re.search(r"-b\s+'([^']+)'", curl_content):
            data["cookie"] = cookie_match.group(1)
        elif cookie_match := re.search(r"-b\s+\"([^\"]+)\"", curl_content):
            data["cookie"] = cookie_match.group(1)
        elif cookie_match := re.search(r"[']Cookie:\s+([^']+)", curl_content, re.IGNORECASE): # fallback for linux/firefox combo
            data["cookie"] = cookie_match.group(1)
        elif cookie_match := re.search(r"[\"]Cookie:\s+([^\"]+)", curl_content, re.IGNORECASE): # fallback for linux/firefox combo
            data["cookie"] = cookie_match.group(1)

        # Extract device_id from -H headers
        if device_id_match := re.search(r"x-device-id:\s+([^'\"]+)", curl_content, re.IGNORECASE):
            data["device_id"] = device_id_match.group(1).strip()

        # Extract accountType from referer header
        if referer_match := re.search(r"referer:\s+[^?]+\?accountType=([^&'\s]+)", curl_content):
            data["account_type"] = referer_match.group(1)
        
        if data["cookie"] and data["device_id"] and (data["pocket_id"] or data["wallet_id"]):
            logger.info('Authentication data parsed successfully from curl command')
            logger.debug(f'Authentication data: \n{data}')
            return AuthData.model_validate(data)
        
        logger.error(f'Could not find all required authentication data from curl command. Found:\n{data}')
        return None

    @classmethod
    def get_auth_data_from_har(cls, abs_root_path: Path) -> AuthData|None:
        'Parses HAR file and finds authentication data'
        har = cls.read_json_file(abs_root_path, 'app.revolut.com.har')
        data = {
            "pocket_id": "",
            "wallet_id": "",
            "cookie": "",
            "device_id": "",
            "account_type": ""
        }
        for entr in har.get('log', {}).get('entries', []):
            request = entr.get('request', {})
            if 'current/transactions/last' in request.get('url', ''):
                for header in request.get('headers', []):
                    if header.get('name') in ('Cookie', 'cookie'): # depends on browser
                        data['cookie'] = header.get('value')
                    if header.get('name') == 'x-device-id':
                        data['device_id'] = header.get('value')
                    if header.get('name') == 'Referer':
                        referer_url = header.get('value')
                        parsed_referer = urlparse(referer_url)
                        referer_query_params = parse_qs(parsed_referer.query)
                        if 'accountType' in referer_query_params:
                            data['account_type'] = referer_query_params['accountType'][0]

                for q in request.get('queryString'):
                    if q.get('name') == 'internalPocketId':
                        data['pocket_id'] = q.get('value')
                    if q.get('name') == 'walletId':
                        data['wallet_id'] = q.get('value')

                if data['cookie'] and data['device_id'] and (data['pocket_id'] or data['wallet_id']):
                    logger.info('Authentication data parsed successfully')
                    logger.debug(f'Authentication data: \n{data}')
                    return AuthData.model_validate(data)
        logger.error('Could not find authentication data from HAR file.')
        return None

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
        month = 0
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
        return message, int(calendar.timegm(dt_last_day.utctimetuple())) * 1000, month_i

    @staticmethod
    def get_ini_config(cat: str) -> dict:
        config = configparser.ConfigParser()
        abs_root_path = Path(__file__).parent.parent / 'config.ini'
        config.read(abs_root_path)
        c = dict(config[cat])
        return c
