import asyncio
import hmac
import os
import time
from base64 import encodebytes
from hashlib import sha1
from typing import AnyStr
import urllib.parse

import requests
from sqlalchemy import create_engine

from service.conqueror.settings import database_config
from service.conqueror.settings.local import VIDEO_TEMP_DIR

DSN = "mysql+pymysql://{user}:{password}@{host}:{port}/{database}"


class FileNotFoundException(Exception):
    pass


def database_connection(wrapped_function):
    def wrapper(*args, **kwargs):
        db_url = DSN.format(**database_config['mysql'])
        engine = create_engine(db_url, max_overflow=10)

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


def get_video_from_amazon_server(job_id):
    timestamp = int(time.time() * 1000)
    signature = get_amazon_server_signature(job_id, timestamp)
    response = requests.get(f'http://mw.rapidcases.ai/download/job/{job_id}?signature={signature}&timestamp={timestamp}')
    if response.status_code == 200:
        return response.content
    else:
        error = f'job_id={job_id} status_code={response.status_code} timestamp={timestamp} signature={timestamp} ' \
                f'file by id not found in storage'
        print(error)
        raise FileNotFoundException(error)


def get_amazon_server_signature(job_id: str, timestamp: int) -> str:
    private_key_bytes = b'1E3dki1GcBxS0LCAM0zhdiKQGOJbqoBFOP2fZXRZlSSzrr4PzNcF-vo0g7D1tSxhtlPUdEasW5VuCma'
    data = bytes(f'{job_id}:{timestamp}', 'utf-8')
    hashed = hmac.new(private_key_bytes, data, sha1).digest()
    return urllib.parse.quote(encodebytes(hashed).strip(b'\n').decode('utf-8'))
