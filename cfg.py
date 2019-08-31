class Config:
    class CfgError(TypeError):
        pass

    def __setattr__(self, key, value):
        if key in self.__dict__:
            raise self.CfgError('can not update exist attribute: %s' % key)
        self.__dict__[key] = value


config = Config()
<<<<<<< HEAD
config.db_user = ''
config.db_pwd = ''
=======
config.db_user = 
config.db_pwd = 
>>>>>>> d627fa08c547e3509ac0b52e43465db262f09318
config.db_host = 'stand-server'
config.ai_db = 'AI5'
config.task_table = 't_tasks'
config.ai_home = '/data/AI5/'
config.push_task_script = 'push-job.sh'
config.kill_task_script = 'kill-job.sh'
config.spark_log = 'spark-log.log'
config.task_limit = 1
config.workers = ['master', 'slave1', 'slave2']
config.kill_task_uri = 'http://master:8080/driver/kill/'
config.access_token = '24.a6bcbbe08994a0ecdd83ec252185f9ba.2592000.1567926490.282335-16745497'
config.new_feature_db_uri = 'https://aip.baidubce.com/rest/2.0/face/v3/faceset/group/add'
config.insert_image_uri = 'https://aip.baidubce.com/rest/2.0/face/v3/faceset/user/add'
config.es_host = 'stand-server'
config.es_port = '9200'
config.file_server_host = 'http://stand-server:80/'
