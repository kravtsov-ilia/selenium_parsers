import datetime
import logging
from typing import TYPE_CHECKING

import environ
import pymongo
import requests
from requests.auth import HTTPBasicAuth

from selenium_parsers.utils.general import webdriver_singleton, get_tuned_driver

if TYPE_CHECKING:
    from selenium.webdriver.chrome.webdriver import WebDriver


logger = logging.getLogger('selenium_worker')

# rabbitmq virtual host
VHOST_NAME = 'selenium_worker_posts'

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    USE_PROXY=(bool, True),
)
DEBUG = env('DJANGO_DEBUG')
USE_PROXY = env('USE_PROXY')
PROXY_IP = env('SELENIUM_WORKER_PROXY_IP')
PROXY_PORT = env('SELENIUM_WORKER_PROXY_PORT')
RABBIT_HOST = env('RABBIT_HOST')


@webdriver_singleton
def get_driver(server_name: str, pid_path: str) -> 'WebDriver':
    extra_params = {}
    if USE_PROXY:
        extra_params.update(proxy_ip=PROXY_IP, proxy_port=PROXY_PORT)
    return get_tuned_driver(
        parser_name=server_name,
        logger=logger,
        headless=(not DEBUG),
        **extra_params
    )


def create_vhost_if_not_exist():
    requests.put(
        f'http://{RABBIT_HOST}:15672/api/vhosts/{VHOST_NAME}',
        verify=False,
        auth=HTTPBasicAuth('guest', 'guest')
    )


def save_result(task_hash: str, link: str, data: dict) -> None:
    with pymongo.MongoClient('mongodb://mongo', 27017) as mongo_client:
        mongo_db = mongo_client['owl_project']['selenium_compare']
        mongo_db.insert_one({
            'task_hash': task_hash,
            'link': link,
            'result': data,
            'datetime': datetime.datetime.now()
        })
