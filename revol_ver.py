import argparse
from pathlib import Path
from lib.outputs import OutputsDB, OutputsExcel
from lib.models import TransactionModel
from lib.inputs import Inputs
from lib.web_requests import WebRequests
from lib.logg import Logging


def read_inputs(source: str, period: str, epoch: int) -> tuple[list[dict], int]:
    transactions: list = []
    count: int = 0
    if source == 'web_request':
        found, cookie, device_id, pocket_id = Inputs.get_auth_data_from_har(abs_root_path)
        if not found:
            return transactions, count
        if period == 'month':
            transactions = WebRequests.get_monthly_transactions(cookie=cookie, 
                                                                device_id=device_id, 
                                                                pocket_id=pocket_id, 
                                                                epoch=epoch)
        elif period == 'all':
            transactions = WebRequests.get_all_transactions(cookie=cookie, 
                                                            device_id=device_id, 
                                                            pocket_id=pocket_id)
    elif source == 'file':
        transactions = Inputs.read_json_file(abs_root_path, 'rev.json')
    count = len(transactions)
    return transactions, count

def process(trans: list[dict], period: str, month: int, existing_ids: list[str] = []) -> tuple[list[dict], int]:
    count_all = len(trans)
    duplicates = []
    transactions = []
    not_correct_month = []
    for t in trans:
        transaction = TransactionModel(**t)
        if transaction.legId in existing_ids:
            duplicates.append(transaction.legId)
            continue
        if period == 'month' and transaction.startedDate.month != month:
            not_correct_month.append(transaction.legId)
            continue
        transactions.append(transaction)
    count_success = len(transactions)
    Logging.log_process(duplicates, not_correct_month, count_all, count_success)
    return [t.__dict__ for t in transactions], count_success

def write_outputs(transactions: list[dict], options: argparse.Namespace, db_output: OutputsDB) -> None:
    if 'excel' in options.output:
        OutputsExcel.to_excel(transactions, options.date, options.period, abs_root_path)
    if 'db' in options.output:
        db_output.to_db(transactions)

def db_instance_and_existing_records(dont_deduplicate: bool, output: list[str]) -> list:
    '''
    DB is not needed if user only wants to use excel output and they
    never specified SQL as output. This prevents creating empty database.
    Also if user specified dont_deduplicate flag, then the existing database
    is not needed. 
    '''
    existing_ids = []
    db_output = None
    if dont_deduplicate: # allowed only with excel output
        logger.info('Database is not needed because deduplication is turned off')
        return existing_ids, db_output
    db_file = abs_root_path / 'trans_db.sql'
    if not Path(db_file).exists() and 'excel' in output and len(output) == 1:
        logger.info('Database is not needed because output is excel and DB does not yet exist.')
        return existing_ids, db_output
    db_output = OutputsDB(db_file)
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
    write_outputs(transactions, options, db_output)

if __name__ == '__main__':
    abs_root_path = Path(__file__).parent
    logger = Logging.setup_logging()
    main()
