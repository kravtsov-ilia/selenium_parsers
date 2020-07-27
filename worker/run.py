import json
import logging
import os
from time import sleep
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import environ
import pika

from selenium_parsers.facebook.groups_parser import parse_post
from selenium_parsers.utils.selenium_loggers import setup_logger
from selenium_parsers.worker.utils import get_driver, save_result, create_vhost_if_not_exist

if TYPE_CHECKING:
    from selenium.webdriver.chrome.webdriver import WebDriver

logger = logging.getLogger('selenium_worker')

env = environ.Env()
PID_PATH = env('SELENIUM_WORKER_PID_PATH')
RABBIT_HOST = env('RABBIT_HOST')

VHOST_NAME = 'selenium_worker_posts'
QUEUE_IN = 'selenium_worker_posts_in'


def parse_fb_post(driver: 'WebDriver', post_link: str) -> dict:
    club_id = post_link.split('/')[-1]
    post_el = driver.find_element_by_css_selector('#contentArea')
    return parse_post(post_el, club_id)


def callback(ch, method, properties, body):
    body_json = json.loads(body)
    post_link = body_json['post_link']
    task_hash = body_json['task_hash']
    driver = get_driver('selenium worker', pid_path=PID_PATH)
    driver.get(post_link)
    sleep(2)
    services_map = {
        'www.facebook.com': parse_fb_post,
        'facebook.com': parse_fb_post,
    }
    parsed_uri = urlparse(post_link)
    domain = parsed_uri.hostname
    if domain in services_map:
        post_data = services_map[domain](driver, post_link)
        save_result(task_hash, post_link, post_data)
    else:
        save_result(
            task_hash,
            post_link,
            {'error': f'Для публикаций на домене {domain} подсчет не реализован'}
        )


def main():
    with pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBIT_HOST,
            virtual_host=VHOST_NAME
        )
    ) as conn:
        channel = conn.channel()
        channel.queue_declare(queue=QUEUE_IN)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue=QUEUE_IN,
            on_message_callback=callback,
            auto_ack=True
        )

        channel.start_consuming()
        while True:
            pass


if __name__ == '__main__':
    log_file = os.environ.get('SELENIUM_WORKER_LOG_FILE')
    setup_logger(
        log_file=log_file,
        logger_name='selenium_worker'
    )
    create_vhost_if_not_exist()
    main()
