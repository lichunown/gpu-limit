import os, sys, time, logging
from collections import deque, namedtuple

SystemInfo = namedtuple('SystemInfo', ('time', 'CPU_utilization','memory', 'gpu', 'task'))
MemoryInfo = namedtuple('MemoryInfo', ('total','free', 'used'))
GPUInfo = namedtuple('GPUInfo', ('id','memory_total', 'memory_free', 'memory_used', 'utilization'))
ProcessInfo = namedtuple('ProcessInfo', ('pid','memory_used', 'gpu_memory'))

class System(object):
    def __init__(self, debug=False):
        self.data = deque(maxlen=1)
        self.debug = debug
    
    @property
    def debug(self):
        return self._debug
    @debug.setter
    def debug(self, value):
        self._debug = bool(value)
        if self._debug:
            self.get_gpu_info = self._get_gpu_info_test
        else:
            self.get_gpu_info = self._get_gpu_info
        try:
            r = self.get_gpu_info()
            if not r:
                self.get_gpu_info = lambda: []
                logging.warn('Can not use `nvidia-smi`, please check you `PATH` environment.')
        except Exception:
            self.get_gpu_info = lambda: []
            logging.warn('Can not use `nvidia-smi`, please check you `PATH` environment.')
            
    def refresh(self):
        self.data.append(SystemInfo(time.time(), self.get_cpu_utilization(), 
                                    self.get_memory_info(), self.get_gpu_info(), 
                                    self.get_pid_info()))
        return self
    
    def __call__(self):
        self.refresh()
        return self.data[-1]
    
    @property
    def gpu(self):
        if len(self.data) == 0:
            raise RuntimeError('call `refresh` first.')
        return self.data[-1].gpu
    
    @property
    def pid(self):
        if len(self.data) == 0:
            raise RuntimeError('call `refresh` first.')
        return self.data[-1].task
    
    @staticmethod
    def _get_gpu_info():
        gpu_info = os.popen('nvidia-smi --query-gpu=index,memory.total,memory.free,memory.used,utilization.gpu --format=csv')
        gpu_info.readline()
    
        gpu_data = []
        for line in gpu_info:
            index, memory_total, memory_free, memory_used, utilization = line.strip().split(', ')
            index = int(index)
            memory_total = float(memory_total.split()[0])
            memory_free = float(memory_free.split()[0])
            memory_used = float(memory_used.split()[0])
            utilization = float(utilization.split()[0])
            gpu_data.append(GPUInfo(index, memory_total, memory_free, memory_used, utilization))
        return gpu_data
    
    @staticmethod
    def _get_gpu_info_test():
        gpu_data = []
        with open('./gpulimit/test/Resources', 'r') as f:
            for line in f:
                id, free = line.strip().split(':')
                id = int(id)
                free = float(free)
                gpu_data.append(GPUInfo(id, 0, free, 0, 0))
        return gpu_data
    
    @staticmethod
    def get_memory_info():
        if sys.platform == 'linux': 
            total, free = os.popen('cat /proc/meminfo').readlines()[:2]
            total = float(total.strip().split(':')[1].split()[0])
            free = float(free.strip().split(':')[1].split()[0])
        else:
            free = float(os.popen('wmic OS get FreePhysicalMemory').readlines()[2].strip())
            total = float(os.popen('wmic ComputerSystem get TotalPhysicalMemory').readlines()[2].strip())
        used = total - free
        return MemoryInfo(total, free, used)
    
    @staticmethod
    def get_pid_info():
#        data = {}
#        if sys.platform == 'linux': 
#            pass
#        else:
#            for line in os.popen('TASKLIST /FO CSV').readlines()[1:]:
#                print(line)
#                name, pid, _, _, memory_used = line.strip().split(',')
#                pid = int(pid.strip('"'))
#                memory_used = memory_used.strip('"').split()[0]
#                memory_used = ''.join(memory_used.split(','))
#                try:
#                    memory_used = float(memory_used)
#                except Exception:
#                    memory_used = 0
#                data[pid] = ProcessInfo(pid, memory_used, None)
        return {}
            
    @staticmethod
    def get_cpu_utilization():
        return None
    

system_info = System()
# if system_info.get_gpu_info() is None:
#     system_info.debug = True
