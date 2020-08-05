import asyncio
import os
from typing import AnyStr

from sqlalchemy import create_engine

from service.conqueror.settings import database_config
from service.conqueror.settings.local import VIDEO_TEMP_DIR

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


def save_video_to_temporary_directory(video_file) -> AnyStr:
    file_name = os.path.join(VIDEO_TEMP_DIR, f'{video_file.signature}.{video_file.format}')
    with open(file_name, 'wb') as f:
        f.write(video_file.video_data)
    return file_name

