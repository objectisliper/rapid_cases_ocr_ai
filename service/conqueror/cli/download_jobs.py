import base64
from os import makedirs, walk
from os.path import isdir
from typing import List

import simplejson

from service.conqueror.db_models import JobModel, JobStatuses, JobStorageStatuses
from service.conqueror.io import VideoFile
from service.conqueror.utils import database_connection, get_video_from_amazon_server

EXPECTED_FILE_TEMPLATE = {
    "SearchPhrasesFound": [
    ],
    "URLContainsResults": {
    },
    "TextContainsResults": {
    }
}


@database_connection
def select_all_available_jobs(connection) -> List[JobModel]:
    result = []
    for row in connection.execute(JobModel.schema.select()
                                          .where(
        JobModel.schema.c.Status.in_([JobStatuses.Uploaded, JobStatuses.Recognized]))
                                          .where(JobModel.schema.c.Storage_Status == JobStorageStatuses.Uploaded)):
        result.append(JobModel(row))
    return result


def download_all_available_jobs():
    if not isdir('../jobs_from_live_base'):
        makedirs('../jobs_from_live_base')

    already_downloaded_jobs = next(walk('../jobs_from_live_base'))[1]

    all_jobs_list = select_all_available_jobs()
    jobs_to_process_count = len(all_jobs_list)

    with open('../../../.jobignore', 'r') as jobignore:
        ignored_jobs = [ignored_job.rstrip() for ignored_job in jobignore.readlines()]

    for job_number, job in enumerate(all_jobs_list):
        if job.id not in already_downloaded_jobs and job.id not in ignored_jobs:
            jobs_dir = f'../jobs_from_live_base/{job.id}'
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
        print(f'Processed {job_number + 1} of {jobs_to_process_count} Jobs')


if __name__ == "__main__":
    download_all_available_jobs()
