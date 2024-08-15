import logging
from lib.inputs import Inputs

class Logging:
    @staticmethod
    def setup_logging() -> None:
        logging.basicConfig(
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()]
        )

        logger = logging.getLogger('revol_ver')
        level = Inputs.get_ini_config('other').get('loglevel', 'INFO')
        logger.setLevel(level)
        return logger
        
    @staticmethod
    def log_process(duplicates: list, 
                    not_correct_month: list, 
                    count_all: int, 
                    count_success: int) -> None:
        logger = logging.getLogger('revol_ver')
        if duplicates:
            logger.warning(f'Skipped {len(duplicates)} out of {count_all} transactions because they are already in the database')
            logger.debug(f'Duplicated legIds:\n{"\n".join(duplicates)}')
        if not_correct_month:
            logger.warning(f'Skipped {len(not_correct_month)} out of {count_all} transactions because they are outside of target period')
            logger.debug(f'Out of period legIds:\n{"\n".join(not_correct_month)}')
        logger.info(f'Found {count_success} transactions')
        if count_success == 0:
            logger.warning('No transactions to save, quitting..')