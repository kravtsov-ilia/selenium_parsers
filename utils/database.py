import datetime
import os
from typing import List

import psycopg2

from selenium_parsers.utils.constants import AccessStatus


def get_postgres_connection():
    return psycopg2.connect(
        dbname=os.getenv('POSTGRES_NAME'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASS'),
        host='postgres'
    )


def get_str_datetime() -> str:
    current_datetime = datetime.datetime.now()
    return current_datetime.strftime("%Y-%m-%d %H:%M:%S")


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


def get_selenium_links(column_name: str, table_name: str) -> List[str]:
    links = []
    connection = get_postgres_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(f'SELECT DISTINCT {column_name} FROM {table_name}')
        for fb_record in cursor.fetchall():
            links.append(fb_record[0])
    finally:
        connection.close()
    return links
