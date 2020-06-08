import os
import sys
import time 
import logging
import psutil

from collections import deque, namedtuple

from gpulimit.utils.pynvml import nvmlInit, nvmlDeviceGetCount, \
                         nvmlDeviceGetHandleByIndex, nvmlDeviceGetMemoryInfo
                 
                    
SystemInfo = namedtuple('SystemInfo', ('time', 'CPU_utilization','memory', 'gpu', 'task'))
MemoryInfo = namedtuple('MemoryInfo', ('total','free', 'used'))
GPUInfo = namedtuple('GPUInfo', ('id','total', 'free', 'used', 'utilization'))
# ProcessInfo = namedtuple('ProcessInfo', ('pid','memory_used', 'gpu_memory'))

nvmlInit()


class System(object):
    
    @staticmethod
    def gpu_nums():
        return nvmlDeviceGetCount()
    
    @staticmethod
    def gpu(id):
        h = nvmlDeviceGetHandleByIndex(id)
        memorys = nvmlDeviceGetMemoryInfo(h)
        return GPUInfo(id, memorys.total/1024/1024/1024, 
                       memorys.free/1024/1024/1024, 
                       memorys.used/1024/1024/1024, None)
    
    @staticmethod
    def gpus():
        return [System.gpu(i) for i in range(System.gpu_nums())]
    
    @staticmethod
    def cpu_nums():
        return psutil.cpu_count()
    
    @staticmethod
    def cpu_usage(id):
        return psutil.cpu_percent(id) / 100
    
    @staticmethod
    def cpu_mean():
        sum([System.cpu_usage(i) for i in range(System.cpu_nums())]) / System.cpu_nums()
       
    @staticmethod
    def memory():
        memory = psutil.virtual_memory()
        return MemoryInfo(memory.total/1024/1024/1024, 
                          memory.available/1024/1024/1024, 
                          memory.used/1024/1024/1024)
    
    @staticmethod
    def best_select_gpu_id():
        return max([(i, gpu.free) for i, gpu in enumerate(System.gpus())], 
                                                      key=lambda x: x[1])[0]
    

    

