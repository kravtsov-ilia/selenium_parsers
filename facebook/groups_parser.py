#!/usr/bin python
import datetime
import logging
import os
import sys
from time import sleep
from typing import List, TYPE_CHECKING

import psycopg2
import pymongo
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chrome.options import Options

from selenium_parsers.facebook.utils.general import FacebookParseError
from selenium_parsers.facebook.utils.login import login
from selenium_parsers.facebook.utils.page import get_display_name, get_club_id, get_club_icon, \
    get_members_and_page_like_count, get_post_parent_selector, scroll_while_post_loaded, extract_posts
from selenium_parsers.facebook.utils.post import get_post_short_text, generate_post_id, get_likes_count, \
    get_actions_count, get_post_img, get_post_date

if TYPE_CHECKING:
    from pymongo.database import Database
    from selenium.webdriver.chrome.webdriver import WebDriver
    from selenium.webdriver.remote.webelement import WebElement


file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


def get_tuned_driver() -> None:
    os.environ["DISPLAY"] = ':99'

    chrome_options = Options()
    prefs = {"profile.default_content_setting_values.notifications": 2}
    chrome_options.add_experimental_option('prefs', prefs)

    capabilities = DesiredCapabilities.CHROME
    capabilities['goog:loggingPrefs'] = {'browser': 'ALL'}

    if sys.platform == 'darwin':
        chrome_options.add_argument("--window-size=1220x1080")
        driver = webdriver.Chrome(
            chrome_options=chrome_options,
            desired_capabilities=capabilities
        )
    else:
        chrome_driver_binary = "/usr/bin/chromedriver"
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920x1080")
        chrome_options.add_argument("start-maximized")
        chrome_options.add_argument("disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")

        driver = webdriver.Chrome(
            chrome_driver_binary,
            options=chrome_options,
            desired_capabilities=capabilities
        )

    driver.implicitly_wait(5)
    return driver


def parse_post(post: WebElement, club_id: int):
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
            'datetime': post_date,
            'post_img': image_link,
            'short_text': post_short_text,
            'comments': comments_cnt,
            'shares': shares_cnt,
            'parse_datetime': datetime.datetime.now(),
            'likes': likes_count,
        }
        return post_data
    except NoSuchElementException:
        logger.error(f'can not parse post - {post_short_text}', exc_info=True)
        raise


def main(driver: WebDriver, facebook_pages: List[str], database: Database) -> None:
    facebook_pages_data = database['facebook_pages_data']
    facebook_posts_data = database['facebook_posts_data']

    driver.get('https://facebook.com')
    user_email = os.environ.get('FB_USERNAME')
    user_passwd = os.environ.get('FB_PASSWD')

    login(driver, user_email, user_passwd)
    sleep(3)
    for link in facebook_pages:
        logger.info(f'starting to parse {link}')
        driver.get(f'{link}/posts/')
        sleep(3)
        try:
            display_name = get_display_name(driver) or link.split('/')[-1]
            club_id = get_club_id(driver)
            club_icon = get_club_icon(driver, club_id)

            members_cnt, page_likes_cnt = get_members_and_page_like_count(driver, driver.current_url)

            posts_selector = get_post_parent_selector(driver)
            scroll_while_post_loaded(driver, posts_selector)
            posts = extract_posts(driver, posts_selector)

            total_posts_counter: int = 0
            total_likes_counter: int = 0
            total_comments_counter: int = 0
            total_shares_counter: int = 0
            for i, post in enumerate(posts, start=1):
                try:
                    post_data = parse_post(post, club_id)
                except NoSuchElementException:
                    continue

                facebook_posts_data.insert_one(post_data)

                likes_count = post_data['likes']
                comments_cnt = post_data['comments']
                shares_cnt = post_data['shares']

                total_posts_counter += 1
                total_likes_counter += likes_count
                total_comments_counter += comments_cnt
                total_shares_counter += shares_cnt

            page_data = {
                'club_id': club_id,
                'posts_count': total_posts_counter,
                'members_count': members_cnt,
                'photo': club_icon,
                'screen_name': display_name,
                'datetime': datetime.datetime.now(),
                'page_likes': page_likes_cnt,
                'posts_likes': total_likes_counter,
                'comments': total_comments_counter,
                'shares': total_shares_counter,
            }
            facebook_pages_data.insert_one(page_data)

        except (FacebookParseError, NoSuchElementException):
            logger.error(f'cant parse facebook page {link}', exc_info=True)


def get_facebook_links() -> list:
    connection = psycopg2.connect(
        dbname=os.getenv('POSTGRES_NAME'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASS'),
        host='postgres'
    )
    fb_links = []
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT page_link FROM api_facebookpage")
        for fb_record in cursor.fetchall():
            fb_links.append(fb_record[0])
    finally:
        connection.close()
    return fb_links


if __name__ == '__main__':
    facebook_links = get_facebook_links()
    chrom_driver = get_tuned_driver()
    try:
        with pymongo.MongoClient(f'mongodb://mongo', 27017) as mongo_client:
            mongo_db = mongo_client['owl_project']
            main(chrom_driver, facebook_links, mongo_db)
    except Exception:
        chrom_driver.close()
        raise
