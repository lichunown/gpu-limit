import subprocess
import os, time
import threading
from collections import namedtuple

['waiting', 'running', 'runtime_error', 'CMD_ERROR', 'complete']

GPUInfo = namedtuple('GPUInfo', ('id','memory_total', 'memory_free', 'memory_used'))

def get_gpu_info():
    gpu_info = os.popen('nvidia-smi --query-gpu=index,memory.total,memory.free,memory.used --format=csv')
    gpu_info.readline()

    gpu_data = []
    for line in gpu_info:
        index, memory_total, memory_free, memory_used = line.strip().split(', ')
        index = int(index)
        memory_total = float(memory_total.split()[0])
        memory_free = float(memory_free.split()[0])
        memory_used = float(memory_used.split()[0])
        gpu_data.append(GPUInfo(index, memory_total, memory_free, memory_used))
    return gpu_data

def get_use_gpu():
    gpu_data = get_gpu_info()
    max_free_memory_gpu = max(gpu_data, key=lambda x: x.memory_free)
    return max_free_memory_gpu


def get_gpu_info():
    gpu_data = []
    with open('./Resources', 'r') as f:
        for line in f:
            id, free = line.strip().split(':')
            id = int(id)
            free = float(free)
            gpu_data.append(GPUInfo(id, 0, free, 0))
    return gpu_data

def get_use_gpu():
    gpu_data = get_gpu_info()
    max_free_memory_gpu = max(gpu_data, key=lambda x: x.memory_free)
    return max_free_memory_gpu



class Task(object):
    def __init__(self, id, pwd, cmds, allow_gpu=1024):
        self.id = id
        self.pwd = pwd
        self.cmds = cmds
        self.error_times = 0
        self.out_file = None
        self.process = None
        self.available = True

        self.allow_gpu = allow_gpu

    def start(self, GPU_id, out_path=None):
        if self.process is not None:
            if self.status == 'runtime_error':
                self.restart(GPU_id, out_path)
        if out_path is not None:
            self.out_file = open(out_path, 'w')
        env = os.environ.copy()
        env['CUDA_VISIBLE_DEVICES'] = str(GPU_id)

        try:
            self.process = subprocess.Popen(self.cmds.split(' '), stdout=self.out_file, stderr=subprocess.STDOUT, cwd=self.pwd, env=env)
            print(f'[starting(GPU:{GPU_id})]: {self.pwd}$ {self.cmds}')
            return 0, None
        except Exception as e:
            print(e)
            self.available = False
            return 1, str(e)

    def restart(self, GPU_id, out_path=None):
        if self.status == 'runtime_error':
            self.error_times += 1
            self.process = None
        self.start(GPU_id, out_path)

    def kill(self):
        self.process.kill()

    @property
    def status(self):
        if self.available is False:
            return 'CMD_ERROR'
        if self.process is None:
            return 'waiting'
        status = self.process.poll()
        if status is None:
            return 'running'
        if status == 0:
            return 'complete'
        else:
            return 'runtime_error'


"""
return standard:

    return (code, string)

"""

class TaskQueue(object):
    def __init__(self, logdir='./tmp', CHECK_INT=10, MINI_MEM_REMAIN=1024):
        self.queue = []
        self.id_give = 0
        self.logdir = logdir

        for logname in os.listdir(self.logdir):
            path = os.path.join(logdir, logname) 
            if os.path.isfile(path):
                os.remove(path)

        self.CHECK_INT = CHECK_INT
        self.MINI_MEM_REMAIN = MINI_MEM_REMAIN

        self._t = threading.Thread(target=self.thread_check_and_restart)
        self._t.start()

    def add(self, pwd, cmds):
        task = Task(self.id_give, pwd, cmds)
        self.id_give += 1
        self.queue.append(task)
        result = f'add task(id:{task.id}) to queue: {len(self.queue)}'
        err, result_ = self.check_and_start()
        return err, '\n'.join([result, result_])

    def run_task(self, task):
        use_gpu = get_use_gpu()
        errcode, result = task.start(use_gpu.id, os.path.join(self.logdir, f'{task.id}.log'))   
        if errcode == 0:
            result = f'RUN at: {task.id}'
        return errcode, result

    def ls(self):
        self._sort_priority('show')
        result = 'num\t|\tID\tstatus\tcmds\n'
        for i, task in enumerate(self.queue):
            result += f'{i}\t|\t{task.id}\t{task.status}\t{task.cmds}\n'
        return 0, result

    def rm(self, id):
        result = ''
        try:
            id = int(id)
        except Exception as e:
            return 1, str(e)
        for i, task in enumerate(self.queue):
            if task.id == id:
                if self.queue[i].status == 'running':
                    self.queue[i].kill()
                del self.queue[i]
                result += f'[del]: {id}'
                break
        if not result:
            return 1, f'[error]: can not found {id}'
        else:
            return 0, result

    def move_to_top(self, id):
        try:
            id = int(id)
        except Exception as e:
            return 1, str(e)
        pos = None
        for i, task in enumerate(self.queue):
            if task.id == id:
                pos = i
                break
        if pos is not None:
            t = self.queue[pos]
            t = self.queue[pos]
            self.queue.insert(0, t)
            print(f'[move] {id} to the first')
            return 0, f'[move] {id} to the first'
        else:
            return 1, f'[error]: can not found {id}'

    def _sort_priority(self, type='start'):
        ['waiting', 'running', 'runtime_error', 'CMD_ERROR', 'complete']
        start_sort_type = {
            'waiting': 0,
            'runtime_error': 1,
            'running': 2,
            'complete': 2,
            'CMD_ERROR': 2,
        }
        show_sort_type = {
            'running': 1,
            'waiting': 2,
            'runtime_error': 3,
            'complete': 4,
            'CMD_ERROR': 5,
        }
        if type == 'start':
            sort_type = start_sort_type
        elif type == 'show':
            sort_type = show_sort_type
        else:
            raise KeyError
        self.queue = sorted(self.queue, key=lambda x: x.id)
        self.queue = sorted(self.queue, key=lambda x: sort_type[x.status])

    def check_and_start(self): 
        gpu_info = get_gpu_info()
        result = ''
        if any(map(lambda x: x.memory_free > self.MINI_MEM_REMAIN, gpu_info)):
            self._sort_priority('start')
            use_gpu = get_use_gpu()
            for task in self.queue:
                if task.status == 'waiting':
                    task.allow_gpu = use_gpu.memory_free
                    self.run_task(task)
                    result += f'RUN: [{task.id}]  {task.pwd}#{task.cmds}'
                    break
                if task.status == 'runtime_error':
                    if task.allow_gpu < use_gpu.memory_free:
                        task.allow_gpu = use_gpu.memory_free
                        self.run_task(task)
                        result += f'RUN: [{task.id}]  {task.pwd}#{task.cmds}'
                        break
                else:
                    break
        if not result:
            result = 'running queue is full. please use `-ls` check status.'
        return 0, result

    def clean(self, *args):
        rm_ids = []
        rm_cmds = []
        rm_pwds = []
        for task in filter(lambda x:x.status in ['CMD_ERROR', 'complete'], self.queue):
            rm_ids.append(task.id)
            rm_cmds.append(task.cmds)
            rm_pwds.append(task.pwd)

        self.queue = list(filter(lambda x:x, [None if task.status in ['CMD_ERROR', 'complete'] else task for task in self.queue]))
        return 0, '\n'.join([f'[rm ID({id_})]: {pwd}# {cmds}' for id_, pwd, cmds in zip(rm_ids, rm_pwds, rm_cmds)])

    def thread_check_and_restart(self):
        while True:
            time.sleep(self.CHECK_INT)
            gpu_info = get_gpu_info()
            while any(map(lambda x: x.memory_free > self.MINI_MEM_REMAIN, gpu_info)):
                self.check_and_start()
                time.sleep(1)
            
        
    def get_output_filename(self, id):
        try:
            id = int(id)
        except Exception as e:
            return 1, str(e)
        return 0, os.path.abspath(os.path.join(self.logdir, f'{id}.log'))

