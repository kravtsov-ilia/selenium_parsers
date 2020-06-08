from selenium.webdriver import ActionChains


def write_text(driver, element, text):
    element.click()
    ActionChains(driver).send_keys(text).perform()
