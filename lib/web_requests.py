import requests
from .inputs import Inputs
from .models import AuthData
from datetime import datetime
import logging
import sys

logger = logging.getLogger('revol_ver')

class WebRequests:

    @classmethod
    def fetch_trans(cls, auth_data: AuthData, to_param: int = 0) -> list[dict]:
        '''
        Simulates a request made by Revolut web app
        '''
        url = "https://app.revolut.com/api/retail/user/current/transactions/last"
        
        params = {
            "count": 500,
        }

        referer_account_param = ''
        if auth_data.wallet_id:
            params["walletId"] = auth_data.wallet_id
            referer_account_param = f'walletId={auth_data.wallet_id}'
            if auth_data.pocket_id: # If both walletId and pocketId are present, add pocketId to referer
                referer_account_param += f'&pocketId={auth_data.pocket_id}'
        elif auth_data.pocket_id:
            params["internalPocketId"] = auth_data.pocket_id
            referer_account_param = f'accountId={auth_data.pocket_id}'


        if to_param != 0:
            params['to'] = to_param

        referer_base = 'https://app.revolut.com/home'
        if auth_data.account_type:
            referer_base += f'?accountType={auth_data.account_type}&{referer_account_param}'
        elif referer_account_param:
            referer_base += f'?{referer_account_param}'


        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9,sl;q=0.8',
            'cookie': auth_data.cookie,
            'priority': 'u=1, i',
            'referer': referer_base,
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Microsoft Edge";v="126"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0',
            'x-browser-application': 'WEB_CLIENT',
            'x-client-geo-location': '41.056946,11.505751',
            'x-client-version': '100.0',
            'x-device-id': auth_data.device_id
        }

        logger.debug(f'Headers used for fetch:\n{headers}')
        response = requests.get(url, headers=headers, params=params, allow_redirects=True).json()
        if isinstance(response, dict):
            print('')
            logger.error(f'Fetching failed, got response\n{response}')
            sys.exit(1)
        return response

    @classmethod
    def get_monthly_transactions(cls, auth_data: AuthData, epoch:int) -> list[dict]:
        logger.info('Fetching monthly transactions')
        return cls.fetch_trans(auth_data, to_param=epoch)

    @classmethod
    def get_all_transactions(cls, auth_data: AuthData) -> list[dict]:
        '''
        Revolut will take epoch and return certain number of results BEFORE this date.
        This function generates epochs for each month and fetches transactions
        '''
        transactions = []
        logger.info('Fetching all transactions')
        for epoch in cls.generate_dates():
            transactions += cls.fetch_trans(auth_data, to_param=epoch)
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
                if y == end_year and m == end_month:
                    break
                _, epoch, _ = Inputs.month_to_epoch(f'{y}.{m}')
                dates.append(epoch)
        return dates
