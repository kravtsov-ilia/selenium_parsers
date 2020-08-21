import logging
from time import sleep

import pymongo
from selenium.common.exceptions import NoSuchElementException

from selenium_parsers.odnoklassniki.ok_logger import setup_ok_logger
from selenium_parsers.utils.constants import OK_SCREENSHOTS_DIR, OK_PROXY_IP, OK_PROXY_PORT
from selenium_parsers.utils.parsing import BaseParser

logger = logging.getLogger('odnoklassniki_parser')


class OdnoklassnikiParser(BaseParser):
    """
    This parser are intended for enrich existing mongo documents
    by new data, which can not got by ok api
    """
    def __init__(self):
        logger.info('odnoklassniki parser initialization start')
        super().__init__()

    @property
    def parser_name(self):
        return 'odnoklassniki parser'

    @property
    def _proxy_ip(self):
        return OK_PROXY_IP

    @property
    def _proxy_port(self):
        return OK_PROXY_PORT

    @property
    def _logger(self):
        return logger

    @property
    def screenshot_dir(self):
        return OK_SCREENSHOTS_DIR

    def add_views(self, obj: dict) -> None:
        """
        Add views post data to mongo document
        """
        view_el_text = (
            self.
            _driver.
            find_elements_by_css_selector('.video-card_info_i')[0].
            text
        )
        try:
            views_count = int(view_el_text.split('&nbsp;')[0].split(' ')[0])
        except (TypeError, IndexError):
            logger.error(f'can not cast ok post views to int: {view_el_text}')
        else:
            obj['views_count'] = views_count

    def enrich_object(self, obj: dict):
        """
        Add some parsed data to mongo document
        """
        self._driver.get(obj['post_link'])
        sleep(2)
        self.add_views(obj)
        obj['is_need_selenium_parsing'] = False


if __name__ == '__main__':
    setup_ok_logger()
    ok_parser = OdnoklassnikiParser()
    with pymongo.MongoClient('mongodb://mongo', 27017) as mongo_client:
        mongo_db = mongo_client['owl_project']
        ok_posts_data = mongo_db['ok_wall_celery']
        ok_objects = ok_posts_data.find({'is_need_selenium_parsing': True})
        try:
            for obj in ok_objects:
                try:
                    ok_parser.enrich_object(obj)
                except NoSuchElementException:
                    screenshot_file = ok_parser.take_screenshot()
                    logger.error(
                        f'can not parse ok post with id={obj["post_id"]}, screenshot: {screenshot_file}',
                        exc_info=True
                    )
                else:
                    ok_posts_data.replace_one({'_id': obj['_id']}, obj)
        finally:
            ok_parser.free()
