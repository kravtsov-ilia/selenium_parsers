import logging
import os

format_string = '%(levelname)s %(asctime)s %(pathname)s in Line: %(lineno)d Process id: %(process)d %(message)s'
log_level = logging.INFO
logging.basicConfig(format=format_string, level=log_level, datefmt='%Y-%m-%d %I:%M:%S')
log_file = os.environ.get('FACEBOOK_PARSER_LOG_FILE')
file_handler = logging.FileHandler(log_file)
logging.root.addHandler(file_handler)
logger = logging.getLogger('selenium_parser')
