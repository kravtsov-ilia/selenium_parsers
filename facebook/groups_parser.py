#!/usr/bin python
import datetime
import logging
import os
import random
import signal
import string
from pathlib import Path
from time import sleep
from typing import List, TYPE_CHECKING, Dict

import environ
import psutil
import psycopg2
import pymongo
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import DesiredCapabilities, Proxy
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.proxy import ProxyType

from selenium_parsers.facebook.facebook_logger import setup_fb_logger
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

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    USE_PROXY=(bool, True)
)
DEBUG = env('DJANGO_DEBUG')
USE_PROXY = env('USE_PROXY')
SCREENSHOTS_DIR = env('SCREENSHOTS_DIR')
PID_PATH = env('PID_PATH')

logger = logging.getLogger('facebook_parser')
logger.info(f'USE_PROXY {USE_PROXY}')
logger.info(f'DEBUG {DEBUG}')
logger.info(f'SCREENSHOTS_DIR {SCREENSHOTS_DIR}')


def get_tuned_driver() -> 'WebDriver':
    os.environ["DISPLAY"] = ':99'

    chrome_options = Options()
    prefs = {"profile.default_content_setting_values.notifications": 2}
    chrome_options.add_experimental_option('prefs', prefs)
    chrome_options.add_argument("--window-size=1220x1080")

    capabilities = DesiredCapabilities.CHROME
    capabilities['goog:loggingPrefs'] = {'browser': 'ALL'}
    if USE_PROXY:
        prox = Proxy()
        prox.proxy_type = ProxyType.MANUAL
        proxy_ip = os.environ.get('FACEBOOK_PROXY_IP_1')
        proxy_port = os.environ.get('FACEBOOK_PROXY_PORT_1')
        prox.http_proxy = f"{proxy_ip}:{proxy_port}"
        prox.ssl_proxy = f"{proxy_ip}:{proxy_port}"

        prox.add_to_capabilities(capabilities)

        logger.info(f'facebook parser use proxy: {proxy_ip}')
    if DEBUG:
        driver = webdriver.Chrome(
            options=chrome_options,
            desired_capabilities=capabilities
        )
    else:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")

        driver = webdriver.Chrome(
            options=chrome_options,
            desired_capabilities=capabilities
        )

    driver.implicitly_wait(5)
    return driver


def parse_post(post: 'WebElement', club_id: str) -> Dict:
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


def main(driver: 'WebDriver', facebook_pages: List[str], database: 'Database') -> None:
    facebook_pages_data = database['facebook_pages_data']
    facebook_posts_data = database['facebook_posts_data']

    driver.get('https://facebook.com')
    sleep(2)
    user_email = os.environ.get('FB_USERNAME')
    user_passwd = os.environ.get('FB_PASSWD')
    login(driver, user_email, user_passwd, 'Иван')
    parsed_pages = 0
    for link in facebook_pages:
        logger.info(f'starting to parse {link}')
        url_name = link.split('/')[-1]
        if link[-1] == '/':
            link = link[:-1]
        page_posts_link = f'{link}/posts/'
        driver.get(page_posts_link)
        sleep(2)
        try:
            display_name = get_display_name(driver) or url_name
            club_id = get_club_id(driver) or url_name
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
                'page_link': link,
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
            code = ''.join(random.choice(string.hexdigits) for _ in range(5))
            logger.error(f'incident code: {code}', exc_info=True)
            screen_path = os.path.join(SCREENSHOTS_DIR, f'facebook_screenshot_{code}.png')
            chrom_driver.save_screenshot(screen_path)
        else:
            parsed_pages += 1

    logger.info(
        f'facebook parsing is finish, {parsed_pages} - pages was parsed, '
        f'total pages: {len(facebook_links)}'
    )


def get_facebook_links() -> List[str]:
    connection = psycopg2.connect(
        dbname=os.getenv('POSTGRES_NAME'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASS'),
        host='postgres'
    )
    fb_links = []
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT page_link FROM api_facebookpage')
        for fb_record in cursor.fetchall():
            fb_links.append(fb_record[0])
    finally:
        connection.close()
    return fb_links


def terminate_old_process(file_path: str) -> None:
    with open(file_path, 'r') as f:
        logger.info('try to terminate old process')
        for pid in f.readlines():
            try:
                pid = int(pid)
                logger.info(f'try to terminate process pid={pid}')
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                logger.info(f'previous process was not found, pid={pid}')
            except ValueError:
                logger.warning(f'can not read process pid from file, proc pid={pid}')
            else:
                logger.warning(f'process with pid={pid} was terminated by timeout')


def save_driver_pid(driver: 'WebDriver', file_path: str) -> None:
    chrom_process = psutil.Process(driver.service.process.pid)
    with open(file_path, 'w') as f:
        python_script_pid = os.getpid()
        f.write(f'{python_script_pid}\n')
        f.write(f'{chrom_process.pid}\n')
        for proc in chrom_process.children(recursive=True):
            f.write(f'{proc.pid}\n')


def create_chrome_driver() -> 'WebDriver':
    pid_file = os.path.join(PID_PATH, 'facebook_chrome.pid')
    Path(pid_file).touch()
    terminate_old_process(pid_file)
    driver = get_tuned_driver()
    save_driver_pid(driver, pid_file)
    return driver


def receive_signal(sig_numb: int, frame: object) -> None:
    logger.critical(f'Received signal: {sig_numb}\nBye! ')
    exit(-sig_numb)


if __name__ == '__main__':
    # set signal handlers
    signal.signal(signal.SIGTERM, receive_signal)
    signal.signal(signal.SIGHUP, receive_signal)

    setup_fb_logger()
    facebook_links = get_facebook_links()
    chrom_driver = create_chrome_driver()
    try:
        with pymongo.MongoClient('mongodb://mongo', 27017) as mongo_client:
            mongo_db = mongo_client['owl_project']
            main(chrom_driver, facebook_links, mongo_db)
    except Exception:
        chrom_driver.close()
        raise
