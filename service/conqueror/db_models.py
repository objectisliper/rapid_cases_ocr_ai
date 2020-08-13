import enum
import json
import pathlib
from datetime import datetime
from typing import List

from sqlalchemy import (
    MetaData, Table, Column, Integer, String, Date, Enum, Text, DateTime
)

from service.conqueror.utils import database_connection


class JobStatuses(enum.Enum):
    Created = 'Created'
    Uploaded = 'Uploaded'
    Recognized = 'Recognized'
    Exception = 'Exception'
    Deleted = 'Deleted'


class JobStorageStatuses(enum.Enum):
    Uploaded = 'Uploaded'
    Deleted = 'Deleted'
    Error = 'Error'


class JobStorageTypes(enum.Enum):
    Amazon_S3 = 'Amazon S3'
    Default = 'Default'


meta = MetaData()


class JobModel:
    schema = Table(
        'Jobs', meta,

        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('JobId', String(256), unique=True),
        Column('Created_Date', DateTime, default=datetime.utcnow()),
        Column('Recognition_Started_On', DateTime, nullable=True),
        Column('Recognition_Competed_On', DateTime, nullable=True),
        Column('Status', Enum(JobStatuses), nullable=False),
        Column('Local_File_Path', Text, nullable=False),
        Column('Recognition_Text', Text, nullable=True),
        Column('Storage_Status', Enum(JobStorageStatuses), nullable=True),
        Column('Storage_Name', String(128), nullable=True),
        Column('Recognition_Identifiers', Text, nullable=True)

    )

    def __init__(self, row):
        self.id = row.JobId
        self.storage_name = row.Storage_Name
        self.__status = row.Status
        self.local_path = row.Local_File_Path
        if row.Recognition_Identifiers:
            recognition_data = json.loads(row.Recognition_Identifiers)
            self.url_contains = recognition_data['caseClasificationRules']['url']
            self.text_contains = recognition_data['caseClasificationRules']['page']
            self.search_phrases = recognition_data['searchPhraseIdentifiers']
        else:
            self.url_contains = ["wpadmin", "wordpress.com"]
            self.text_contains = ["MySQL", "MariaDB"]
            self.search_phrases = ["error", "exception"]

    @staticmethod
    @database_connection
    def insert_fake_data(connection):
        video_path = (pathlib.Path(
            __file__).parent.parent / 'conqueror' / 'tests' / 'integration_tests_video' / '7bbfc76b.mp4').as_posix()
        connection.execute(JobModel.schema.insert(values=[
            {'Status': JobStatuses.Created, 'Local_File_Path': video_path,
             'Storage_Name': JobStorageTypes.Default.value, 'JobId': 'test 1'},
            {'Status': JobStatuses.Uploaded, 'Local_File_Path': video_path,
             'Storage_Name': JobStorageTypes.Amazon_S3.value, 'JobId': 'test 2'},
            {'Status': JobStatuses.Recognized, 'Local_File_Path': video_path,
             'Storage_Name': JobStorageTypes.Default.value, 'JobId': 'test 3'},
            {'Status': JobStatuses.Deleted, 'Local_File_Path': video_path,
             'Storage_Name': JobStorageTypes.Default.value, 'JobId': 'test 4'},
        ]))

    @database_connection
    def job_start_processing(self, connection):
        connection.execute(self.schema
                           .update()
                           .where(self.schema.c.JobId == self.id)
                           .values(Recognition_Started_On=datetime.utcnow()))

    @database_connection
    def job_processed(self, recognition_text, connection):
        connection.execute(self.schema
                           .update()
                           .where(self.schema.c.JobId == self.id)
                           .values(Status=JobStatuses.Recognized, Recognition_Text=recognition_text,
                                   Recognition_Competed_On=datetime.utcnow()))

    @database_connection
    def video_not_found(self, exception: str, connection):
        connection.execute(self.schema
                           .update()
                           .where(self.schema.c.JobId == self.id)
                           .values(Status=JobStatuses.Exception, Recognition_Text=exception,
                                   Recognition_Competed_On=datetime.utcnow()))


@database_connection
def select_uploaded_jobs(connection) -> List[JobModel]:
    result = []
    for row in connection.execute(JobModel.schema.select()
                                          .where(JobModel.schema.c.Status == JobStatuses.Uploaded)
                                          .where(JobModel.schema.c.Recognition_Started_On == None)
                                          .where(JobModel.schema.c.Storage_Status == JobStorageStatuses.Uploaded)):
        result.append(JobModel(row))
    return result


@database_connection
def select_job_by_id(job_id, connection) -> JobModel:
    jobs = list(connection.execute(JobModel.schema.select()
                                   .where(JobModel.schema.c.JobId == job_id)))
    if len(jobs) < 1:
        raise Exception(f'Job with id - {job_id}, does not exist')
    return JobModel(jobs[0])


models_list = [
    JobModel,
]
