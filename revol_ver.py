import argparse
from logging import Logger
from pathlib import Path
import json

from lib.outputs import OutputsDB, OutputsExcel, OutputsCsv
from lib.models import TransactionModel, AuthData
from lib.inputs import Inputs
from lib.web_requests import WebRequests
from lib.logg import Logging

abs_root_path = Path(__file__).parent
logger: Logger


def read_inputs(source: str, period: str, epoch: int) -> tuple[list[dict], int]:
    transactions: list = []
    count: int = 0
    if source == 'web_request':
        auth_data: AuthData | None = Inputs.get_auth_data(abs_root_path)
        if not auth_data:
            return transactions, count
            
        if period == 'month':
            transactions = WebRequests.get_monthly_transactions(auth_data,                                                                                                                                                                                                                                                                
                                                                epoch=epoch)
        elif period == 'all':
            transactions = WebRequests.get_all_transactions(auth_data,
                                                            account_type=account_type)
    elif source == 'file':
        transactions = Inputs.read_json_file(abs_root_path, 'rev.json')
    count = len(transactions)
    return transactions, count

def id_to_custom_category(custom_categories_map: dict, cat: str) -> str:
    'Translates custom category UUID to category defined in config.ini'
    if len(cat.split('-')) != 5:   # detects uuid
        return cat
    return custom_categories_map.get(cat)

def process(trans: list[dict], period: str, month: int, existing_ids: list[str] = None) -> tuple[list[dict], int]:
    if existing_ids is None:
        existing_ids = []
    count_all = len(trans)
    duplicates = []
    transactions = []
    not_correct_month = []
    custom_categories_map = Inputs.get_ini_config('custom.categories')
    for t in trans:
        if pretty_cat := id_to_custom_category(custom_categories_map, 
                                               cat=t['category']):
            logger.debug(f'Resolved category ID {t["category"]} to {pretty_cat}')
            t['category'] = pretty_cat
        else:
            raise Exception(f'\nCategory with ID {t["category"]} was not found. Full transaction:\n{json.dumps(t, indent=4)}')

        transaction = TransactionModel(**t)
        if transaction.legId in existing_ids:
            duplicates.append(transaction.legId)
            continue
        if period == 'month' and transaction.startedDate.month != month:
            not_correct_month.append(transaction.legId)
            continue
        transactions.append(transaction)
        existing_ids.append(transaction.legId)
    count_success = len(transactions)
    Logging.log_process(duplicates, not_correct_month, count_all, count_success)
    return [t.__dict__ for t in transactions], count_success

def write_outputs(transactions: list[dict], options: argparse.Namespace, db_output: OutputsDB, output_filename: str | None) -> None:
    if 'excel' in options.output:
        OutputsExcel.to_file(transactions, options.date, options.period, abs_root_path, options.escape_newlines, output_filename)
    if 'csv' in options.output:
        OutputsCsv.to_file(transactions, options.date, options.period, abs_root_path, options.escape_newlines, output_filename)
    if 'db' in options.output:
        db_output.to_db(transactions)

def db_instance_and_existing_records(dont_deduplicate: bool,
                                     output: list[str]) -> tuple[list[str] | None, OutputsDB | None]:
    '''
    DB is not needed if user only wants to use excel output and they
    never specified SQL as output. This prevents creating empty database.
    Also if user specified dont_deduplicate flag, then the existing database
    is not needed.
    '''
    if dont_deduplicate: # allowed only with file output
        logger.info('Database is not needed because deduplication is turned off')
        return [], None

    db_file = abs_root_path / 'trans_db.sql'
    if not Path(db_file).exists() and 'db' not in output:
        logger.info('Database is not needed because output is file and DB does not yet exist')
        return [], None

    db_output = OutputsDB(str(db_file))
    existing_ids = db_output.read_existing_records()
    return existing_ids, db_output

def main() -> None:
    options = Inputs.get_options()
    transactions, count = read_inputs(options.source, options.period, options.epoch)
    if count == 0:
        return
    existing_ids, db_output = db_instance_and_existing_records(options.dont_deduplicate,
                                                               options.output)
    transactions, count = process(transactions, options.period, options.month, existing_ids)
    if count == 0:
        return
    write_outputs(transactions, options, db_output, options.filename)

def run() -> None:
    global logger
    logger = Logging.setup_logging()
    main()

if __name__ == '__main__':  # pragma: no cover
    run()
