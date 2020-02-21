# -*- coding: utf-8 -*-
import subprocess
import os, time, traceback
import threading
import logging
import psutil

class TaskStatus(object):
    status2id = dict(zip(['CMD_ERROR', 'complete', 'waiting', 'running', 'runtime_error', 'killed', 'paused'], range(-1, 5)))
    id2status = dict(zip(status2id.values(), status2id.keys()))
    
    can_start_list = ['waiting', 'runtime_error', 'killed']
    auto_start_list = ['waiting', 'runtime_error']
    
    def __init__(self, status='waiting', run_times=0, err_code=None):
        self._status = None
        self.run_times = run_times
        self.err_code = err_code
        
        if isinstance(status, int):
            self._set_status_id(status)
            
        elif isinstance(status, str):
            self._set_status_name(status)       
            
        else:
            raise TypeError(f'status must be int or str, not {type(status)}')
    
    @property
    def id(self):
        return self.status2id[self.status]
    
    @id.setter
    def id(self, nid):
        self._set_status_id(nid)
        
    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, new_status):
        self._set_status_name(new_status)
        
    def _set_status_id(self, id):
            if id in self.id2status:
                self._status = self.id2status[id]
            else:
                raise ValueError(f'status id must be: {self.id2status}')
    
    def _set_status_name(self, name):
            if name in self.status2id:
                self._status = name
            else:
                raise ValueError(f'status name must be: {self.status2id}')
            
    def __str__(self):
        return self.status
    
    def __repr__(self):
        return f'TaskStatus({self.status})'


class Sort(object):
    start_sort_type = {
        'waiting': 0,
        'runtime_error': 1,
        'paused': 2,
        'killed': 2,
        'running': 3,
        'complete': 3,
        'CMD_ERROR': 3,
    }
    show_sort_type = {
        'running': 0,
        'paused': 1,
        'waiting': 2,
        'killed': 3,
        'runtime_error': 3,
        'complete': 4,
        'CMD_ERROR': 5,
    }
    
    sort_types = ['id', 'priority', 'show', 'run']
    
    def __call__(self, *args, **kwargs):
        return self.sort(*args, **kwargs)
    
    @staticmethod
    def sort(tasks, type):
        if type == 'run':
            tasks = sorted(tasks, key=lambda x: x.id)
            tasks = sorted(tasks, key=lambda x: Sort.start_sort_type[x.status.status])

        elif type == 'show':
            tasks = sorted(tasks, key=lambda x: x.id)
            tasks = sorted(tasks, key=lambda x: Sort.show_sort_type[x.status.status])
            
        elif type == 'id':
            tasks = sorted(tasks, key=lambda x: x.id)
            
        elif type == 'priority':
            tasks = sorted(tasks, key=lambda x: x.id)
            tasks = sorted(tasks, key=lambda x: x.priority)
        else:
            return f'[Error]: can not found sort type `{type}`, which can only use {Sort.sort_types}'

        return tasks
        
        
        
class Task(object):
    def __init__(self, task_manage, id, pwd, cmds, out_path=None):
        self.task_manage = task_manage
        self.id = id
        self.pwd = pwd
        self.cmds = cmds
        self.out_path = out_path
        
        self.priority = None
        self.pid = None
        self.gpu = None
        
        self.run_times = 0
        self.out_file = None
        self.pkg_process = None
        self.process = None
        self.available = True
        self.paused = False
        
        self.killed = False
        self.debug_msg = None
        
    def _run_task(self, GPU_id):
        try:
            if self.out_path is not None:
                self.out_file = open(self.out_path, 'w')
            self.gpu = GPU_id
            env = os.environ.copy()
            env['CUDA_VISIBLE_DEVICES'] = str(GPU_id)
            self.process = subprocess.Popen(self.cmds, stdout=self.out_file, shell=True, stderr=subprocess.STDOUT, cwd=self.pwd, env=env)
            self.pid = self.process.pid
            logging.info(f'[starting({self.id}: GPU:{GPU_id})]: {self.pwd}$ {self.cmds}')
        except Exception as e:
            self.available = False
            logging.info(f'[CMD_ERROR({self.id}: GPU:{GPU_id})]: {self.pwd}$ {self.cmds} \nerror:\n{e}')
            msg = traceback.format_exc()
            logging.info(msg)
            self.debug_msg = 'cmds: ' + str(self.cmds) + "\n" + msg
            self.task_manage.scheduling.callback_process_end(self.task_manage)
            return
        self.process.wait()
        self.gpu = None
        self.pid = None
        logging.info(f'[finish({self.id}: GPU:{GPU_id})]: {self.pwd}$ {self.cmds}')
        
        self.task_manage.scheduling.callback_process_end(self.task_manage)

    def start(self, GPU_id):
        if self.killed:
            self.killed = False
        if self.status.status in ['waiting', 'runtime_error', 'killed']:
            self.run_times += 1
            self.pkg_process = threading.Thread(target=self._run_task, args=(GPU_id,))
            self.pkg_process.start()
            
            return 0, f'[info]: start task {self.id} succeed.'
        else:
            return 1, f'[info]: can not start task {self.id} which have status `{self.status.status}`'
        
    def kill(self):
        if self.process is not None and self.status.status == 'running':
            self.process.terminate()
            time.sleep(1)
            self.process.kill()
            self.killed = True
            
            self.gpu = None
            self.pid = None
            return 0, f'[info]: kill task {self.id} succeed.'
        else:
            return 1, f'[warning]: can not kill task {self.id} which have status `{self.status.status}`'

    def pause(self):
        if self.pid is not None:
            if not self.paused:
                psutil.Process(self.pid).suspend()
                self.paused = True
                return 0, f'[Info]: task {self.id} paused.'
            return 1, f'[Warning]: task {self.id} have been paused before.'
        return 1, f'[Error]: task {self.id} not running.'
    
    def resume(self):
        if self.pid is not None:
            if self.paused:
                psutil.Process(self.pid).resume()
                self.paused = False
                return 0, f'[Info]: task {self.id} resume.'
            return 1, f'[Warning]: task {self.id} is running.'
        return 1, f'[Error]: task {self.id} not running.'
    
    @property
    def status(self):
        if not self.available:
            return TaskStatus('CMD_ERROR', self.run_times)
        
        if self.process is None:
            return TaskStatus('waiting', self.run_times)
        
        if self.killed:
            return TaskStatus('killed', self.run_times)
        
        status = self.process.poll()
        if status is None:
            if self.paused:
                return TaskStatus('paused', self.run_times)
            return TaskStatus('running', self.run_times)
        
        if status == 0:
            return TaskStatus('complete', self.run_times)
        else:
            return TaskStatus('runtime_error', self.run_times, err_code=status)