import logging
from typing import Optional

import dateparser
from selenium.common.exceptions import NoSuchElementException

from selenium_parsers.facebook.utils.general import FacebookParseError

logger = logging.getLogger(__name__)


def get_post_short_text(post_el) -> str:
    post_el_text = post_el.text
    post_el_text_lines = post_el_text.split('\n')
    post_message_text = post_el_text_lines[2:]
    stop_words = ('Комментарии:', 'Поделились:', 'Нравится', 'Комментировать', 'Поделиться')
    lines = []
    try:
        for line in post_message_text:
            for stop_word in stop_words:
                if stop_word in line:
                    raise StopIteration
            lines.append(line)
    except StopIteration:
        pass

    short_text = ''.join(lines)
    return short_text


def generate_post_id(post_short_text: str) -> int:
    return abs(hash(f'{post_short_text}')) % (10 ** 8)


def get_post_date(post):
    post_date_str = post.find_element_by_xpath('.//a/abbr[@data-utime]').get_attribute('title')
    import locale
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
    return dateparser.parse(post_date_str, date_formats=['%A, %d %B %Y г. в %H:%M'], languages=['ru'])


def get_post_img(post) -> Optional[str]:
    try:
        fb_link = (
            post
            .find_elements_by_xpath(
                './/div[@class="uiScaledImageContainer"]/img'
            )[0].get_attribute('src')
        )
    except (IndexError, NoSuchElementException):
        return None
    else:
        return fb_link


def get_actions_count(post_el, post_name, sub_string):
    comments_block = post_el.find_elements_by_xpath(f'.//*[contains(text(), "{sub_string}:")]')
    if len(comments_block) > 1:
        raise FacebookParseError(f'can not parse post {post_name}, too mach blocks - {sub_string}')
    if len(comments_block) == 1:
        count_part = comments_block[0].text.replace(sub_string, '').replace(':', '').replace(' ', '')
        return int(count_part)


def get_likes_count(post_el):
    try:
        likes_icons_block = post_el.find_element_by_xpath('.//*[@aria-label="Посмотрите, кто отреагировал на это"]')
    except NoSuchElementException:
        return None

    likes_block = likes_icons_block.find_element_by_xpath('..')
    spans = likes_block.find_elements_by_xpath('.//span')
    for span in spans:
        try:
            likes_cnt = int(span.text)
        except (TypeError, ValueError):
            pass
        else:
            return likes_cnt
