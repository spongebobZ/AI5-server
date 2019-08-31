import json
import os
import re

from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename

from apis import push_task, process_images, list_tasks, kill_task, query_es_data, query_task

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# app.config['UPLOAD_FOLDER'] = '/data/AI5/upload_images'
app.config['UPLOAD_FOLDER'] = 'tmp'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(files):
    for file in files:
        filename = file.filename
        if '.' not in filename or filename.rsplit('.', 1)[1] not in app.config['ALLOWED_EXTENSIONS']:
            break
    else:
        return True
    return False


@app.route('/', methods=['GET'])
def index():
    return render_template('task_list.html')


@app.route('/newMatchTask', methods=['GET', 'POST'])
def match_task_new():
    # """debug"""
    # return render_template('new_success.html', taskID='000001')
    if request.method == 'GET':
        return render_template('new_match_task.html')
    elif request.method == 'POST':
        video_url = request.form['videoUrl']
        match_threshold = int(request.form['matchThreshold'])
        desc = request.form.get('description')
        if not video_url or not match_threshold:
            return render_template('new_match_task.html', message='please input complete')
        if desc and re.match(r'[a-zA-Z0-9_,\s]+', desc).string != desc:
            return render_template('new_match_task.html',
                                   message='task description only accept letters, nums, _/, and space')
        r = upload_image().json
        if r.get('code') != 0:
            return render_template('new_match_task.html', message='incorrect images')
        process_result = process_images(r.get('images'))
        match_db = process_result['db_name']
        user_ids = ','.join(process_result['user_ids'])
        push_result = push_task(video_url, 0, desc,
                                **{'match_dbs': match_db, 'match_min_threshold': match_threshold, 'user_ids': user_ids})
        task_id = push_result.get('taskID')
        if not task_id:
            return render_template('new_match_task.html', message='create task failed')
        return render_template('new_success.html', taskType=0, taskID=task_id)


@app.route('/newFuzzyTask', methods=['GET', 'POST'])
def fuzzy_task_new():
    # """debug"""
    # return render_template('new_success.html', taskID='000001')
    if request.method == 'GET':
        return render_template('new_fuzzy_task.html')
    elif request.method == 'POST':
        video_url = request.form['videoUrl']
        age_low = request.form.get('age_low') == '' and -1 or int(request.form.get('age_low'))
        age_high = request.form.get('age_high') == '' and -1 or int(request.form.get('age_high'))
        beauty_low = request.form.get('beauty_low') == '' and -1 or int(request.form.get('beauty_low'))
        beauty_high = request.form.get('beauty_high') == '' and -1 or int(request.form.get('beauty_high'))
        faceshape = request.form.get('faceshape')
        expression = request.form.get('expression')
        gender = request.form.get('gender')
        glasses = request.form.get('glasses')
        emotion = request.form.get('emotion')
        race = request.form.get('race')
        desc = request.form.get('description')
        search_condition = {'ageLow': age_low, 'ageHigh': age_high, 'beautyLow': beauty_low, 'beautyHigh': beauty_high,
                            'expression': expression, 'faceShape': faceshape, 'gender': gender, 'glasses': glasses,
                            'emotion': emotion, 'race': race}
        keys = tuple(search_condition.keys())
        for k in keys:
            if search_condition[k] in (-1, 'all'):
                search_condition.pop(k)
        if not video_url:
            return render_template('new_fuzzy_task.html', message='please input complete')
        if desc and re.match(r'[a-zA-Z0-9_,\s]+', desc).string != desc:
            return render_template('new_match_task.html',
                                   message='task description only accept letters, nums, _/, and space')
        push_result = push_task(video_url, 1, desc, **{'search_condition': json.dumps(search_condition)})
        task_id = push_result.get('taskID')
        if not task_id:
            return render_template('new_fuzzy_task.html', message='create task failed')
        return render_template('new_success.html', taskType=1, taskID=task_id)


@app.route('/uploadImg', methods=['POST'])
def upload_image():
    files = []
    for i in range(1000):
        if not request.files.get('file' + str(i + 1)):
            break
        file = request.files['file' + str(i + 1)]
        files.append(file)
    if not files or not allowed_file(files):
        return jsonify({'code': -1, 'result': 'incorrect images'})
    paths = []
    for file in files:
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        paths.append(save_path)
    return jsonify({'code': 0, 'result': 'upload success', 'images': paths})


@app.route('/taskInfo/<task_type>/<task_id>', methods=['GET'])
def task_info(task_type, task_id):
    task_type = int(task_type)
    task = query_task(task_type, task_id)
    if task_type == 0:
        return render_template('match_task_info.html', taskID=task_id, submitTime=task['submit_time'],
                               status=task['status'],
                               videoUrl=task['video_url'], matchMinThreshold=task['match_min_threshold'],
                               description=task['task_desc'], user_ids=task['user_ids'])
    elif task_type == 1:
        return render_template('fuzzy_task_info.html', taskID=task_id, submitTime=task['submit_time'],
                               status=task['status'],
                               videoUrl=task['video_url'], searchCondition=task['search_condition'],
                               description=task['task_desc'])


@app.route('/taskList', methods=['GET', 'POST'])
def task_list():
    tasks = list_tasks()
    return jsonify(tasks)


@app.route('/killTask/<task_type>/<task_id>', methods=['GET', 'DELETE'])
def task_kill(task_type, task_id):
    status = query_task(int(task_type), task_id)['status']
    if status != 'RUNNING':
        return jsonify({'code': -1, 'message': 'task not running'})
    r = kill_task(task_id)
    # r = {'code': 0, 'message': 'kill taskL %s success' % task_id}
    if request.method == 'DELETE':
        return jsonify(r)
    elif request.method == 'GET':
        return index()


@app.route('/queryMatchData/<task_type>/<task_id>', methods=['GET'])
def query_match_data(task_type, task_id):
    data = query_es_data(task_type, task_id)
    return jsonify(data)


if __name__ == '__main__':
    app.run('127.0.0.1', 5566)
