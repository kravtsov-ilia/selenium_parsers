import logging.config
import os

import environ

ENV = environ.Env(
    DJANGO_DEBUG=(bool, False)
)

DEBUG = ENV('DJANGO_DEBUG')
MAX_LOG_SIZE = 1024 * 1024 * 50


class DebugTrueFilter(logging.Filter):
    """
    Check container debug status, use for console logging
    """
    def filter(self, record):
        return DEBUG


class DebugFalseFilter(logging.Filter):
    """
    Check container debug status, use for file logging
    """
    def filter(self, record):
        return not DEBUG


def setup_fb_logger():
    """
    Setup logger for facebook parser script
    """
    log_file = os.environ.get('FACEBOOK_PARSER_LOG_FILE')
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    log_config = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'verbose': {
                'format':
                    '%(levelname)s %(asctime)s %(pathname)s in Line: %(lineno)d Process id: %(process)d %(message)s'
            },
            'simple': {
                'format': '%(pathname)s %(message)s'
            },
        },
        'filters': {
            'debug_false': {
                '()': 'selenium_parsers.facebook.facebook_logger.DebugFalseFilter',
            },
            'debug_true': {
                '()': 'selenium_parsers.facebook.facebook_logger.DebugTrueFilter',
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
                'filters': ['debug_true'],
            },
            'general': {
                'level': 'INFO',
                'filters': ['debug_false'],
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': log_file,
                'maxBytes': MAX_LOG_SIZE,
                'formatter': 'verbose'
            }
        },
        'root': {
            'level': 'DEBUG',
            'handlers': ['console', 'general'],
            'propagate': False
        },
        'loggers': {
            'facebook_parser': {
                'level': 'INFO',
                'handlers': ['console', 'general'],
                'propagate': False
            }
        }
    }

    logging.config.dictConfig(log_config)
