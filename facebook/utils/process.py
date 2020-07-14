import logging
import os
import signal
from typing import TYPE_CHECKING

import psutil

if TYPE_CHECKING:
    from selenium.webdriver.chrome.webdriver import WebDriver

logger = logging.getLogger(__name__)


def terminate_old_process(file_path: str) -> None:
    with open(file_path, 'r') as f:
        logger.info('try to terminate old process')
        for pid in f.readlines():
            try:
                pid = int(pid)
                logger.info(f'try to terminate process pid={pid}')
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                logger.info(f'previous process was not found, pid={pid}')
            except ValueError:
                logger.warning(f'can not read process pid from file, proc pid={pid}')
            else:
                logger.warning(f'process with pid={pid} was terminated by timeout')


def save_driver_pid(driver: 'WebDriver', file_path: str) -> None:
    chrom_process = psutil.Process(driver.service.process.pid)
    with open(file_path, 'w') as f:
        python_script_pid = os.getpid()
        f.write(f'{python_script_pid}\n')
        f.write(f'{chrom_process.pid}\n')
        for proc in chrom_process.children(recursive=True):
            f.write(f'{proc.pid}\n')


def receive_signal(sig_numb: int, frame: object) -> None:
    logger.critical(f'Received signal: {sig_numb}\nBye! ')
    exit(-sig_numb)
