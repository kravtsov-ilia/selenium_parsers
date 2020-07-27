import datetime
import logging
import os
import random
import string
from time import sleep
from typing import Optional

import environ
import pymongo
from selenium.common.exceptions import NoSuchElementException

from selenium_parsers.facebook.utils.page import scroll_while_loading
from selenium_parsers.tiktok.tiktok_logger import setup_tiktok_logger
from selenium_parsers.utils.database import get_selenium_links
from selenium_parsers.utils.general import get_tuned_driver
from selenium_parsers.utils.parsers_signals import setup_signals_handlers, process_terminate

logger = logging.getLogger('tiktok_parser')

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    USE_PROXY=(bool, False),
    TIKTOK_PROXY_IP=(Optional[str], None),
    TIKTOK_PROXY_PORT=(Optional[str], None)
)
DEBUG = env('DJANGO_DEBUG')
USE_PROXY = env('USE_PROXY')
PID_PATH = env('PID_PATH')
PROXY_IP = env('TIKTOK_PROXY_IP')
PROXY_PORT = env('TIKTOK_PROXY_PORT')
SCREENSHOTS_DIR = env('TIKTOK_SCREENSHOTS_DIR')


class TikTokParsingError(Exception):
    pass


class TikTokParser:
    def __init__(self):
        logger.info('tiktok parser initialization start')
        self._setup_driver()
        self._post_item_css_selector = '.video-feed-item'

    def _get_proxy(self):
        return PROXY_IP, PROXY_PORT

    def _setup_driver(self):
        extra_params = {}
        if USE_PROXY:
            proxy_ip, proxy_port = self._get_proxy()
            extra_params.update(proxy_ip=proxy_ip, proxy_port=proxy_port)

        self._driver = get_tuned_driver(
            parser_name='tiktok parser',
            logger=logger,
            headless=(not DEBUG),
            **extra_params
        )

    def _scroll_to_bottom(self):
        scroll_while_loading(
            self._driver,
            self._post_item_css_selector
        )

    def _posts(self, link):
        if DEBUG:
            self._driver.get('https://bot.sannysoft.com/')
            sleep(2)
        self._driver.get(link)
        sleep(2)
        self._scroll_to_bottom()
        posts = self._driver.find_elements_by_css_selector(self._post_item_css_selector)
        for post in posts:
            post.click()
            sleep(2)
            yield
            self._driver.find_element_by_css_selector('img.control-icon.close').click()
            sleep(1)

    def _get_post_content(self):
        return self._driver.find_element_by_css_selector('h1.video-meta-title').text

    def _parse_date(self, date_text):
        """
        Дата может встречаться в следующих форматах:
        '9 мин назад'
        '14 ч назад'
        '1 дн. назад'
        '1 нед. назад'
        '7-8'
        '7-7'
        '6-27'
        '2019-12-29'
        """
        date_spaces_separate = date_text.split(' ')
        if len(date_spaces_separate) == 3:
            # parse relative date
            current_date = datetime.datetime.now()
            value = int(date_spaces_separate[0])
            unit_slug = date_spaces_separate[1].replace('.', '')
            units_map = {
                'мин': 'minutes',
                'минут': 'minutes',
                'ч': 'hours',
                'час': 'hours',
                'часов': 'hours',
                'дн': 'days',
                'дней': 'days',
                'день': 'days',
                'нед': 'weeks',
                'недель': 'weeks',
                'недели': 'weeks',
                'неделю': 'weeks'
            }
            unit = units_map[unit_slug]
            kwargs = {
                unit: value
            }
            return current_date - datetime.timedelta(**kwargs)

        elif len(date_text.split('-')) >= 2:
            # parse absolute date
            date_list = date_text.split('-')
            date_list_len = len(date_list)
            if date_list_len == 2:
                month = int(date_list[0])
                day = int(date_list[1])
                year = datetime.datetime.now().year
            elif date_list_len == 3:
                year = int(date_list[0])
                month = int(date_list[1])
                day = int(date_list[2])
            else:
                raise TikTokParsingError('Unknown absolute date format')
            return datetime.datetime(day=day, month=month, year=year)
        else:
            raise TikTokParsingError('Unknown date format')

    def _get_post_date(self):
        date_block_text = self._driver.find_elements_by_css_selector('h2.user-nickname')[0].text
        date_text = date_block_text.split('·')[1].strip()
        return self._parse_date(date_text)

    def _get_counters(self, css_selector):
        value_text = self._driver.find_element_by_css_selector(css_selector).text
        value_base = float(''.join(c for c in value_text if c.isdigit() or c == '.'))
        multiplier_slug = value_text[-1]
        multipliers_map = {
            'K': 1000,
            'M': 10 ** 6
        }
        if multiplier_slug in multipliers_map:
            multiplier = multipliers_map[multiplier_slug]
        else:
            multiplier = 1
        return int(value_base * multiplier)

    def _get_likes_count(self):
        return self._get_counters('strong.like-text')

    def _get_comments_count(self):
        return self._get_counters('strong.comment-text')

    def _get_post_pic(self):
        style = self._driver.find_element_by_css_selector('div.video-card-browse').get_attribute('style')
        return style.split('"')[1]

    def free(self):
        self._driver.close()

    def parse_page(self, chan_link):
        logger.info(f'starting to parse {chan_link}')
        with pymongo.MongoClient('mongodb://mongo', 27017) as mongo_client:
            mongo_db = mongo_client['owl_project']
            tiktok_posts_data = mongo_db['tiktok_posts_data']
            for _ in self._posts(chan_link):
                post_date = self._get_post_date()
                image_link = self._get_post_pic()
                content = self._get_post_content()
                likes_count = self._get_likes_count()
                comments_count = self._get_comments_count()
                post_link = self._driver.current_url
                post_data = {
                    'post_link': post_link,
                    'chan_link': chan_link,
                    'datetime': post_date,
                    'post_pic': image_link,
                    'content': content,
                    'likes_count': likes_count,
                    'comments_count': comments_count,
                    'parse_datetime': datetime.datetime.now(),
                }
                tiktok_posts_data.insert_one(post_data)

    def take_screenshot(self) -> str:
        code = ''.join(random.choice(string.hexdigits) for _ in range(5))
        screen_path = os.path.join(SCREENSHOTS_DIR, f'tiktok_screenshot_{code}.png')
        self._driver.save_screenshot(screen_path)
        return screen_path


if __name__ == '__main__':
    setup_tiktok_logger()
    setup_signals_handlers(process_terminate)

    tiktok_parser = TikTokParser()
    pages = get_selenium_links(
        column_name='tiktok_link',
        table_name='api_tiktokchannels',
    )
    try:
        for page in pages:
            try:
                tiktok_parser.parse_page(page)
            except (TikTokParsingError, NoSuchElementException):
                screenshot_file = tiktok_parser.take_screenshot()
                logger.error(
                    f'can not parse tiktok page: {page}, screenshot: {screenshot_file}',
                    exc_info=True
                )
    finally:
        tiktok_parser.free()
