import logging

from selenium.common.exceptions import NoSuchElementException

from selenium_parsers.utils.selenium_utils import write_text

logger = logging.getLogger(__name__)


def get_design_full_login_elements(driver):
    email_field = driver.find_element_by_xpath('//input[@data-testid="royal_email"]')
    password_field = driver.find_element_by_xpath('//input[@data-testid="royal_pass"]')
    submit_btn = driver.find_element_by_xpath('//input[@data-testid="royal_login_button"]')
    return email_field, password_field, submit_btn


def get_design_min_login_elements(driver):
    email_field = driver.find_element_by_xpath('//input[@id="email"]')
    password_field = driver.find_element_by_xpath('//input[@id="pass"]')
    submit_btn = driver.find_element_by_xpath('//input[@type="submit"]')
    return email_field, password_field, submit_btn


def input_login_data(
        driver,
        user_email,
        user_passwd,
        email_field, password_field,
        submit_btn
):
    write_text(driver, email_field, user_email)
    write_text(driver, password_field, user_passwd)
    submit_btn.click()


def login(driver, user_email, user_passwd):
    facebook_design_schemes = (get_design_full_login_elements, get_design_min_login_elements)
    for scheme in facebook_design_schemes:
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
        except NoSuchElementException:
            logger.warning(f'design scheme {scheme} not suitable')
        else:
            logger.info(f'use {scheme} design scheme for login')
            return

    logger.critical('Facebook login page was modified, login scrips no longer work')
