from selenium_parsers.utils.constants import TIKTOK_PARSER_LOG_FILE
from selenium_parsers.utils.selenium_loggers import setup_logger


def setup_tiktok_logger() -> None:
    setup_logger(
        log_file=TIKTOK_PARSER_LOG_FILE,
        logger_name='tiktok_parser'
    )
