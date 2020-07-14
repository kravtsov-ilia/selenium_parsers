import os

import psycopg2


def get_postgres_connection():
    return psycopg2.connect(
        dbname=os.getenv('POSTGRES_NAME'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASS'),
        host='postgres'
    )
