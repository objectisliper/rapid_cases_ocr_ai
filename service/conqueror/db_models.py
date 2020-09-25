import enum
import json
import os
import pathlib
from datetime import datetime, timedelta
from typing import List

from sqlalchemy import (
    MetaData, Table, Column, Integer, String, Enum, Text, DateTime, SmallInteger, or_
)

from service.conqueror.utils import database_connection, RecognitionTimeoutRepeatExceededException


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
        Column('Recognition_Identifiers', Text, nullable=True),
        Column('Exception_Text', Text, nullable=True),
        Column('Number_Of_Repeat', SmallInteger, nullable=True)

    )

    def __init__(self, row):
        self.id = row.JobId
        self.storage_name = row.Storage_Name
        self.__status = row.Status
        self.local_path = row.Local_File_Path
        self.number_of_repeat = row.Number_Of_Repeat or 0
        if row.Recognition_Identifiers:
            self.recognition_identifiers = json.loads(row.Recognition_Identifiers)
            self.url_contains = self.recognition_identifiers['caseClasificationRules']['url'] or []
            self.text_contains = self.recognition_identifiers['caseClasificationRules']['page'] or []
            self.search_phrases = self.recognition_identifiers['searchPhraseIdentifiers'] or []
        else:
            self.recognition_identifiers = {}
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
             'Storage_Name': JobStorageTypes.Default.value, 'JobId': 'test 1',
             'Storage_Status': JobStorageStatuses.Uploaded.value},
            {'Status': JobStatuses.Uploaded, 'Local_File_Path': video_path,
             'Storage_Name': JobStorageTypes.Amazon_S3.value, 'JobId': '3NhmZPwuyE2p8u3GtAFNaxhERIz-2wIA',
             'Storage_Status': JobStorageStatuses.Uploaded.value},
            {'Status': JobStatuses.Uploaded, 'Local_File_Path': video_path,
             'Storage_Name': JobStorageTypes.Default.value, 'JobId': 'iCaoEdL47HvDQH-BK4_ehw2YlMfd_ODd',
             'Storage_Status': JobStorageStatuses.Uploaded.value},
            {'Status': JobStatuses.Deleted, 'Local_File_Path': video_path,
             'Storage_Name': JobStorageTypes.Default.value, 'JobId': 'test 4',
             'Storage_Status': JobStorageStatuses.Uploaded.value},
        ]))

    @database_connection
    def job_start_processing(self, connection):
        if self.number_of_repeat + 1 > int(os.environ.get('SCHEDULING_RECOGNITION_JOB_REPEAT', 3)):
            raise RecognitionTimeoutRepeatExceededException('system trying to process this job too much times')

        connection.execute(self.schema
                           .update()
                           .where(self.schema.c.JobId == self.id)
                           .values(Recognition_Started_On=datetime.utcnow(),
                                   Number_Of_Repeat=self.number_of_repeat + 1))

    @database_connection
    def job_processed(self, recognition_text, connection):
        connection.execute(self.schema
                           .update()
                           .where(self.schema.c.JobId == self.id)
                           .values(Status=JobStatuses.Recognized, Recognition_Text=recognition_text,
                                   Recognition_Competed_On=datetime.utcnow()))

    @database_connection
    def exception_catched(self, exception: str, connection):
        connection.execute(self.schema
                           .update()
                           .where(self.schema.c.JobId == self.id)
                           .values(Status=JobStatuses.Exception, Exception_Text=exception,
                                   Recognition_Competed_On=datetime.utcnow()))


@database_connection
def select_uploaded_jobs(connection) -> List[JobModel]:
    result = []
    timeout_datetime = datetime.utcnow() - timedelta(seconds=int(os.environ.get('SCHEDULING_RECOGNITION_JOB_TIMEOUT', 1800)))
    timeout_repeat_exceeded = os.environ.get('SCHEDULING_RECOGNITION_JOB_REPEAT', 3)
    for row in connection.execute(JobModel.schema.select()
                                          .where(JobModel.schema.c.Status == JobStatuses.Uploaded)
                                          .where(or_(JobModel.schema.c.Recognition_Started_On == None,
                                                     JobModel.schema.c.Recognition_Started_On < timeout_datetime))
                                          .where(or_(JobModel.schema.c.Number_Of_Repeat == None,
                                                     JobModel.schema.c.Number_Of_Repeat <= timeout_repeat_exceeded))
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
