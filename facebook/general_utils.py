import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class FacebookParseError(Exception):
    pass


class FacebookParseLikesError(FacebookParseError):
    pass


def download_fb_image(link: str, file_name: str) -> Optional[str]:
    possible_extensions = ('.jpg', '.jpeg', '.png')
    full_file_name = None
    for ext in possible_extensions:
        if ext in link:
            full_file_name = f'{file_name}{ext}'
            break

    if not full_file_name:
        return None
    response = requests.get(link)
    if response.status_code != 200:
        logger.error(f'can not download facebook image: {link}')
        return
    data = response.content
    file_path = f'/tmp/uploaded/{full_file_name}'
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # TODO save images to shared volume
    with open(file_path, 'wb') as f:
        f.write(data)
    # TODO return relative url
    return full_file_name
