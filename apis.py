import base64
import json
import time
import requests
import os
import subprocess
import threading

from uuid import uuid4
from elasticsearch import Elasticsearch

from cfg import config
from tools import interface_log
from sql_manager import select, insert, update


@interface_log('NEW TASK')
def push_task(video_address, match_dbs, match_min_threshold, task_desc=None, user_ids=None):
    """
    :param video_address:
    :param match_dbs:
    :param match_min_threshold:
    :param task_desc:
    :param user_ids:
    :return:
    """
    old_tasks = select(config.task_table, 'appID', **{'status': 'RUNNING'})
    if len(old_tasks) >= config.task_limit:
        return {'error': 'exceed limit of tasks'}
    lock = threading.Lock()
    lock.acquire()
    latest_task_id = select(config.task_table, 'max(taskID)')
    new_task_id = '%06d' % (latest_task_id == [] and 1 or int(latest_task_id[0][0]) + 1)
    command_result = os.system('cd %s && sh ./%s %s %s %s %s' % (
        config.ai_home, config.push_task_script, video_address, new_task_id, match_dbs, match_min_threshold))
    assert command_result == 0, 'push task failed: %s' % command_result
    command_result_get_id = subprocess.getstatusoutput(
        "cat %s/%s | grep driver-|head -1|awk '{print $9}'" % (config.ai_home, config.spark_log))
    assert command_result_get_id[0] == 0, 'get driver id failed: %s' % str(command_result_get_id)
    driver_id = command_result_get_id[1]
    lock.release()
    insert(config.task_table,
           **{'taskID': new_task_id, 'appID': driver_id, 'status': 'RUNNING',
              'submit_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
              'video_url': video_address, 'match_dbs': match_dbs, 'match_min_threshold': match_min_threshold,
              'task_desc': task_desc, 'user_ids': user_ids})
    return {'taskID': new_task_id}


@interface_log('KILL TASK')
def kill_task(task_id):
    """
    :param task_id:
    :return:
    """
    query_rs = select(config.task_table, 'appID', **{'taskID': task_id})
    assert query_rs, 'not exist task id: %s' % task_id
    driver_id = query_rs[0]
    delete_rsp = requests.post(config.kill_task_uri, data={'id': driver_id, 'terminate': True})
    assert delete_rsp.status_code == 200, 'http error: %s' % delete_rsp.status_code
    command_result = os.system('cd %s && sh ./%s %s' % (config.ai_home, config.kill_task_script, task_id))
    assert command_result == 0, 'clean task failed:%s' % task_id
    sql_result = update(config.task_table, {'status': 'KILLED'}, **{'taskID': task_id})
    assert sql_result == 1, 'update multi record: %s' % sql_result
    return {'code': 0, 'message': 'kill taskL %s success' % task_id}


@interface_log('INSERT IMAGES')
def process_images(images):
    """
    :param images: images path on the server
    :return: {db_name,user_ids}
    """
    db_name = str(uuid4()).replace('-', '')
    params = {'access_token': config.access_token}
    rsp_new_db = requests.post(config.new_feature_db_uri, params=params, json={'group_id': db_name})
    content_new_db = json.loads(rsp_new_db.content)
    assert content_new_db.get('error_code') == 0, 'create feature db failed:%s' % content_new_db.get('error_msg')
    user_ids = []
    for image in images:
        with open(image, 'rb') as fr:
            data = base64.b64encode(fr.read()).decode('utf-8')
            rsp_insert_image = requests.post(config.insert_image_uri, params=params,
                                             json={'image': data, 'image_type': 'BASE64', 'group_id': db_name,
                                                   'user_id': os.path.basename(image).split('.')[0],
                                                   'user_info': os.path.basename(image).split('.')[0],
                                                   'quality_control': None, 'liveness_control': None})
            content_insert_image = json.loads(rsp_insert_image.content)
            assert content_insert_image.get('error_code') == 0, 'insert image failed: %s' % image
            user_ids.append(os.path.basename(image).split('.')[0])
    return {'db_name': db_name, 'user_ids': user_ids}


@interface_log('LIST TASKS')
def list_tasks():
    """
    :return:[{'taskID':taskID1,...},{'taskID':taskID2,...},...]
    """
    select_keys = ('taskID', 'submit_time', 'status', 'video_url', 'match_dbs', 'match_min_threshold')
    tasks = select(config.task_table, *select_keys, **{'status': 'RUNNING'})
    task_list = []
    for task in tasks:
        tmp_dict = dict(zip(select_keys, task))
        task_list.append(tmp_dict)
    return task_list


@interface_log('GET TASK')
def query_task(task_id):
    """
    :param task_id:
    :return:
    """
    select_keys = (
        'taskID', 'submit_time', 'status', 'video_url', 'match_dbs', 'match_min_threshold', 'task_desc', 'user_ids')
    task = select(config.task_table, *select_keys, **{'taskID': task_id})
    assert len(task) == 1, 'task record not equals 1: %s' % len(task)
    return dict(zip(select_keys, task[0]))


@interface_log('QUERY MATCH DATA')
def query_es_data(task_id):
    """
    :param task_id:
    :return:[{match_frame1},{match_frame2}]
    """
    es = Elasticsearch(hosts=config.es_host, port=config.es_port)
    r = es.search(index=task_id, params={'size': 10000})
    assert r, 'query match data failed: %s' % r
    result = r['hits']['hits']
    all_result = [{}] * r['hits']['total']
    file_svr_host = config.file_server_host
    for i, e in enumerate(result):
        matches = []
        frame_result = e['_source']['matches'].values()
        for m in frame_result:
            matches.extend(m)
        format_result = {'taskID': e['_source']['taskID'], 'eventTime': e['_source']['eventTime'],
                         'imagePath': file_svr_host + e['_source']['imagePath'], 'matches': matches}
        all_result[i] = format_result
    all_result.sort(key=lambda x: x['eventTime'])
    all_result.reverse()
    return all_result


if __name__ == '__main__':
    r = query_es_data('000023')
    print(r)
