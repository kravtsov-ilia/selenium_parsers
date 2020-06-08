import logging
from time import sleep

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys

from selenium_parsers.facebook.utils.general import FacebookParseError

logger = logging.getLogger(__name__)


def get_club_icon(driver, club_id: str) -> str:
    try:
        fb_icon_block = driver.find_elements_by_xpath('//div[@id="entity_sidebar"]')[0]
        fb_icon_link = fb_icon_block.find_elements_by_xpath('.//img')[0].get_attribute('src')
    except IndexError:
        logger.error(f'can not parse club icon for {club_id}', exc_info=True)
        return ''
    return fb_icon_link


def get_members_and_page_like_count(driver, redirect_location) -> tuple:
    driver.find_element_by_xpath('//div/a[@data-endpoint]/span[contains(text(), "Сообщество")]').click()
    sleep(3)
    members_child_el = driver.find_element_by_xpath('//div[contains(text(), "Всего подписчиков")]')
    likes_child_el = driver.find_element_by_xpath('//div[contains(text(), "Всего отметок")]')
    result = []
    for block in [members_child_el, likes_child_el]:
        block = block.find_element_by_xpath('..')
        cnt = int(block.find_elements_by_xpath('.//div')[0].text.replace(' ', ''))
        result.append(cnt)

    driver.get(redirect_location)
    sleep(3)
    return tuple(result)


def get_post_parent_selector(driver):
    likes_blocks = driver.find_elements_by_xpath(f'//*[contains(text(), "Нравится")]')
    comments_blocks = driver.find_elements_by_xpath(f'//*[contains(text(), "Комментировать")]')
    shares_blocks = driver.find_elements_by_xpath(f'//*[contains(text(), "Поделиться")]')

    if len(likes_blocks) <= 0 or len(comments_blocks) <= 0 or len(shares_blocks) <= 0:
        logger.critical(
            f'can not parse reactions parent node, '
            f'some block was not found: '
            f'{len(likes_blocks)}, '
            f'{len(comments_blocks)}, '
            f'{len(shares_blocks)}'
        )
        exit(-1)

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


def scroll_while_post_loaded(driver, posts_selector):
    prev_posts_count = len(driver.find_elements_by_css_selector(posts_selector))

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
            sleep(0.1)
        sleep(2)
        prev_posts_count = current_posts_count
        current_posts_count = len(driver.find_elements_by_css_selector(posts_selector))


def extract_posts(driver, posts_selector):
    elements = driver.find_elements_by_css_selector(posts_selector)
    posts = []
    for element in elements:
        el_classes = element.get_attribute('class')
        el_selector = '.' + '.'.join(el_classes.split(' '))
        if el_selector == posts_selector:
            posts.append(element)
    return posts


def get_display_name(driver):
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
            return display_name

    logger.error('can not parse group display name')


def get_club_id(driver):
    return driver.find_element_by_xpath('//div/a[@href="#"][contains(text(), "@")]').text
