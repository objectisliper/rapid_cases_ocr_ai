import pathlib
from os.path import exists

import yaml
from fabric.contrib.files import sed
from fabric.operations import local
from fabric.state import env
from fabric.api import task

BASE_DIR = pathlib.Path(__file__).parent
config_path = BASE_DIR / 'deploy_local.yaml'


def get_config(path):
    with open(path) as f:
        config = yaml.safe_load(f)
    return config


deploy_config = get_config(config_path)

ASGI_SUPERVISOR_CONF_NAME = 'recognize_service_asgi.conf'
CELERY_BEAT_CONF_NAME = 'recognize_service_beat.conf'
CELERY_WORKER_CONF_NAME = 'recognize_service_worker.conf'

ASGI_SUPERVISOR_LOCAL_CONF_NAME = 'supervisor_aiohttp_recognize_service.conf'
CELERY_BEAT_LOCAL_CONF_NAME = 'supervisor_recognize_service_beat.conf'
CELERY_WORKER_GET_VIDEOS_LOCAL_CONF_NAME = 'supervisor_recognize_service_get_videos_to_process_worker.conf'
CELERY_WORKER_PROCESS_VIDEO_LOCAL_CONF_NAME = 'supervisor_recognize_service_process_video_worker.conf'

NGINX_LOCAL_CONFIG_NAME = 'nginx_config.conf'

NGINX_CONFIG_NAME = 'recognize_service'

SUPERVISOR_CONF_FILES = [
    (ASGI_SUPERVISOR_LOCAL_CONF_NAME, ASGI_SUPERVISOR_CONF_NAME),
    (CELERY_BEAT_LOCAL_CONF_NAME, CELERY_BEAT_CONF_NAME),
    (CELERY_WORKER_GET_VIDEOS_LOCAL_CONF_NAME, CELERY_WORKER_GET_VIDEOS_LOCAL_CONF_NAME),
    (CELERY_WORKER_PROCESS_VIDEO_LOCAL_CONF_NAME, CELERY_WORKER_PROCESS_VIDEO_LOCAL_CONF_NAME),
]

CURRENT_FILEPATH = pathlib.Path(__file__).parent.as_posix()

ROOT_FILEPATH = pathlib.Path(__file__).parent.parent.as_posix()


def deploy():
    __copy_supervisor_conf()
    __copy_nginx_conf()


def __copy_supervisor_conf():
    if not exists('/var/log/celery'):
        local('mkdir /var/log/celery')
    for celery_daemon_type in ['worker, beat', 'asgi']:
        if not exists(f'/var/log/celery/recognize_service_{celery_daemon_type}.log'):
            local(f'touch /var/log/celery/recognize_service_{celery_daemon_type}.log')
    if not exists(f'{ROOT_FILEPATH}/sockets'):
        local(f'mkdir {ROOT_FILEPATH}/sockets')
        local(f'chown -R www-data:www-data {ROOT_FILEPATH}/sockets')
    for local_conf, server_conf in SUPERVISOR_CONF_FILES:
        supervisor_filepath = f'/etc/supervisor/conf.d/{server_conf}'
        local(f'cp {CURRENT_FILEPATH}/{local_conf} {supervisor_filepath}')
        local(f'sed -i \'s+RECOGNIZE_SERVICE_DIRECTORY+{ROOT_FILEPATH}+g\' {supervisor_filepath}')
        local(f'sed -i \'s+CELERY_BROKER_URL+{deploy_config.get("CELERY_BROKER_URL")}+g\' {supervisor_filepath}')

    local('supervisorctl reread && supervisorctl reload')


def __copy_nginx_conf():
    def sed_nginx_config(path):
        local(f'sed -i \'s+RECOGNIZE_SERVICE_DIRECTORY+{ROOT_FILEPATH}+g\' {path}')
        local(f'sed -i \'s+RECOGNIZE_SERVICE_SERVER_NAME+{deploy_config.get("RECOGNIZE_SERVICE_SERVER_NAME")}+g\' {path}')
        local(f'sed -i \'s+RECOGNIZE_SERVICE_PORT+{deploy_config.get("RECOGNIZE_SERVICE_PORT")}+g\' {path}')

    if exists('/etc/nginx/sites-available'):
        local(f'cp {CURRENT_FILEPATH}/{NGINX_LOCAL_CONFIG_NAME} /etc/nginx/sites-available/{NGINX_CONFIG_NAME}')
        sed_nginx_config(f'/etc/nginx/sites-available/{NGINX_CONFIG_NAME}')
        local(f'cp /etc/nginx/sites-available/{NGINX_CONFIG_NAME} /etc/nginx/sites-enabled/{NGINX_CONFIG_NAME}')

    else:
        local(f'cp {CURRENT_FILEPATH}/{NGINX_LOCAL_CONFIG_NAME} /etc/nginx/conf.d/{NGINX_CONFIG_NAME}.conf')
        sed_nginx_config(f'/etc/nginx/conf.d/{NGINX_CONFIG_NAME}.conf')

    local('systemctl restart nginx')
