from os import makedirs
from os.path import isdir
from typing import List

import simplejson

from service.conqueror.db_models import JobModel
from service.conqueror.utils import get_video_from_amazon_server, database_connection, FileNotFoundException

EXPECTED_FILE_TEMPLATE = {
    "SearchPhrasesFound": [
    ],
    "URLContainsResults": {
    },
    "TextContainsResults": {
    }
}


@database_connection
def select_job_by_id(job_id: str, connection) -> JobModel:
    return JobModel(list(connection.execute(JobModel.schema.select()
                                   .where(JobModel.schema.c.JobId == job_id)))[0])


def download_job(job: JobModel, directory: str):
    jobs_dir = f'../{directory}/{job.id}'
    makedirs(jobs_dir)
    video = get_video_from_amazon_server(job.id)
    with open(f'{jobs_dir}/case.webm', 'wb') as video_file:
        video_file.write(video)
    with open(f'{jobs_dir}/input.json', 'w') as recognition_identifiers_file:
        recognition_identifiers_file.write(
            simplejson.dumps(job.recognition_identifiers, indent=4, sort_keys=True)
        )
    with open(f'{jobs_dir}/expected.json', 'w') as expected_file:
        expected_file.write(
            simplejson.dumps(EXPECTED_FILE_TEMPLATE, indent=4, sort_keys=True)
        )


if __name__ == "__main__":
    if not isdir('../single_job_download_from_live'):
        makedirs('../single_job_download_from_live')
    try:
        download_job(select_job_by_id('some_job_id_hash'), 'single_job_download_from_live')
    except IndexError:
        print('\033[91m' + 'There is no job with such caseId in database' + '\033[0m')
