import json
import logging
import os
from time import sleep
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import pika
from selenium.common.exceptions import NoSuchElementException

from selenium_parsers.facebook.groups_parser import parse_post
from selenium_parsers.facebook.utils.page import transform_link_to_russian
from selenium_parsers.utils.constants import SELENIUM_WORKER_PID_PATH, RABBIT_HOST
from selenium_parsers.utils.selenium_loggers import setup_logger
from selenium_parsers.worker.utils import (
    get_driver, save_result, create_vhost_if_not_exist, cast_facebook_compare_data, cast_instagram_compare_data
)

if TYPE_CHECKING:
    from selenium.webdriver.chrome.webdriver import WebDriver

logger = logging.getLogger('selenium_worker')

VHOST_NAME = 'selenium_worker_posts'
QUEUE_IN = 'selenium_worker_posts_in'


def parse_fb_post(driver: 'WebDriver', post_link: str) -> dict:
    club_id = post_link.split('/')[-1]
    post_el = driver.find_element_by_css_selector('#contentArea')
    fb_obj = parse_post(post_el, club_id)
    return cast_facebook_compare_data(post_link, fb_obj, 'facebook.com')


def parse_insta_post(driver: 'WebDriver', post_link: str) -> dict:
    post_page = driver.execute_script("return window._sharedData.entry_data.PostPage[0]")
    if post_page is None:
        logger.error(f'can not parse post - : {post_link.encode("utf-8")}')
        raise NoSuchElementException("Unavailable Page: {}".format(post_link.encode("utf-8")))

    media = post_page["graphql"]["shortcode_media"]
    comment_count = media["edge_media_preview_comment"]["count"]
    likes_count = media["edge_media_preview_like"]["count"]
    is_video = media["is_video"]
    result = {'comment_count': comment_count, 'likes_count': likes_count}
    if is_video:
        result['video_views'] = media['video_view_count']

    return cast_instagram_compare_data(post_link, result, 'instagram.com')


def handle_link(link: str) -> str:
    if 'facebook' in link:
        return transform_link_to_russian(link)
    return link


def get_second_level_domain(link: str) -> str:
    parsed_uri = urlparse(link)
    domain = parsed_uri.hostname
    return '.'.join(domain.split('.')[-2:])


def callback(ch, method, properties, body):
    body_json = json.loads(body)
    post_link = body_json['post_link']
    task_hash = body_json['task_hash']
    driver = get_driver('selenium worker', pid_path=SELENIUM_WORKER_PID_PATH)

    post_link = handle_link(post_link)
    driver.get(post_link)
    sleep(2)

    services_map = {
        'facebook.com': parse_fb_post,
        'instagram.com': parse_insta_post,
    }
    domain = get_second_level_domain(post_link)
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
        logger.info('Worker is online')
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
