import logging
from time import sleep
from typing import TYPE_CHECKING, Tuple

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from selenium_parsers.utils.selenium_utils import write_text

if TYPE_CHECKING:
    from selenium.webdriver.chrome.webdriver import WebDriver
    from selenium.webdriver.remote.webelement import WebElement

logger = logging.getLogger('facebook_parser')


def get_design_full_login_elements(driver: 'WebDriver') -> Tuple['WebElement', 'WebElement', 'WebElement']:
    """
    Old design login page
    """
    email_field = driver.find_element_by_xpath('//input[@data-testid="royal_email"]')
    password_field = driver.find_element_by_xpath('//input[@data-testid="royal_pass"]')
    submit_btn = driver.find_element_by_xpath('//input[@data-testid="royal_login_button"]')
    return email_field, password_field, submit_btn


def get_design_min_login_elements(driver: 'WebDriver') -> Tuple['WebElement', 'WebElement', 'WebElement']:
    """
    New design login page
    """
    email_field = driver.find_element_by_xpath('//input[@id="email"]')
    password_field = driver.find_element_by_xpath('//input[@id="pass"]')
    submit_btn = driver.find_element_by_xpath('//input[@type="submit"]')
    return email_field, password_field, submit_btn


def get_design_special_page(driver: 'WebDriver') -> Tuple['WebElement', 'WebElement', 'WebElement']:
    """
    Special login page
    """
    driver.get(
        'https://www.facebook.com/login/device-based/regular/login/?login_attempt=1&lwv=110'
    )
    sleep(2)
    email_field = driver.find_element_by_xpath('//input[@id="email"]')
    password_field = driver.find_element_by_xpath('//input[@id="pass"]')
    submit_btn = driver.find_element_by_xpath('//button[@id="loginbutton"]')
    return email_field, password_field, submit_btn


def input_login_data(
        driver: 'WebDriver',
        user_email: str,
        user_passwd: str,
        email_field: 'WebElement',
        password_field: 'WebElement',
        submit_btn: 'WebElement'
):
    """
    Input login data to elements
    """
    write_text(driver, email_field, user_email)
    write_text(driver, password_field, user_passwd)
    submit_btn.click()


def login_blindly(
        driver: 'WebDriver',
        user_email: str,
        user_passwd: str,
        login_display_name: str
) -> None:
    """
    Login without searching for items
    """
    logger.info('try blindly login')
    driver.get('https://www.facebook.com/login')
    sleep(2)
    ActionChains(driver).send_keys(user_email).perform()
    ActionChains(driver).send_keys(Keys.TAB).perform()
    ActionChains(driver).send_keys(user_passwd).perform()
    ActionChains(driver).send_keys(Keys.ENTER).perform()
    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, f'//span[contains(text(), "{login_display_name}")]'))
    )


def login(
        driver: 'WebDriver',
        user_email: str,
        user_passwd: str,
        login_display_name: str
) -> None:
    """
    Try to login user by several login schemes
    """
    facebook_design_schemes = (
        get_design_full_login_elements,
        get_design_min_login_elements,
        get_design_special_page
    )
    for i, scheme in enumerate(facebook_design_schemes, start=1):
        try:
            email_field, password_field, submit_btn = scheme(driver)
            input_login_data(
                driver,
                user_email,
                user_passwd,
                email_field,
                password_field,
                submit_btn
            )
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, f'//span[contains(text(), "{login_display_name}")]'))
            )
        except NoSuchElementException:
            logger.warning(f'design scheme {i} not suitable')
        except TimeoutException:
            logger.warning(f'design scheme {i} timeout')
        else:
            logger.info(f'use {i} design scheme for login')
            return
    login_blindly(driver, user_email, user_passwd, login_display_name)
