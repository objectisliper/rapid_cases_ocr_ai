import enum
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
    Deleted = 'Deleted'


class JobStorageStatuses(enum.Enum):
    Uploaded = 'Uploaded'
    Deleted = 'Deleted'
    Error = 'Error'


meta = MetaData()


class JobModel:
    schema = Table(
        'Jobs', meta,

        Column('JobId', Integer, primary_key=True, autoincrement=True),
        Column('Created_Date', DateTime, default=datetime.utcnow()),
        Column('Recognition_Started_On', DateTime, nullable=True),
        Column('Recognition_Competed_On', DateTime, nullable=True),
        Column('Status', Enum(JobStatuses), nullable=False),
        Column('Local_File_Path', Text, nullable=False),
        Column('Recognition_Text', Text, nullable=True),
        Column('Storage_Status', Enum(JobStorageStatuses), nullable=True),

    )

    def __init__(self, row):
        self.id = row.JobId
        self.__status = row.Status
        self.local_path = row.Local_File_Path

    @staticmethod
    @database_connection
    def insert_fake_data(connection):
        video_path = (pathlib.Path(
            __file__).parent.parent / 'conqueror' / 'tests' / 'integration_tests_video' / '7bbfc76b.mp4').as_posix()
        connection.execute(JobModel.schema.insert(values=[
            {'Status': JobStatuses.Created, 'Local_File_Path': video_path},
            {'Status': JobStatuses.Uploaded, 'Local_File_Path': video_path},
            {'Status': JobStatuses.Recognized, 'Local_File_Path': video_path},
            {'Status': JobStatuses.Deleted, 'Local_File_Path': video_path},
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
def select_uploaded_jobs(connection) -> List[JobModel]:
    result = []
    for row in connection.execute(JobModel.schema.select()
                                          .where(JobModel.schema.c.Status == JobStatuses.Uploaded)
                                          .where(JobModel.schema.c.Recognition_Started_On == None)):
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
