import argparse
from logging import Logger
from pathlib import Path

from lib.outputs import OutputsDB, OutputsExcel, OutputsCsv
from lib.models import TransactionModel, UnknownCategoryError
from lib.inputs import Inputs
from lib.web_requests import WebRequests
from lib.logg import Logging

logger: Logger


def read_inputs(source: str, period: str, epoch: int,
                lookback_years: int | None = None) -> tuple[list[dict], int]:
    transactions: list = []
    count: int = 0
    if source == 'web_request':
        found, cookie, device_id, pocket_id, wallet_id, account_type = Inputs.get_auth_data(abs_root_path)
        if not found:
            return transactions, count
        if period == 'month':
            transactions = WebRequests.get_monthly_transactions(cookie=cookie,
                                                                device_id=device_id,
                                                                pocket_id=pocket_id,
                                                                wallet_id=wallet_id,
                                                                account_type=account_type,
                                                                epoch=epoch)
        elif period == 'all':
            transactions = WebRequests.get_all_transactions(cookie=cookie,
                                                            device_id=device_id,
                                                            pocket_id=pocket_id,
                                                            wallet_id=wallet_id,
                                                            account_type=account_type,
                                                            lookback_years=lookback_years)
    elif source == 'file':
        transactions = Inputs.read_json_file(abs_root_path, 'rev.json')
    count = len(transactions)
    return transactions, count

def process(trans: list[dict], period: str, month: int, existing_ids: list[str] = None) -> tuple[list[dict], int]:
    if existing_ids is None:
        existing_ids = []
    count_all = len(trans)
    duplicates = []
    transactions = []
    not_correct_month = []
    unknown_categories: set[str] = set()
    for t in trans:
        try:
            transaction = TransactionModel(**t)
        except UnknownCategoryError as exc:
            unknown_categories.add(exc.category_id)
            continue
        if transaction.legId in existing_ids:
            duplicates.append(transaction.legId)
            continue
        if period == 'month' and transaction.startedDate.month != month:
            not_correct_month.append(transaction.legId)
            continue
        transactions.append(transaction)
        existing_ids.append(transaction.legId)
    if unknown_categories:
        listing = '\n'.join(f'{cat} = your_category_name' for cat in sorted(unknown_categories))
        raise UnknownCategoryError(
            f'{len(unknown_categories)} custom category ID(s) are not defined in config.ini. '
            f'Add them all under [custom.categories] and run again:\n{listing}'
        )
    count_success = len(transactions)
    Logging.log_process(duplicates, not_correct_month, count_all, count_success)
    return [t.__dict__ for t in transactions], count_success

MONEY_FIELDS = ('amount', 'fee', 'balance', 'amountWithCharges', 'counterpart_amount')

# Currencies whose smallest unit is not 1/100. Everything else is assumed to have
# two decimal places, which covers the currencies Revolut holds balances in.
CURRENCY_EXPONENT = {
    'BIF': 0, 'CLP': 0, 'DJF': 0, 'GNF': 0, 'ISK': 0, 'JPY': 0, 'KMF': 0, 'KRW': 0,
    'PYG': 0, 'RWF': 0, 'UGX': 0, 'UYI': 0, 'VND': 0, 'VUV': 0, 'XAF': 0, 'XOF': 0,
    'XPF': 0,
    'BHD': 3, 'IQD': 3, 'JOD': 3, 'KWD': 3, 'LYD': 3, 'OMR': 3, 'TND': 3,
}
DEFAULT_EXPONENT = 2

def to_decimal_amounts(transactions: list[dict]) -> list[dict]:
    '''Convert the monetary fields from the currency's smallest unit, so 4000 is
    written as 40.00.

    Revolut returns money in the smallest unit and the export keeps it that way by
    default (issue #18). This is opt-in for anyone who wants the decimal amount.
    The divisor follows the currency: most have two decimal places, but JPY has
    none and KWD has three, and dividing those by 100 would be wrong.
    '''
    for transaction in transactions:
        divisor = 10 ** CURRENCY_EXPONENT.get(transaction.get('currency'), DEFAULT_EXPONENT)
        counterpart_divisor = 10 ** CURRENCY_EXPONENT.get(
            transaction.get('counterpart_currency'), DEFAULT_EXPONENT)
        for field in MONEY_FIELDS:
            value = transaction.get(field)
            if value is None:
                continue
            field_divisor = counterpart_divisor if field == 'counterpart_amount' else divisor
            transaction[field] = value / field_divisor if field_divisor != 1 else value
    return transactions

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
    transactions, count = read_inputs(options.source, options.period, options.epoch,
                                      options.lookback_years)
    if count == 0:
        return
    existing_ids, db_output = db_instance_and_existing_records(options.dont_deduplicate,
                                                               options.output)
    transactions, count = process(transactions, options.period, options.month, existing_ids)
    if count == 0:
        return
    if options.decimal_amounts:
        transactions = to_decimal_amounts(transactions)
    write_outputs(transactions, options, db_output, options.filename)

if __name__ == '__main__': # pragma: no cover
    abs_root_path = Path(__file__).parent
    logger = Logging.setup_logging()
    main()
