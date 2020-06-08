# -*- coding: utf-8 -*-
import os, time
import threading
import logging
import heapq # TODO

from gpulimit.utils import prettytable as pt
from gpulimit.utils import check_input

from .system_info import System
from .tasks import Task, STATUS_COMPLETE, STATUS_CMD_ERROR, Status
from .scheduling import BaseScheduling


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
    def __init__(self, scheduling):
        self.queue = []
        self._id_give = 0
        
        self.logdir = None
        self.func_map = {}
        self.scheduling = scheduling
        
        self._setter_param = {
            'TIMER_POLLING_TIME': 10,
        }
        
        self._setter_param.update(self.scheduling.param)
        
        self.start_thread = threading.Thread(target=self._thread_start_task)
        self.lock = threading.RLock()
        # print('init')
        
    def set_param(self, k, v):
        self._setter_param[k] = v
        if k in self.scheduling.param:
            self.scheduling.param[k] = v
    
    def get_param(self, k):
        return self._setter_param[k]
    
    def get_params(self):
        return self._setter_param.items()
        
    def start(self, logdir='./tmp', **kwargs):
        """
        init setting, and start timer scheduling
        
        """
        print('start')
        
        self.logdir = logdir
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        else:
            # del logfiles in log dir
            for logname in os.listdir(self.logdir):
                path = os.path.join(logdir, logname) 
                if os.path.isfile(path):
                    os.remove(path)   

        self.log_file = os.path.join(self.logdir, 'main.log')

        logging.basicConfig(filename=self.log_file, level=logging.INFO, format='%(asctime)s - %(message)s')
        logging.basicConfig(filename=self.log_file, level=logging.WARNING, format='%(asctime)s - %(message)s')


        for k, v in kwargs.items():
            self.set_param(k, v)
        
        self.start_thread.start()
        
        
    def _thread_start_task(self):
        while True:
            # print('call timer_call')
            self.scheduling.timer_call(self)
            time.sleep(self.get_param('TIMER_POLLING_TIME'))
    
    @property
    def tasks(self):
        return self.queue.copy()
    
    def __len__(self):
        return len(self.queue)
    
    def add_task(self, new_task):
        self.lock.acquire()
        self.queue.append(new_task)
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
        task.priority = priority
        return True

    
    def add(self, pwd, cmds, *, priority:int=5, logpath=None):
        '''
        add [cmds]                    ls GPU task queue status
        
        Options:
            
            --priority [priority]     set task priority.
            --logpath  [path]         set task output file path.
        '''
        priority = int(priority)
        
        def task_callback():
            self.scheduling.callback_process_end(self)
            
        if logpath is None:
            logpath = os.path.join(self.logdir, f'{self._id_give}.log')
        
        task = Task(self._id_give, pwd, cmds, priority, logpath, task_callback)
        self._id_give += 1
        self.add_task(task)
        
        result = f'add task(id:{task.id}) to queue(len: {len(self.queue)})'
        logging.info(f'add task(id:{task.id}): {pwd}$ {cmds})')
    
        err, result_ = self.scheduling.callback_add_process(self)
        
        return err, '\n'.join([result, result_])
    
    
    def client(self, client_cmd):
        """
        This is decorator functions.
        
        Examples:
            
            ```
            task_manage = TaskManage(...)
            @task_manage.client('example')
            def example(a, b, *, c='c', d='d'):
                pass
            ```
            
            **Args which have default value, must set it as `inspect.kwonlyargs`**
            
        """
        def decorator(func):
            self.func_map[client_cmd] = func
            return func
        return decorator
    

task_manage = TaskManage(BaseScheduling())


@task_manage.client('ls')
def ls(*, all=False):
    '''
        ls                            ls GPU task queue status
        
        Options:
            
            --all                     default ls only show <80 commands, 
                                      use `all` to show all commands. 
            --sort                    show by different sort type. 
                                      can use: ['id', 'priority', 'show', 'run']
    '''
    
    (all,), err_msg = check_input(((all, bool), ))
    if err_msg: return 1, err_msg
    tasks = task_manage.tasks
    
    table = pt.PrettyTable(['[ID]', 'num', 'status', 'run_times', 'pwd', 'cmds'])
    table.border = False
    for i, task in enumerate(tasks):
        status = str(task.status) + f'(GPU:{task.gpu})' if task.gpu is not None else str(task.status)
        if not all:
            table.add_row([task.id, i, status, task.run_times, task.pwd+'#', " ".join(task.cmds)[:80]])
        else:
            table.add_row([task.id, i, status, task.run_times, task.pwd+'#', " ".join(task.cmds)])

    return 0, str(table)


@task_manage.client('show')
def show(id):
    '''
        show [id]                     show task [id] details.

    '''
    
    (id,), err_msg = check_input(((id, int),))
    if err_msg:
        return 1, err_msg
    
    task = task_manage.get_task(id)
    if task is None:
        return 1, f'[error]: can not found id {id} in task queue.'
    
    table = pt.PrettyTable(['name', 'value'])
    table.border = False
    table.align = 'l'
    table.add_row(['task id:', task.id])
    table.add_row(['task pid:', task.pid])
    table.add_row(['priority:', task.priority])
    table.add_row(['use gpu:', task.gpu])
    table.add_row(['run times:', task.run_times])
    table.add_row(['status:', task.status])
    table.add_row(['out file:', task.out_path])
    table.add_row(['pwd:', task.pwd])
    table.add_row(['cmds:', " ".join(task.cmds)])
    return 0, str(table)


@task_manage.client('rm')
def rm(id):
    '''
        rm [id]                       remove task [id] from manage, if task is running, kill it.
    '''
    (id,), err_msg = check_input(((id, int),))
    if err_msg:
        return 1, err_msg
    
    if task_manage.rm_task(id):
        return 0, f'[info]: del task {id}'
    else:
        return 1, f'[error]: can not found {id} in task queue.'


@task_manage.client('clean')
def clean(*args):
    '''
        clean [type(default=None)]    remove complete task and CMD_ERROR task.
        
        Example:
            
            gpulimit clean            clean all `CMD_ERROR` `complete` status task
            gpulimit clean kill       clean all `kill` status task
    '''
    if not args:
        rm_types = [STATUS_COMPLETE, STATUS_CMD_ERROR]
    else:
        rm_types = [Status(i) for i in args]
        
    rm_tasks = []
    for task in task_manage.tasks:
        if task.status in rm_types:
            rm_tasks.append(task)
            
    for task in rm_tasks:
        task_manage.rm_task(task.id)
        
    table = pt.PrettyTable(['id', 'status', 'run_times', 'pwd', 'cmds'])
    table.border = False
    table.align = 'l'
    for task in rm_tasks:
        table.add_row([task.id, task.status, task.run_times, task.pwd, ' '.join(task.cmds)])
        
    return 0, '[info]: rm task as follows:\n' + str(table)


@task_manage.client('kill')
def kill(id):
    '''
        kill [id]                     kill task [id]
    '''
    
    (id,), err_msg = check_input(((id, int),))
    if err_msg:
        return 1, err_msg
    
    task = task_manage.get_task(id)
    if task is None:
        return 1, f'[error]: can not found id {id} in task queue.'
    return task.kill()
    

@task_manage.client('mv') 
def mv(id, index=0, *args, **kwargs):
    '''
        mv [id] [index(default=0)]    move [id] to [index]
    '''
    (id, index), err_msg = check_input(((id, int),(index, int)), args, kwargs)
    if err_msg:
        return 1, err_msg
    
    if index > len(task_manage):
        return 2, f'[error]: index {index} is bigger than task queue length({len(task_manage)})'
    
    if task_manage.mv_task(id, index):
        return 0, f'[info]: move {id} to the first'
    else:
        return 1, f'[error]: can not found task {id}'


@task_manage.client('set') 
def set_property(name=None, value=None):
    '''
        set [name] [value]            set some property.
                                      If no input, show all param setted value.
                                      
        Can Set Params:
            
            'MINI_MEM_REMAIN':        MINI_MEM_REMAIN,
            'MAX_ERR_TIMES':          MAX_ERR_TIMES,
            'WAIT_TIME':              WAIT_TIME,
            
        Example:
            
            gpulimit set WAIT_TIME 1  set `WAIT_TIME=1`
    '''
    if name is None:
        return 0, '\n'.join([f'{k} = {v}' for k,v in task_manage.get_params()])
    
    if name in list(zip(*task_manage.get_params()))[0]:
        if value is None:
            return 0, f'{name} = {task_manage.get_param(name)}'
        
        value = int(value)
        task_manage.set_param(name, value)
        result = 0, f'[info]: seted {name} = {value}'
    else:
        result = 1, f'[error]: name `{name}` can not set.'
    logging.info(result[1])
    return result
    

@task_manage.client('start') 
def start(id=None):
    '''
        start [iddefalut=None]        Force start task(s).
        
        Information:
            
            gpulimit start            running `check_and_start`, and auto start new task.
            gpulimit start 1          Force start task [id].
    '''
    
    if id is None:
        return task_manage.scheduling.user_start_scheduling(task_manage)
    (id, ), err_msg = check_input(((id, int),), )
    if err_msg:
        return 1, err_msg
    return task_manage.scheduling.user_start_scheduling(task_manage, id)


@task_manage.client('log')          
def get_output_filename(id):
    '''
        log [id]                      show [id] output.
        
        Example:
            
            gpulimit log 1            show task(id=1) output.
            gpulimit log main         show manage background log info.
    '''
    
    if id=='main':
        return 0, task_manage.log_file
    
    (id, ), err_msg = check_input(((id, int),), )
    if err_msg:
        return 1, err_msg
    
    task = task_manage.get_task(id)
    if task is None:
        return 1, 'Error'
    return 0, os.path.abspath(task.out_path)


@task_manage.client('status')   
def status():
    '''
        status                        show System status.
        
        Example:
            
            Nothing
    '''
    gpus = System.gpus()
    memory = System.memory()
    
    task_nums = [0] * len(gpus)
    for task in task_manage.tasks:
        if task.gpu is not None:
            task_nums[int(task.gpu)] += 1
    
    result = ''
    table = pt.PrettyTable(['CPU utilization', 'memory total', 'memory free', 'memory used'])
    table.border = False
    table.add_row(['None', memory.total, memory.free, memory.used])
    result += str(table)
    result += '\n\n'
    table = pt.PrettyTable(['GPU[ID]', 'memory total', 'memory free', 'memory used', 'utilization', 'running tasks num'])
    table.border = False
    for info, use_num in zip(gpus, task_nums):
        table.add_row([info.id, info.total, info.free, info.used, 'None', use_num])
    result += str(table)
    
    return 0, result


@task_manage.client('debug')   
def debug(id):
    '''
        debug [id]                    if task [id] is `CMD_ERROR`, use this show error traceback.
        
        Example:
            
            debug 1                   show task 1 error traceback.                
    '''
    (id, ), err_msg = check_input(((id, int),), )
    if err_msg:
        return 1, err_msg
    
    task = task_manage.get_task(id)
    if task is None:
        return 1, f'[error]: can not found task[{id}]'
    
    return 0, str(task.debug_msg)


        

        
