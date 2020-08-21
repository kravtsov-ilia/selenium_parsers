import os

from selenium_parsers.utils.selenium_loggers import setup_logger


def setup_ok_logger() -> None:
    log_file = os.environ.get('OK_PARSER_LOG_FILE')
    setup_logger(
        log_file=log_file,
        logger_name='odnoklassniki_parser'
    )
