import asyncio

from sqlalchemy import create_engine

from service.conqueror.settings import database_config

DSN = "mysql+pymysql://{user}:{password}@{host}:{port}/{database}"


def database_connection(wrapped_function):
    def wrapper(*args, **kwargs):
        db_url = DSN.format(**database_config['mysql'])
        engine = create_engine(db_url)

        with engine.connect() as connection:
            result = wrapped_function(connection=connection, *args, **kwargs)

            connection.execute("commit")

        return result
    return wrapper
