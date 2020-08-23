import logging
from time import sleep
from typing import TYPE_CHECKING, List, Optional, Tuple

from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
from selenium.webdriver.common.keys import Keys

from selenium_parsers.facebook.utils.general import FacebookParseError

if TYPE_CHECKING:
    from selenium.webdriver.chrome.webdriver import WebDriver
    from selenium.webdriver.remote.webelement import WebElement  # noqa: F401

logger = logging.getLogger('facebook_parser')


def get_club_icon(driver: 'WebDriver', club_id: str) -> str:
    """
    Get facebook page icon
    """
    try:
        fb_icon_block = driver.find_elements_by_xpath('//div[@id="entity_sidebar"]')[0]
        fb_icon_link = fb_icon_block.find_elements_by_xpath('.//img')[0].get_attribute('src')
    except IndexError:
        logger.error(f'can not parse club icon for {club_id}', exc_info=True)
        return ''
    return fb_icon_link


def get_page_info_from_members_and_likes_page_widget(
        driver: 'WebDriver',
        redirect_location: str
) -> Tuple[int, int]:
    """
    Use community widget for extract page likes and members
    """
    driver.find_element_by_xpath('//div/a[@data-endpoint]/span[contains(text(), "Главная")]').click()
    sidebar_el = driver.find_element_by_xpath('//div[@id="pages_side_column"]')
    likes_child_el = sidebar_el.find_element_by_xpath('.//div[contains(text(), "Нравится ")]')
    members_child_el = sidebar_el.find_element_by_xpath('.//div[contains(text(), "Подписан")]')
    likes_text = likes_child_el.text
    members_text = members_child_el.text
    likes_str = ''.join([c for c in likes_text if c.isdigit()])
    members_str = ''.join([c for c in members_text if c.isdigit()])

    driver.get(redirect_location)
    sleep(2)
    return int(likes_str), int(members_str)


def get_page_info_by_members_page_visit(
        driver: 'WebDriver',
        redirect_location: str
) -> Tuple[int, int]:
    """
    Use community page for extract page likes and members
    """
    driver.find_element_by_xpath('//div/a[@data-endpoint]/span[contains(text(), "Сообщество")]').click()
    sleep(3)
    members_child_el = driver.find_element_by_xpath('//div[contains(text(), "Всего подписчиков")]')
    likes_child_el = driver.find_element_by_xpath('//div[contains(text(), "Всего отметок")]')
    likes_cnt = 0
    members_cnt = 0
    for slug, block in (('members', members_child_el), ('likes', likes_child_el)):
        block = block.find_element_by_xpath('..')
        cnt = int(block.find_elements_by_xpath('.//div')[0].text.replace(' ', ''))
        if slug == 'members':
            members_cnt = cnt
        elif slug == 'likes':
            likes_cnt = cnt
    driver.get(redirect_location)
    return likes_cnt, members_cnt


def get_members_and_page_like_count(driver: 'WebDriver', redirect_location: str) -> Tuple[int, int]:
    """
    Parse page likes and members count
    """
    methods = (
        get_page_info_from_members_and_likes_page_widget,
        get_page_info_by_members_page_visit
    )
    for i, method in enumerate(methods, start=1):
        try:
            likes, members = method(driver, redirect_location)
        except NoSuchElementException:
            logger.warning(f'can not parse members and likes page info try {i}')
        else:
            return likes, members
    logger.critical('can not parse page info: likes and members count')
    raise FacebookParseError


def get_single_post_selector(driver: 'WebDriver') -> str:
    """
    Find posts parent container on single post page
    """
    comments_blocks = driver.find_elements_by_xpath('//*[contains(text(), "Комментарии")]')
    shares_blocks = driver.find_elements_by_xpath('//*[contains(text(), "Поделились")]')

    if len(comments_blocks) <= 0 or len(shares_blocks) <= 0:
        raise FacebookParseError(
            f'can not parse reactions parent node, '
            f'some block was not found: '
            f'{len(comments_blocks)}, '
            f'{len(shares_blocks)}'
        )

    ancestor_container = comments_blocks[0]

    i = 0
    max_iteration_cnt = 100
    while i < max_iteration_cnt:
        i += 1
        previous_parent = ancestor_container
        ancestor = ancestor_container.find_element_by_xpath('..')

        comments_cnt = len(ancestor.find_elements_by_xpath('.//*[contains(text(), "Комментировать")]'))
        shares_cnt = len(ancestor.find_elements_by_xpath('.//*[contains(text(), "Поделиться")]'))

        if comments_cnt == 1 and shares_cnt == 1:
            post_parent_class = previous_parent.get_attribute('class')
            return '.' + '.'.join(post_parent_class.split(' '))
    raise FacebookParseError('cant not find main post ancestor')


def get_post_parent_selector(driver: 'WebDriver') -> str:
    """
    Find posts parent container on community posts page
    """
    likes_blocks = driver.find_elements_by_xpath('//*[contains(text(), "Нравится")]')
    comments_blocks = driver.find_elements_by_xpath('//*[contains(text(), "Комментировать")]')
    shares_blocks = driver.find_elements_by_xpath('//*[contains(text(), "Поделиться")]')

    if len(likes_blocks) <= 0 or len(comments_blocks) <= 0 or len(shares_blocks) <= 0:
        raise FacebookParseError(
            f'can not parse reactions parent node, '
            f'some block was not found: '
            f'{len(likes_blocks)}, '
            f'{len(comments_blocks)}, '
            f'{len(shares_blocks)}'
        )

    ancestor = comments_blocks[len(comments_blocks) // 2]

    i = 0
    max_iteration_cnt = 100
    while i < max_iteration_cnt:
        i += 1
        previous_parent = ancestor
        ancestor = ancestor.find_element_by_xpath('..')

        likes_cnt = len(ancestor.find_elements_by_xpath('.//*[contains(text(), "Нравится")]'))
        comments_cnt = len(ancestor.find_elements_by_xpath('.//*[contains(text(), "Комментировать")]'))
        shares_cnt = len(ancestor.find_elements_by_xpath('.//*[contains(text(), "Поделиться")]'))

        if likes_cnt > 1 and comments_cnt > 1 and shares_cnt > 1:
            post_parent_class = previous_parent.get_attribute('class')
            return '.' + '.'.join(post_parent_class.split(' '))
    raise FacebookParseError('cant not find main post ancestor')


def scroll_while_loading(
        driver: 'WebDriver',
        posts_css_selector: str,
        trigger: Optional[callable] = None,
        trigger_kwargs: Optional[dict] = None
) -> None:
    """
    Scroll page while posts are loading or max iteration was reached
    """
    prev_posts_count = len(driver.find_elements_by_css_selector(posts_css_selector))

    current_posts_count = 0
    max_iteration_count = 100
    i = 0
    while (
        prev_posts_count != current_posts_count
        and current_posts_count < 1200
        and i < max_iteration_count
    ):
        i += 1
        html = driver.find_element_by_tag_name('html')
        for _ in range(4):
            html.send_keys(Keys.END)
            sleep(0.3)
        sleep(2)
        prev_posts_count = current_posts_count
        current_posts_count = len(driver.find_elements_by_css_selector(posts_css_selector))
        if trigger:
            trigger(**trigger_kwargs)


def extract_posts(driver: 'WebDriver', posts_selector: str) -> List['WebElement']:
    """
    Return only posts items, filter other instances
    """
    elements = driver.find_elements_by_css_selector(posts_selector)
    posts = []
    for element in elements:
        el_classes = element.get_attribute('class')
        el_selector = '.' + '.'.join(el_classes.split(' '))
        if el_selector == posts_selector:
            posts.append(element)
    return posts


def get_display_name(driver: 'WebDriver') -> Optional[str]:
    """
    Get page display name
    """
    display_name_selectors = (
        '//h1[@id="seo_h1_tag"]/a/span',
        '//h1[@id="seo_h1_tag"]',
    )

    for selector in display_name_selectors:
        try:
            display_name = driver.find_element_by_xpath(selector).text
        except NoSuchElementException:
            pass
        else:
            return ''.join([c for c in display_name if c.isalnum() or c == ' '])

    logger.error('can not parse group display name')


def get_club_id(driver: 'WebDriver') -> Optional[str]:
    """
    Get page unique name
    """
    try:
        club_id = driver.find_element_by_xpath('//div/a[@href="#"][contains(text(), "@")]').text
    except NoSuchElementException:
        logger.warning('no such club id')
        club_id = None
    return club_id


def close_unauthorized_popup(driver: 'WebDriver') -> bool:
    """
    Close popup for unauthorized users,
    return true if popup was closed
    """
    try:
        (
            driver
            .find_element_by_xpath('//div/a[@href="#"][contains(text(), "Не сейчас")]')
            .click()
        )
    except (ElementNotInteractableException, NoSuchElementException):
        return False
    else:
        return True


def transform_link_to_russian(link: str) -> str:
    """
    Transform link to russian version of resource
    """
    if 'www' in link:
        return link.replace('www', 'ru-ru')
    else:
        return link.replace('https://', 'https://ru-ru.')
