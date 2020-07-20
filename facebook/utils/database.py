from typing import Tuple, List

from selenium_parsers.utils.constants import AccessStatus
from selenium_parsers.utils.database import update_records, get_postgres_connection


def update_account_status(fb_login: str, status: AccessStatus) -> None:
    update_records(
        table='api_facebookaccounts',
        set_dict={'last_login_status': status},
        conditions_dict={'login': fb_login},
        status=status,
        date_field='date_last_login'
    )


def get_facebook_account() -> Tuple[str, str, str, List[dict]]:
    """
    Return account that was logged less often
    """
    connection = get_postgres_connection()
    try:
        cursor = connection.cursor()
        cursor.execute('''
            SELECT
                name,
                login,
                password,
                cookies
            FROM api_facebookaccounts
            ORDER BY date_last_login
            LIMIT 1
        ''')
        account_record = cursor.fetchone()
    finally:
        connection.close()
    return account_record


def get_facebook_proxy() -> Tuple[str, str]:
    """
    Return ip and port of proxy, that was used less often
    """
    connection = get_postgres_connection()
    try:
        cursor = connection.cursor()
        cursor.execute('''
            SELECT
                ip,
                port
            FROM api_facebookproxy
            ORDER BY date_last_usage
            LIMIT 1
        ''')
        account_record = cursor.fetchone()
    finally:
        connection.close()
    return account_record
