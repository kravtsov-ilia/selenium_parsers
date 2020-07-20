import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import environ
import requests
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities, Proxy
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.proxy import ProxyType

from selenium_parsers.facebook.utils.database import AccessStatus
from selenium_parsers.utils.database import update_proxy_status
from selenium_parsers.utils.parsers_signals import terminate_old_process, save_driver_pid

if TYPE_CHECKING:
    from logging import Logger
    from selenium.webdriver.chrome.webdriver import WebDriver

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    USE_PROXY=(bool, True)
)
DEBUG = env('DJANGO_DEBUG')
USE_PROXY = env('USE_PROXY')


def create_chrome_driver(
    pid_file_path: str,
    pid_file_name: str,
    logger: 'Logger',
    **extra_params
) -> 'WebDriver':
    pid_file = os.path.join(pid_file_path, f'{pid_file_name}')
    Path(pid_file).touch()
    terminate_old_process(pid_file)
    driver = get_tuned_driver(
        parser_name='facebook parser',
        logger=logger,
        **extra_params
    )
    save_driver_pid(driver, pid_file)
    return driver


def get_tuned_driver(
        parser_name: str,
        logger: 'Logger',
        proxy_ip: Optional[str] = None,
        proxy_port: Optional[str] = None
) -> 'WebDriver':
    os.environ["DISPLAY"] = ':99'

    chrome_options = Options()

    capabilities = DesiredCapabilities.CHROME
    capabilities['goog:loggingPrefs'] = {'browser': 'ALL'}
    if USE_PROXY:
        prox = Proxy()
        prox.proxy_type = ProxyType.MANUAL
        prox.http_proxy = f"{proxy_ip}:{proxy_port}"
        prox.ssl_proxy = f"{proxy_ip}:{proxy_port}"
        try:
            response = requests.get(
                'https://google.com',
                proxies={
                    'http': f'{proxy_ip}:{proxy_port}',
                    'https': f'{proxy_ip}:{proxy_port}',
                }
            )
        except requests.RequestException:
            update_proxy_status(proxy_ip, AccessStatus.fail)
            raise
        if response.status_code != 200:
            update_proxy_status(proxy_ip, AccessStatus.fail)
            logger.critical(f'proxy {proxy_ip}:{proxy_port} not work')
            exit(-1)
        update_proxy_status(proxy_ip, AccessStatus.success)
        prox.add_to_capabilities(capabilities)

        logger.info(f'{parser_name} use proxy: {proxy_ip}:{proxy_port}')
    if DEBUG:
        driver = webdriver.Chrome(
            options=chrome_options,
            desired_capabilities=capabilities
        )
    else:
        chrome_options.add_argument("--no-sandbox")
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

    prefs = {"profile.default_content_setting_values.notifications": 2}
    chrome_options.add_experimental_option('prefs', prefs)
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_argument('start-maximized')
    chrome_options.add_argument('incognito')

    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
        Object.defineProperty(navigator, 'webdriver', {
          get: () => undefined,
          enumerable: false,
          configurable: true
        });
        const newProto = navigator.__proto__;
        delete newProto.webdriver;
        navigator.__proto__ = newProto;
        delete navigator.webdriver;
      """
    })

    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                     'Chrome/83.0.4103.53 Safari/537.36'
    })

    driver.implicitly_wait(5)
    return driver
