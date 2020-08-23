#!/usr/bin python
import datetime
import logging
import os
import random
import string
from time import sleep
from typing import List, TYPE_CHECKING

import pymongo
from selenium.common.exceptions import NoSuchElementException

from selenium_parsers.facebook.facebook_logger import setup_fb_logger
from selenium_parsers.facebook.utils.database import get_facebook_proxy
from selenium_parsers.facebook.utils.general import FacebookParseError
from selenium_parsers.facebook.utils.page import get_display_name, get_club_id, get_club_icon, \
    get_members_and_page_like_count, get_post_parent_selector, scroll_while_loading, extract_posts, \
    close_unauthorized_popup, transform_link_to_russian
from selenium_parsers.facebook.utils.post import get_post_short_text, generate_post_id, get_likes_count, \
    get_actions_count, get_post_img, get_post_date
from selenium_parsers.utils.constants import FACEBOOK_SCREENSHOTS_DIR, DEBUG, USE_PROXY, FACEBOOK_PID_PATH
from selenium_parsers.utils.database import get_selenium_links
from selenium_parsers.utils.general import create_chrome_driver
from selenium_parsers.utils.mongo_models import FacebookPageData, FacebookPostData
from selenium_parsers.utils.parsers_signals import setup_signals_handlers, \
    process_terminate

if TYPE_CHECKING:
    from pymongo.database import Database
    from selenium.webdriver.chrome.webdriver import WebDriver
    from selenium.webdriver.remote.webelement import WebElement


logger = logging.getLogger('facebook_parser')
logger.info(f'USE_PROXY {USE_PROXY}')
logger.info(f'DEBUG {DEBUG}')
logger.info(f'SCREENSHOTS_DIR {FACEBOOK_SCREENSHOTS_DIR}')


def parse_post(post: 'WebElement', club_id: str) -> FacebookPostData:
    """
    Parse facebook post data
    """
    post_short_text = get_post_short_text(post)
    try:
        post_id = generate_post_id(post_short_text)

        likes_count = get_likes_count(post)
        comments_cnt = get_actions_count(post, post_short_text, 'Комментарии')
        shares_cnt = get_actions_count(post, post_short_text, 'Поделились')

        image_link = get_post_img(post)
        post_date = get_post_date(post)
        post_data = {
            'club_id': club_id,
            'post_id': post_id,
            'post_img': image_link,
            'content': post_short_text,
            'comments_count': comments_cnt,
            'shares_count': shares_cnt,
            'likes_count': likes_count,
            'datetime': post_date,
            'parse_datetime': datetime.datetime.now(),
        }
        return FacebookPostData(post_data)
    except NoSuchElementException:
        logger.error(f'can not parse post - {post_short_text}', exc_info=True)
        raise


def set_cookies(driver: 'WebDriver', cookies: List[dict]) -> None:
    """
    Set cookies to browser driver
    """
    for cookie in cookies:
        driver.add_cookie(cookie)


def main(driver: 'WebDriver', facebook_pages: List[str], database: 'Database') -> None:
    """
    Parse all facebook groups from database, save result to mongodb
    """
    facebook_pages_data = database['facebook_pages_data']
    facebook_posts_data = database['facebook_posts_data']

    driver.get('https://facebook.com')
    parsed_pages = 0
    for link in facebook_pages:
        link = link.rstrip()
        logger.info(f'starting to parse {link}')
        url_name = link.split('/')[-1]
        source_link = link
        if link[-1] == '/':
            link = link[:-1]
        page_posts_link = f'{link}/posts/'

        ru_page_posts_link = transform_link_to_russian(page_posts_link)
        driver.get(ru_page_posts_link)
        sleep(2)

        close_unauthorized_popup(driver)
        try:
            display_name = get_display_name(driver) or url_name
            club_id = get_club_id(driver) or url_name
            club_icon = get_club_icon(driver, club_id)

            members_cnt, page_likes_cnt = get_members_and_page_like_count(driver, driver.current_url)

            posts_selector = get_post_parent_selector(driver)
            scroll_while_loading(
                driver,
                posts_selector,
                trigger=close_unauthorized_popup,
                trigger_kwargs={'driver': driver}
            )
            posts = extract_posts(driver, posts_selector)

            total_posts_counter: int = 0
            total_likes_counter: int = 0
            total_comments_counter: int = 0
            total_shares_counter: int = 0
            for i, post in enumerate(posts, start=1):
                try:
                    fb_post_obj = parse_post(post, club_id)
                except NoSuchElementException:
                    continue

                fb_post_obj.save(collection=facebook_posts_data)

                likes_count = fb_post_obj.likes_count
                comments_cnt = fb_post_obj.comments_count
                shares_cnt = fb_post_obj.shares_count

                total_posts_counter += 1
                total_likes_counter += likes_count
                total_comments_counter += comments_cnt
                total_shares_counter += shares_cnt

            page_data = {
                'club_id': club_id,
                'club_link': source_link,
                'posts_count': total_posts_counter,
                'subscribers_count': members_cnt,
                'club_img': club_icon,
                'club_display_name': display_name,
                'datetime': datetime.datetime.now(),
                'page_likes': page_likes_cnt,
                'posts_likes': total_likes_counter,
                'comments_count': total_comments_counter,
                'shares_count': total_shares_counter,
            }
            facebook_data = FacebookPageData(page_data)
            facebook_data.save(facebook_pages_data)
        except (FacebookParseError, NoSuchElementException):
            logger.error(f'cant parse facebook page {link}', exc_info=True)
            code = ''.join(random.choice(string.hexdigits) for _ in range(5))
            logger.error(f'incident code: {code}', exc_info=True)
            screen_path = os.path.join(FACEBOOK_SCREENSHOTS_DIR, f'facebook_screenshot_{code}.png')
            chrom_driver.save_screenshot(screen_path)
        else:
            parsed_pages += 1

    logger.info(
        f'facebook parsing is finish, {parsed_pages} - pages was parsed, '
        f'total pages: {len(facebook_links)}'
    )


if __name__ == '__main__':
    setup_signals_handlers(process_terminate)
    setup_fb_logger()
    facebook_links = get_selenium_links(
        column_name='page_link',
        table_name='api_facebookpage'
    )
    extra_params = {}
    if USE_PROXY:
        proxy_ip, proxy_port = get_facebook_proxy()
        extra_params = {
            'proxy_ip': proxy_ip,
            'proxy_port': proxy_port
        }

    chrom_driver = create_chrome_driver(
        pid_file_path=FACEBOOK_PID_PATH,
        logger=logger,
        headless=(not DEBUG),
        **extra_params
    )
    try:
        with pymongo.MongoClient('mongodb://mongo', 27017) as mongo_client:
            mongo_db = mongo_client['owl_project']
            main(chrom_driver, facebook_links, mongo_db)
    except Exception:
        chrom_driver.close()
        raise
