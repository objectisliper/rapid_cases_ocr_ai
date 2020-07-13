import asyncio

from sqlalchemy import MetaData, create_engine
from sqlalchemy.sql.ddl import CreateTable, DropTable

from service.conqueror.settings import database_config
from service.conqueror.db_models import models_list, select_uploaded_jobs
from service.conqueror.utils import DSN


def create_tables(engine):
    with engine.connect() as connection:
        for model in models_list:
            connection.execute(f'DROP TABLE IF EXISTS {model.schema.name}')
            connection.execute(CreateTable(model.schema))
            model.insert_fake_data()
            for job in select_uploaded_jobs():
                job.job_processed('test_text')


def init_db():
    db_url = DSN.format(**database_config['mysql'])
    engine = create_engine(db_url)

    create_tables(engine)


if __name__ == '__main__':
    init_db()
