import requests
from .inputs import Inputs
from datetime import datetime
import logging
import sys
import re
import os

logger = logging.getLogger('revol_ver')

class WebRequests:

    MAX_PAGES_PER_MONTH = 50

    @classmethod
    def load_headers_from_curl(cls) -> dict:
        '''
        Parse headers from curlcmd.txt file
        Returns a dictionary of headers extracted from the curl command
        '''
        curl_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'curlcmd.txt')
        headers = {}

        try:
            with open(curl_file, 'r') as f:
                content = f.read()

            # Match all -H 'header-name: header-value' patterns
            # Handles quoted values that may contain special characters
            pattern = r"-H\s+'([^:]+):\s*(.+?)'\s*\\"
            matches = re.findall(pattern, content)

            for header_name, header_value in matches:
                headers[header_name.strip()] = header_value.strip()

            logger.debug(f'Loaded {len(headers)} headers from curlcmd.txt')
            return headers
        except FileNotFoundError:
            logger.warning(f'curlcmd.txt not found at {curl_file}, using default headers')
            return {}

    @classmethod
    def fetch_pockets(cls, cookie: str, device_id: str) -> list[dict]:
        '''Every pocket on the profile, as the web app lists them.

        One transactions request only ever covers the account whose id it carries,
        so exporting a whole profile means knowing every pocket id. The web app
        reads them from the wallet endpoint; so does this.
        '''
        url = "https://app.revolut.com/api/retail/user/current/wallet"
        headers = cls.load_headers_from_curl()
        headers['cookie'] = cookie
        headers['x-device-id'] = device_id
        response = requests.get(url, headers=headers, allow_redirects=True).json()
        if not isinstance(response, dict) or 'pockets' not in response:
            print('')
            logger.error(f'Fetching pockets failed, got response\n{response}')
            sys.exit(1)
        pockets = [p for p in response['pockets'] if p.get('id')]
        logger.info(f'Wallet lists {len(pockets)} pockets')
        return pockets

    @classmethod
    def fetch_trans(cls, cookie: str, device_id: str, pocket_id:str = '', wallet_id: str = '', account_type: str = '', to_param: int = 0) -> list[dict]:
        '''
        Simulates a request made by Revolut web app
        '''
        url = "https://app.revolut.com/api/retail/user/current/transactions/last"
        
        params = {
            "count": 500,
        }

        referer_account_param = ''
        if wallet_id:
            params["walletId"] = wallet_id
            referer_account_param = f'walletId={wallet_id}'
            if pocket_id: # If both walletId and pocketId are present, add pocketId to referer
                referer_account_param += f'&pocketId={pocket_id}'
        elif pocket_id:
            params["internalPocketId"] = pocket_id
            referer_account_param = f'accountId={pocket_id}'


        if to_param != 0:
            params['to'] = to_param

        referer_base = 'https://app.revolut.com/home'
        if account_type:
            referer_base += f'?accountType={account_type}&{referer_account_param}'
        elif referer_account_param:
            referer_base += f'?{referer_account_param}'

        # Load headers from curlcmd.txt
        headers = cls.load_headers_from_curl()

        # Override with runtime parameters
        headers['cookie'] = cookie
        headers['referer'] = referer_base
        headers['x-device-id'] = device_id

        logger.debug(f'Headers used for fetch:\n{headers}')
        response = requests.get(url, headers=headers, params=params, allow_redirects=True).json()
        if isinstance(response, dict):
            print('')
            logger.error(f'Fetching failed, got response\n{response}')
            sys.exit(1)
        for t in response:
            if "card" in t:
                t["cardLastFour"] = t["card"].get("lastFour", "")
                t["cardLabel"] = t["card"].get("label", "")
        return response

    @classmethod
    def get_monthly_transactions(cls, cookie: str, device_id: str, epoch: int, pocket_id:str = '', wallet_id: str = '', account_type: str = '') -> list[dict]:
        logger.info('Fetching monthly transactions')
        return cls.fetch_month(cookie=cookie, device_id=device_id, epoch=epoch, pocket_id=pocket_id, wallet_id=wallet_id, account_type=account_type)

    @classmethod
    def fetch_month(cls, cookie: str, device_id: str, epoch: int, pocket_id:str = '', wallet_id: str = '', account_type: str = '') -> list[dict]:
        '''
        Revolut returns a limited number of transactions per request (about 140,
        whatever "count" asks for), so one request may not reach back to the start
        of a busy month. Keep requesting older pages until the month is covered.
        '''
        last_day = datetime.fromtimestamp(epoch / 1000)
        month_start = int(last_day.replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp()) * 1000
        transactions = []
        seen = set()
        to_param = epoch
        for _ in range(cls.MAX_PAGES_PER_MONTH):
            page = cls.fetch_trans(cookie=cookie, device_id=device_id, pocket_id=pocket_id, wallet_id=wallet_id, account_type=account_type, to_param=to_param)
            new = [t for t in page if cls.trans_key(t) not in seen]
            if not new:
                break
            for t in new:
                seen.add(cls.trans_key(t))
            transactions += new
            oldest = min((t['startedDate'] for t in page if t.get('startedDate')), default=None)
            if oldest is None or oldest < month_start or oldest >= to_param:
                break
            to_param = oldest
        else:
            logger.warning(f'Stopped after {cls.MAX_PAGES_PER_MONTH} pages; the start of the month may be missing')
        return transactions

    @staticmethod
    def trans_key(t: dict) -> tuple:
        return (t.get('id'), t.get('legId'))

    @classmethod
    def get_all_transactions(cls, cookie: str, device_id: str, pocket_id:str = '', wallet_id: str = '', account_type: str = '') -> list[dict]:
        '''
        Revolut will take epoch and return certain number of results BEFORE this date.
        This function generates epochs for each month and fetches transactions
        '''
        transactions = []
        logger.info('Fetching all transactions')
        seen = set()
        for epoch in cls.generate_dates():
            for t in cls.fetch_month(cookie=cookie, device_id=device_id, epoch=epoch, pocket_id=pocket_id, wallet_id=wallet_id, account_type=account_type):
                if cls.trans_key(t) not in seen:
                    seen.add(cls.trans_key(t))
                    transactions.append(t)
        return transactions

    @classmethod
    def generate_dates(cls) -> list[int]:
        '''
        Generates epochs for all months from current to the whatever is set in config.ini
        '''
        now = datetime.now()
        end_year = now.year
        start_year = end_year - int(Inputs.get_ini_config('other').get('allimportlookbackyears', 2))
        end_month = now.month
        logger.info(f'Preparing epoch timestamps of last day of month for months between years {start_year} and {end_year}')
        dates = []
        for y in range(start_year, end_year + 1):
            for m in range(1,13):
                if y == end_year and m > end_month:
                    break
                _, epoch, _ = Inputs.month_to_epoch(f'{y}.{m}')
                dates.append(epoch)
        return dates
