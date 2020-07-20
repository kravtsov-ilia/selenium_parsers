from typing import Optional, TYPE_CHECKING

import dateparser
from selenium.common.exceptions import NoSuchElementException

from selenium_parsers.facebook.utils.general import FacebookParseError

if TYPE_CHECKING:
    import datetime
    from selenium.webdriver.remote.webelement import WebElement


def get_post_short_text(post_el: 'WebElement') -> str:
    """
    Get post visible text
    """
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
    """
    Generation post unique id
    """
    return abs(hash(f'{post_short_text}')) % (10 ** 8)


def get_post_date(post: 'WebElement') -> 'datetime.datetime':
    """
    Parse post date create
    """
    post_date_str = post.find_element_by_xpath('.//a/abbr[@data-utime]').get_attribute('title')
    import locale
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
    return dateparser.parse(post_date_str, date_formats=['%A, %d %B %Y г. в %H:%M'], languages=['ru'])


def get_post_img(post: 'WebElement') -> Optional[str]:
    """
    Parse post image link
    """
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


def parse_count(text: str) -> int:
    """
    Parse count from html tags
    """
    text = text.replace(',', '.').replace(':', '').replace(' ', '')
    i = 0
    digit_part = ''
    while i < len(text) and (text[i].isdigit() or text[i] == '.'):
        digit_part += text[i]
        i += 1
    digit = float(digit_part)
    k = 1
    for suffix in ('тыс.', 'тысяч'):
        if suffix in text:
            k = 1000
    for suffix in ('млн.', 'миллионов'):
        if suffix in text:
            k = 10**6
    return int(digit * k)


def get_actions_count(post_el: 'WebElement', post_name: str, sub_string: str) -> int:
    """
    Parse post actions count such as comments and shares from html elements contains substring
    """
    comments_block = post_el.find_elements_by_xpath(f'.//*[contains(text(), "{sub_string}:")]')
    if len(comments_block) > 1:
        raise FacebookParseError(f'can not parse post {post_name}, too mach blocks - {sub_string}')
    if len(comments_block) == 1:
        count_part = comments_block[0].text.replace(sub_string, '')
        return parse_count(count_part)
    return 0


def get_likes_count(post_el: 'WebElement') -> int:
    """
    Get post likes count
    """
    try:
        likes_icons_block = post_el.find_element_by_xpath('.//*[@aria-label="Посмотрите, кто отреагировал на это"]')
    except NoSuchElementException:
        return 0

    likes_block = likes_icons_block.find_element_by_xpath('..')
    spans = likes_block.find_elements_by_xpath('.//span')
    for span in spans:
        try:
            likes_cnt = int(span.text)
        except (TypeError, ValueError):
            pass
        else:
            return likes_cnt
    return 0
