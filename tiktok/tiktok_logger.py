import os

from selenium_parsers.utils.selenium_loggers import setup_logger


def setup_tiktok_logger() -> None:
    log_file = os.environ.get('TIKTOK_PARSER_LOG_FILE')
    setup_logger(
        log_file=log_file,
        logger_name='tiktok_parser'
    )
