from typing import TYPE_CHECKING

from selenium.webdriver import ActionChains

if TYPE_CHECKING:
    from selenium.webdriver.chrome.webdriver import WebDriver
    from selenium.webdriver.remote.webelement import WebElement


def write_text(
        driver: 'WebDriver',
        element: 'WebElement',
        text: str,
) -> None:
    """
    Send text like a user
    """
    element.click()
    ActionChains(driver).send_keys(text).perform()
