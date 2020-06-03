# -*- coding: utf-8 -*-
import subprocess
import sys
import os, time, traceback
import signal
import threading
import logging
import psutil

from utils import asyn

class Status(int):
    _map = {
        'waiting': 0,
        'running': 1,
        'complete': 2,
        'runtime_error': 3,
        'CMD_ERROR': 4,
        'killed': 5,
        'paused': 6,
    }
    
    _int2str = dict([(v, k) for k, v in _map.items()])
    
    _sort_show = dict(zip(['running', 'waiting', 'runtime_error', 'killed', 
                           'complete', 'paused', 'CMD_ERROR'], range(7)))
    
    _sort_run = dict(zip(['waiting', 'runtime_error', 'paused', 'killed', 
                           'complete', 'CMD_ERROR', 'running'], range(7)))
    
    def __new__(cls, status):
        if isinstance(status, str):
            status = cls._map[status]
        if status not in cls._int2str:
            raise ValueError
        return super(Status, cls).__new__(cls, status)
    
    @property
    def sort_show(self):
        return self._sort_show[self.str]
    
    @property
    def sort_run(self):
        return self._sort_run[self.str]
    
    @property
    def str(self):
        return str(self)
    
    def __str__(self):
        return self._int2str[self]
    
    def __repr__(self):
        return f'Status({self.str})'

   
STATUS_RUNNING = Status('running')
STATUS_WAITING = Status('waiting')
STATUS_RUNTIME_ERROR = Status('runtime_error')
STATUS_KILLED = Status('killed')
STATUS_COMPLETE = Status('complete')
STATUS_PAUSED = Status('paused')
STATUS_CMD_ERROR = Status('CMD_ERROR')


class Task(object):
    def __init__(self, id, pwd, cmds, priority=5, out_path=None, end_callback=None):
        self.id = id
        self.pwd = pwd
        self.cmds = cmds
        self.priority = priority
        self.out_path = out_path
        self.end_callback = end_callback
        
        self.gpu = None
        self.start_time = None
        self.end_time = None
        
        self.run_times = 0

        self.out_file = None
        self.pkg_process = None
        self.process = None
        
        self.status = STATUS_WAITING
        self.debug_msg = None # if cmd_error, save error msg
        
        if self.end_callback is None:
            self.end_callback = lambda: None
            
    @property
    def pid(self):
        if self.status == Status('running'):
            return self.process.pid
        return None

    @property
    def running_time(self):
        if self.start_time is None:
            return 0
        end_time = time.time() if self.end_time is None else self.end_time
        return end_time - self.start_time
            
    @staticmethod
    def _change_gpu_id(inputs):
        if isinstance(inputs, (int, float, str)):
            return str(inputs) 
        if isinstance(inputs, (list, tuple)):
            return str(inputs)[1: -1]

    @asyn
    def _run_task(self, GPU_id):
        self.start_time = time.time()
        self.gpu = GPU_id
        self.end_time = None
        self.run_times += 1
        self.status = STATUS_RUNNING
        
        try:
            if self.out_path is not None:
                self.out_file = open(self.out_path, 'w')
                self.out_file.write(f'{self.pwd}# {self.cmds}\n')
            env = os.environ.copy()
            env['CUDA_VISIBLE_DEVICES'] = self._change_gpu_id(GPU_id)
            self.process = subprocess.Popen(self.cmds, stdout=self.out_file, shell=False,
                                            stderr=subprocess.STDOUT, cwd=self.pwd, env=env)
            
        except Exception as e:
            self.status = STATUS_CMD_ERROR
            logging.info(f'[CMD_ERROR({self.id}: GPU:{GPU_id})]: {self.pwd}$ {self.cmds} \nerror:\n{e}')
            msg = traceback.format_exc()
            logging.info(msg)
            self.debug_msg = 'cmds: ' + str(self.cmds) + "\n" + msg
            self.end_callback()
            return
        
        logging.info(f'[starting({self.id}: GPU:{GPU_id})]: {self.pwd}$ {self.cmds}')
        self.process.wait()
        
        self.end_time = time.time()
        self.gpu = None
        self.status = STATUS_COMPLETE
        
        logging.info(f'[finish({self.id}: GPU:{GPU_id})]: {self.pwd}$ {self.cmds}')
        self.end_callback()

    @asyn
    def start(self, GPU_id):
        if self.status == STATUS_PAUSED:
            return self.resume()
        if self.status in [STATUS_WAITING, STATUS_RUNTIME_ERROR, STATUS_KILLED]:
            self._run_task(GPU_id)
            return 0, f'[info]: start task {self.id} succeed.'
        else:
            return 1, f'[info]: can not start task {self.id} which have status `{self.status}`'
        
    @asyn
    def kill(self):
        if self.process is not None and self.status == STATUS_RUNNING:
            self.status = STATUS_KILLED
            
            self.process.terminate()
            time.sleep(5)
            self.process.kill()
            
            self.gpu = None

            return 0, f'[info]: kill task {self.id} succeed.'
        else:
            return 1, f'[warning]: can not kill task {self.id} which have status `{self.status}`'

    @asyn
    def pause(self):
        if self.pid is not None:
            if self.status != STATUS_PAUSED:
                psutil.Process(self.pid).suspend()
                self.status = STATUS_PAUSED
                return 0, f'[Info]: task {self.id} paused.'
            return 1, f'[Warning]: task {self.id} have been paused before.'
        return 1, f'[Error]: task {self.id} not running.'
    
    @asyn
    def resume(self):
        if self.pid is not None:
            if self.status == STATUS_PAUSED:
                psutil.Process(self.pid).resume()
                self.status = STATUS_RUNNING
                return 0, f'[Info]: task {self.id} resume.'
            return 1, f'[Warning]: task {self.id} is running.'
        return 1, f'[Error]: task {self.id} not running.'


if __name__ == '__main__':
    a = Task(0, './', ['sleep', '45'])
    