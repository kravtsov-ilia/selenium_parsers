import os

from selenium_parsers.utils.selenium_loggers import setup_logger


def setup_fb_logger() -> None:
    log_file = os.environ.get('FACEBOOK_PARSER_LOG_FILE')
    setup_logger(log_file, 'facebook_parser')
