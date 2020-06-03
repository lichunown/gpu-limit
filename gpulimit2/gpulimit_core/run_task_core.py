# -*- coding: utf-8 -*-
import os, time
import threading
import logging
import heapq # TODO

from gpulimit.utils import prettytable as pt
from gpulimit.utils import check_input

from gpulimit_core.system_info import System
from gpulimit_core.tasks import Task
from gpulimit_core.scheduling import BaseScheduling


class TaskManage(object):
    """
    Task Manage Class
    
    Property:
        
        tasks                    list: all task list
        logdir                   str: log dir path
        scheduling               scheduling class
        setter_param             a dict of variable parameter
        
    Functions:
        
        start(self, logdir='./tmp', MINI_MEM_REMAIN=1024, MAX_ERR_TIMES=5, WAIT_TIME=10)
        add_task(self, new_task, priority=5)
        get_task(self, id)
        rm_task(self, id)
        mv_task(self, id, index)
        change_priority(self, id, priority)
        
    Decorator:
        
        client
        
    """
    def __init__(self, scheduling, logdir='./tmp'):
        self.queue = []
        self._id_give = 0
        
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        else:
            # del logfiles in log dir
            for logname in os.listdir(self.logdir):
                path = os.path.join(logdir, logname) 
                if os.path.isfile(path):
                    os.remove(path)   
                    
        self.logdir = logdir
        self.log_file = os.path.join(self.logdir, 'main.log')

        logging.basicConfig(filename=self.log_file, level=logging.INFO, format='%(asctime)s - %(message)s')
        logging.basicConfig(filename=self.log_file, level=logging.WARNING, format='%(asctime)s - %(message)s')

        # self.func_map = {}
        self.scheduling = scheduling
        
        self._setter_param = {
            'WAIT_TIME': 10,
        }
        
        self._setter_param.update(self.scheduling.param)
        
        self.start_thread = threading.Thread(target=self._thread_start_task)
        self.lock = threading.RLock()
        
    def set_param(self, k, v):
        self._setter_param[k] = v
        if k in self.scheduling.param:
            self.scheduling.param[k] = v
    
    def get_param(self, k):
        return self._setter_param[k]
    
    def start(self, **kwargs):
        """
        init setting, and start timer scheduling
        
        """
        for k, v in kwargs.items():
            self.set_param(k, v)
        
        self.start_thread.start()
        
        
    def _thread_start_task(self):
        while True:
            result = self.scheduling.timer_call(self)
            time.sleep(self.get_param('WAIT_TIME'))
    
    @property
    def tasks(self):
        return self.queue.copy()
    
    def __len__(self):
        return len(self.queue)
    
    def add_task(self, new_task):
        priority = new_task.priority
        
        i = 0
        for i, task in enumerate(self.queue):
            if priority >= task.priority:
                i = i + 1
            if priority < task.priority:
                break
            
        self.lock.acquire()
        self.queue.insert(i, new_task)
        self.lock.release()
    
    
    def get_task(self, id):
        for task in self.queue:
            if task.id == id:
                return task
        return None
    
    def rm_task(self, id):
        task = self.get_task(id)
        if task is None:
            return False
        task.kill()
        self.lock.acquire()
        self.queue.remove(task)
        self.lock.release()
        return True
           
    def mv_task(self, id, index):
        task = self.get_task(id)
        if task is None:
            return False
        self.lock.acquire()
        self.queue.remove(task)
        self.queue.insert(index, task)
        self.lock.release()
        return True
    
    def change_priority(self, id, priority):
        task = self.get_task(id)
        if task is None:
            return False
        self.lock.acquire()
        self.queue.remove(task)
        self.lock.release()
        self.add_task(task)
        return True

    
    def add(self, pwd, cmds, *, priority:int=5, logpath=None):
        '''
        add [cmds]                    ls GPU task queue status
        
        Options:
            
            --priority [priority]     set task priority.
            --logpath  [path]         set task output file path.
        '''
        def task_callback():
            self.scheduling.callback_process_end(self)
            
        if logpath is None:
            logpath = os.path.join(self.logdir, f'{self._id_give}.log')
            
        task = Task(self, self._id_give, pwd, cmds, priority, logpath, task_callback)
        self._id_give += 1
        self.add_task(task, priority)
        
        result = f'add task(id:{task.id}) to queue(len: {len(self.queue)})'
        logging.info(f'add task(id:{task.id}): {pwd}$ {cmds})')
    
        err, result_ = self.scheduling.callback_add_process(self)
        
        return err, '\n'.join([result, result_])
    
    


# task_manage = TaskManage(BaseScheduling())



        
