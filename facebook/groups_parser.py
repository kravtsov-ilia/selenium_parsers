#!/usr/bin python
import datetime
import logging
import os
import sys
from time import sleep

import pymongo
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chrome.options import Options

from facebook.general_utils import FacebookParseError
from facebook.page_utils import get_design_full_login_elements, get_design_min_login_elements, get_display_name, \
    get_club_id, get_club_icon, get_members_and_page_like_count, get_post_parent_selector, scroll_while_post_loaded, \
    extract_posts
from facebook.post_utils import get_post_short_text, generate_post_id, get_likes_count, get_actions_count, \
    get_post_img, get_post_date

file_dir = os.path.dirname(__file__)
sys.path.append(file_dir)

from selenium_parsers.utils.selenium_utils import write_text  # noqa: E402


logger = logging.getLogger(__name__)


def setup_driver():
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
            chrome_options=chrome_options,
            desired_capabilities=capabilities
        )

    driver.implicitly_wait(3)
    return driver


def input_login_data(driver, email_field, password_field, submit_btn):
    write_text(driver, email_field, 'ivan.kohomov@gmail.com')
    write_text(driver, password_field, '5!kX4/PxA96W')
    submit_btn.click()


def login(driver):
    facebook_design_schemes = [get_design_full_login_elements, get_design_min_login_elements]
    for scheme in facebook_design_schemes:
        try:
            email_field, password_field, submit_btn = scheme(driver)
            input_login_data(driver, email_field, password_field, submit_btn)
        except NoSuchElementException:
            logger.warning(f'design scheme {scheme} not suitable')
        else:
            logger.info(f'use {scheme} design scheme for login')
            return

    logger.critical('Facebook login page was modified, login scrips no longer work')


def parse_post(post, club_id):
    post_short_text = get_post_short_text(post)
    print('post_short_text', post_short_text)
    try:
        post_id = generate_post_id(post_short_text)

        likes_count = get_likes_count(post) or 0
        comments_cnt = get_actions_count(post, post_short_text, 'Комментарии') or 0
        shares_cnt = get_actions_count(post, post_short_text, 'Поделились') or 0

        local_image_link = get_post_img(post, post_id)
        post_date = get_post_date(post)
        post_data = {
            'club_id': club_id,
            'post_id': post_id,
            'datetime': post_date,
            'post_img': local_image_link,
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


def main(driver, database):
    facebook_pages_data = database['facebook_pages_data']
    facebook_posts_data = database['facebook_posts_data']

    driver.get('https://facebook.com')
    login(driver)
    sleep(3)
    links = [
        'https://www.facebook.com/SIRELIS.BEAUTY.SILK',
        'https://www.facebook.com/JustinBieberofficialFC',
        'https://www.facebook.com/auchanrussia',
    ]
    for link in links[0:]:
        try:
            driver.get(f'{link}/posts/')
            sleep(3)

            display_name = get_display_name(driver)
            club_id = get_club_id(driver)
            club_icon = get_club_icon(driver, club_id)

            members_cnt, page_likes_cnt = get_members_and_page_like_count(driver, driver.current_url)

            posts_selector = get_post_parent_selector(driver)
            scroll_while_post_loaded(driver, posts_selector)
            posts = extract_posts(driver, posts_selector)

            total_posts_counter = 0
            total_likes_counter = 0
            total_comments_counter = 0
            total_shares_counter = 0
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


if __name__ == '__main__':
    chrom_driver = setup_driver()
    try:
        with pymongo.MongoClient(f'mongodb://mongo', 27017) as mongo_client:
            mongo_db = mongo_client['owl_project']
            main(chrom_driver, mongo_db)
    except Exception:
        chrom_driver.close()
        raise
