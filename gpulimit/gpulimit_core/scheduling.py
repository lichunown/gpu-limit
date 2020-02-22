import abc
import logging

from .system_info import system_info
from .tasks import TaskStatus, Sort

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
        if not info.gpu:
            return 0
        return sorted(info.gpu, key = lambda x: x.memory_free, reverse=True)[0].id
        
    @staticmethod
    def sort_for_timer_call(tasks):
        tasks = sorted(tasks, key=lambda x: x.run_times)
        tasks = sorted(tasks, key=lambda x: Sort.status_sort_type[x.status.status])
        return tasks
    
    def callback_process_end(self, task_manage, *args, **kwargs):
        if all([task.status.status != 'running' for task in task_manage.tasks]):
            return self.timer_call(task_manage)
    
    def callback_add_process(self, task_manage, *args, **kwargs):
        if all([task.status.status != 'running' for task in task_manage.tasks]):
            if self.timer_call(task_manage):
                return 0, 'start task.'
        return 0, ''
    
    def timer_call(self, task_manage):
        info = system_info.refresh()
        tasks = task_manage.tasks
        tasks = self.sort_for_timer_call(tasks)
        
        for task in tasks:
            if task.run_times > task_manage.setter_param['MAX_ERR_TIMES']:
                continue
            if task.status.status in TaskStatus.auto_start_list:
                gpu_id = self._use_gpu_id(info)
                task.start(self._use_gpu_id(info))
                logging.info(f'start task {task.id} in GPU({gpu_id}).')
                return True
    
        return False
    
    def user_start_scheduling(self, task_manage, task_id=None):
        if task_id is None:
            return self.callback_add_process(task_manage)
        
        task = task_manage.get_task(task_id)
        info = system_info.refresh()
        gpu_id = self._use_gpu_id(info)
        
        logging.info(f'start task {task.id} in GPU({gpu_id}).')
        return task.start(gpu_id)