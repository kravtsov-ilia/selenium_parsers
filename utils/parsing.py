import os
import random
import string

from selenium_parsers.utils.general import get_tuned_driver

from selenium_parsers.utils.constants import USE_PROXY, DEBUG


class BaseParser:
    def __init__(self):
        self._setup_driver()

    @property
    def parser_name(self):
        """
        Set selenium parser name for logging
        """
        raise NotImplementedError()

    @property
    def _proxy_ip(self):
        """
        Set selenium parser proxy ip
        """
        raise NotImplementedError()

    @property
    def _proxy_port(self):
        """
        Set selenium parser proxy port
        """
        raise NotImplementedError()

    @property
    def _logger(self):
        """
        Set selenium parser logger
        """
        raise NotImplementedError()

    def _setup_driver(self):
        """
        Prepare selenium driver
        """
        extra_params = {}
        if USE_PROXY:
            extra_params.update(proxy_ip=self._proxy_ip, proxy_port=self._proxy_port)

        self._driver = get_tuned_driver(
            parser_name=self.parser_name,
            logger=self._logger,
            headless=(not DEBUG),
            **extra_params
        )

    @property
    def screenshot_dir(self):
        """
        Set selenium screenshot dir for debugging
        """
        raise NotImplementedError()

    def free(self):
        """
        Free object re  sources
        """
        self._driver.close()

    def take_screenshot(self):
        """
        Make a screenshot
        """
        code = ''.join(random.choice(string.hexdigits) for _ in range(5))
        screen_path = os.path.join(self.screenshot_dir, f'ok_screenshot_{code}.png')
        self._driver.save_screenshot(screen_path)
        return screen_path
