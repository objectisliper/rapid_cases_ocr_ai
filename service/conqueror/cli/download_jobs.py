from os import makedirs, walk
from os.path import isdir
from typing import List

from service.conqueror.cli.download_job import download_job
from service.conqueror.db_models import JobModel, JobStatuses, JobStorageStatuses
from service.conqueror.utils import database_connection



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
            download_job(job, 'jobs_from_live_base')
        print(f'Processed {job_number + 1} of {jobs_to_process_count} Jobs')


if __name__ == "__main__":
    download_all_available_jobs()
