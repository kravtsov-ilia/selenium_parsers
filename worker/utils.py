import datetime
import logging
from typing import TYPE_CHECKING

import pymongo
import requests
from requests.auth import HTTPBasicAuth

from selenium_parsers.utils.constants import USE_PROXY, SELENIUM_WORKER_PROXY_IP, SELENIUM_WORKER_PROXY_PORT, \
    HEADLESS_SELENIUM_PARSERS, RABBIT_HOST
from selenium_parsers.utils.general import webdriver_singleton, get_tuned_driver
from selenium_parsers.utils.mongo_models import FacebookPostData

if TYPE_CHECKING:
    from selenium.webdriver.chrome.webdriver import WebDriver


logger = logging.getLogger('selenium_worker')

# rabbitmq virtual host
VHOST_NAME = 'selenium_worker_posts'


@webdriver_singleton
def get_driver(server_name: str, pid_path: str) -> 'WebDriver':
    extra_params = {}
    if USE_PROXY:
        extra_params.update(
            proxy_ip=SELENIUM_WORKER_PROXY_IP,
            proxy_port=SELENIUM_WORKER_PROXY_PORT
        )
    return get_tuned_driver(
        parser_name=server_name,
        logger=logger,
        headless=HEADLESS_SELENIUM_PARSERS,
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


def get_compare_data(
        link: str,
        likes: str,
        dislikes: str,
        comments: str,
        reposts: str,
        views: str,
        domain: str
) -> dict:
    return {
        'link': link,
        'likes': likes,
        'dislikes': dislikes,
        'comments': comments,
        'reposts': reposts,
        'views': views,
        'sn': domain
    }


def cast_facebook_compare_data(
        post_link: str,
        fb_data_object: 'FacebookPostData',
        domain: str
):
    return get_compare_data(
        link=post_link,
        likes=fb_data_object.likes_count,
        dislikes='-',
        comments=fb_data_object.comments_count,
        reposts=fb_data_object.shares_count,
        views='-',
        domain=domain,
    )


def cast_instagram_compare_data(post_link, post_data, domain):
    return get_compare_data(
        link=post_link,
        likes=post_data['likes_count'],
        dislikes='-',
        comments=post_data['comment_count'],
        reposts='-',
        views=post_data.get('video_views', '-'),
        domain=domain,
    )
