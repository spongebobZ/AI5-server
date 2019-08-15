import logging
import functools
import requests
import json
from cfg import config
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger()


def interface_log(log_type):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            tmp = list(args)
            if kw:
                tmp.append(kw)
            try:
                r = func(*args, **kw)
                logger.info('%s,func:%s,args:%s' % (log_type, func.__name__, ','.join(str(x) for x in tmp)))
                return r
            except Exception as e:
                logger.error(e)
                logger.error('%s,func:%s,args:%s' % (log_type, func.__name__, ','.join(str(x) for x in tmp)))

        return wrapper

    return decorator


def get_match_tasks():
    match_tasks = []
    workers = config.workers
    while True:
        for worker in workers:
            ip, port = worker, 4040
            while True:
                uri = 'http://%s:%s/api/v1/applications' % (ip, port)
                try:
                    rsp = requests.get(uri)
                    # only one task would refer to one couple ip:port
                    rsp_content = json.loads(rsp.content)[0]
                    task_name = rsp_content.get('name')
                    if 'match_faces_in_aimDB' not in task_name:
                        continue
                    driver_id = rsp_content.get('id')
                    match_tasks.append(driver_id)
                except requests.exceptions.ConnectionError:
                    # if connect time out then means no any more task on this worker
                    break
                finally:
                    port += 1
        if match_tasks:
            break
        time.sleep(3)
    return match_tasks
