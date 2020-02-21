import abc
import logging

from .system_info import system_info
from .tasks import TaskStatus

class Scheduling(metaclass=abc.ABCMeta):
    
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
        pass
    
    @staticmethod
    def _use_gpu_id(info):
        return sorted(info.gpu, key = lambda x: x.memory_free, reverse=True)[0].id
        
    def callback_process_end(self, task_manage, *args, **kwargs):
        pass
    
    def callback_add_process(self, task_manage, *args, **kwargs):
        return 0, ''
    
    def timer_call(self, task_manage, *args, **kwargs):
        info = system_info.refresh()
        if not info.gpu:
            for task in task_manage.tasks:
                if task.run_times > task_manage.setter_param['MAX_ERR_TIMES']:
                    continue
                if task.status.status in TaskStatus.auto_start_list:
                    task.start(0)
                    logging.info(f'start task {task.id}.')
                    return True
            return False
        
        if info.gpu[self._use_gpu_id(info)].memory_free > task_manage.setter_param['MINI_MEM_REMAIN']:
            for task in task_manage.tasks:
                if task.run_times > task_manage.setter_param['MAX_ERR_TIMES']:
                    continue
                if task.status.status in TaskStatus.auto_start_list:
                    task.start(self._use_gpu_id(info))
                    logging.info(f'start task {task.id}.')
                    return True
        return False
    
    def user_start_scheduling(self, task_manage, task_id=None):
        if task_id is None:
            return self.callback_add_process(task_manage)
        
        task = task_manage.get_task(task_id)
        info = system_info.refresh()
        
        logging.info(f'start task {task.id}.')
        return task.start(self._use_gpu_id(info))