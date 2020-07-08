import abc
import logging

from .system_info import System
from .tasks import Status, STATUS_WAITING, STATUS_RUNTIME_ERROR


class Scheduling(metaclass=abc.ABCMeta):
    def __init__(self):
        self.param = {}
        
    @abc.abstractmethod
    def callback_process_end(self, task_manage, *args, **kwargs):
        pass
    
    @abc.abstractmethod
    def callback_add_process(self, task_manage, *args, **kwargs):
        pass
    
    @abc.abstractmethod
    def timer_call(self, task_manage, *args, **kwargs):
        pass
    
    @abc.abstractmethod
    def user_start_scheduling(self, task_manage, task_id=None):
        pass
    
    
class BaseScheduling(Scheduling):
    def __init__(self):
        self.param = {
            'MAX_ERR_TIMES': 1,
            'MAX_RUNNING_TASKS': -1,
            'SAFETY_KEEP_MEMORY': 0.2,
            'SAFETY_KEEP_GPU_MEMORY': 0.6,
        }
        
    @staticmethod
    def sort_for_timer_call(tasks):
        tasks = sorted(tasks, key=lambda x: x.priority)
        tasks = sorted(tasks, key=lambda x: x.run_times)
        tasks = sorted(tasks, key=lambda x: x.status.sort_run)
        return tasks
    
    def callback_process_end(self, task_manage, *args, **kwargs):
        pass
    
    def callback_add_process(self, task_manage, *args, **kwargs):
        return 0, ''
    
    def timer_call(self, task_manage):
        gpu_id = System.best_select_gpu_id()
        gpu = System.gpu(gpu_id)
        memory = System.memory()
        # print('timer_call: ', end='')
        if gpu.free < self.param['SAFETY_KEEP_GPU_MEMORY'] * gpu.total:
            # print('gpu.free return')
            return False
        
        if memory.free < self.param['SAFETY_KEEP_MEMORY'] * memory.total:
            # print('memory.free return')
            return False
        
        tasks = task_manage.tasks

        if 0 < self.param['MAX_RUNNING_TASKS'] <= sum([task.gpu==gpu_id for task in tasks]):
            return False

        tasks = self.sort_for_timer_call(tasks)
        
        for task in tasks:
            if task.run_times >= self.param['MAX_ERR_TIMES']:
                continue
            
            if task.status in [STATUS_WAITING, STATUS_RUNTIME_ERROR]:
                task.start(gpu_id)
                logging.info(f'start task {task.id} in GPU({gpu_id}).')
                return True
    
        return False
    
    def user_start_scheduling(self, task_manage, task_id=None):
        if task_id is None:
            return self.callback_add_process(task_manage)
        
        task = task_manage.get_task(task_id)
        gpu_id = System.best_select_gpu_id()
        
        logging.info(f'start task {task.id} in GPU({gpu_id}).')
        return task.start(gpu_id)