import datetime
from enum import Enum
from typing import Tuple, List

from selenium_parsers.utils.general import get_postgres_connection


class AccessStatus(Enum):
    success = 'success'
    fail = 'fail'

    def __eq__(self, other):
        return self.value == other

    def __str__(self):
        return self.value


def get_str_datetime() -> str:
    current_datetime = datetime.datetime.now()
    return current_datetime.strftime("%Y-%m-%d %H:%M:%S")


def update_account_status(fb_login: str, status: AccessStatus) -> None:
    update_records(
        table='api_facebookaccounts',
        set_dict={'last_login_status': status},
        conditions_dict={'login': fb_login},
        status=status,
        date_field='date_last_login'
    )


def update_proxy_status(proxy_ip: str, status: AccessStatus) -> None:
    update_records(
        table='api_facebookproxy',
        set_dict={'last_usage_status': status},
        conditions_dict={'ip': proxy_ip},
        status=status,
        date_field='date_last_usage'
    )


def update_records(
        table: str,
        set_dict: dict,
        conditions_dict: dict,
        status: AccessStatus,
        date_field: str
) -> None:
    connection = get_postgres_connection()
    current_date = get_str_datetime()

    if status == AccessStatus.success:
        set_dict[date_field] = f'{current_date}'

    set_data_string = ','.join([f'{key}=%({key})s' for key, value in set_dict.items()])
    condition_string = ','.join([f'{key}=%({key})s' for key, value in conditions_dict.items()])

    sql_data = dict(
        {k: f'{v}' for k, v in set_dict.items()},
        **{k: f'{v}' for k, v in conditions_dict.items()}
    )

    try:
        cursor = connection.cursor()
        query = f'UPDATE {table} SET {set_data_string} WHERE {condition_string}'
        cursor.execute(query, sql_data)
        connection.commit()
    finally:
        connection.close()


def get_facebook_links() -> List[str]:
    fb_links = []
    connection = get_postgres_connection()
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT page_link FROM api_facebookpage')
        for fb_record in cursor.fetchall():
            fb_links.append(fb_record[0])
    finally:
        connection.close()
    return fb_links


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
