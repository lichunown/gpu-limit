import subprocess
import os, time, traceback
import threading
import logging

from collections import namedtuple
from queue import Queue

try:
    import prettytable as pt
except ModuleNotFoundError:
    from utils import prettytable as pt

                
GPUInfo = namedtuple('GPUInfo', ('id','memory_total', 'memory_free', 'memory_used'))

def _get_gpu_info():
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


def _get_use_gpu(allow_free=None):
    gpu_data = get_gpu_info()
    if allow_free is None:
        return max(gpu_data, key=lambda x: x.memory_free)
    else:
        return list(filter(lambda x: x.memory_free > allow_free, gpu_data))


def get_gpu_info_test():
    gpu_data = []
    with open('./gpulimit/test/Resources', 'r') as f:
        for line in f:
            id, free = line.strip().split(':')
            id = int(id)
            free = float(free)
            gpu_data.append(GPUInfo(id, 0, free, 0))
    return gpu_data


def get_use_gpu_test(allow_free=None):
    gpu_data = get_gpu_info()
    if allow_free is None:
        return max(gpu_data, key=lambda x: x.memory_free)
    else:
        return list(filter(lambda x: x.memory_free > allow_free, gpu_data))


if not os.environ.get('GPULIMIT_DEBUG'):
    try:
        result = _get_gpu_info()
    except Exception:
        result = None
    if not result:
        print('[Warning]: can not use `nvidia-smi`, please check cuda environment.')
        print('[info]: set GPULIMIT_DEBUG=1.')
        os.environ['GPULIMIT_DEBUG'] = '1'

if os.environ.get('GPULIMIT_DEBUG'):
    logging.warning('here use debug environment. NO GPU USE!!!')
    get_gpu_info = get_gpu_info_test
    get_use_gpu = get_use_gpu_test
else:
    get_gpu_info = _get_gpu_info
    get_use_gpu = _get_use_gpu



        

class TaskStatus(object):
    status2id = dict(zip(['CMD_ERROR', 'complete', 'waiting', 'running', 'runtime_error', 'killed'], range(-1, 5)))
    id2status = dict(zip(status2id.values(), status2id.keys()))
    
    can_start_list = ['waiting', 'runtime_error', 'killed']
    auto_start_list = ['waiting', 'runtime_error']
    
    start_sort_type = {
        'waiting': 0,
        'runtime_error': 1,
        'killed': 2,
        'running': 3,
        'complete': 3,
        'CMD_ERROR': 3,
    }
    show_sort_type = {
        'running': 1,
        'waiting': 2,
        'killed': 3,
        'runtime_error': 3,
        'complete': 4,
        'CMD_ERROR': 5,
    }
    
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


class Task(object):
    def __init__(self, task_queue, id, pwd, cmds, out_path=None):
        self.task_queue = task_queue
        self.id = id
        self.pwd = pwd
        self.cmds = cmds
        self.out_path = out_path
        
        self.gpu = None
        self.is_in_queue = False
        
        self.run_times = 0
        self.out_file = None
        self.pkg_process = None
        self.process = None
        self.available = True

        self.killed = False
        self.debug_msg = None
        
    def _run_task(self, GPU_id):
        if self.out_path is not None:
            self.out_file = open(self.out_path, 'w')
        self.gpu = GPU_id
        env = os.environ.copy()
        env['CUDA_VISIBLE_DEVICES'] = str(GPU_id)
        try:
            self.process = subprocess.Popen(self.cmds, stdout=self.out_file, shell=True, stderr=subprocess.STDOUT, cwd=self.pwd, env=env)
            logging.info(f'[starting({self.id}: GPU:{GPU_id})]: {self.pwd}$ {self.cmds}')
        except Exception as e:
            self.available = False
            logging.info(f'[CMD_ERROR({self.id}: GPU:{GPU_id})]: {self.pwd}$ {self.cmds} \nerror:\n{e}')
            msg = traceback.format_exc()
            logging.info(msg)
            self.debug_msg = 'cmds: ' + str(self.cmds) + "\n" + msg
            self.task_queue.check_and_start()
            return
        self.process.wait()
        self.gpu = None
        self.is_in_queue = False
        logging.info(f'[finish({self.id}: GPU:{GPU_id})]: {self.pwd}$ {self.cmds}')
        
        self.task_queue.check_and_start()

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
            self.is_in_queue = False
            return 0, f'[info]: kill task {self.id} succeed.'
        else:
            return 1, f'[warning]: can not kill task {self.id} which have status `{self.status.status}`'

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
            return TaskStatus('running', self.run_times)
        
        if status == 0:
            return TaskStatus('complete', self.run_times)
        else:
            return TaskStatus('runtime_error', self.run_times, err_code=status)


#def client(client_cmd):
#    def decorator(func):
#        def wrapper(self, *args, **kwargs):
#            self.func_map[client_cmd] = func
#            return func(*args, **kwargs)
#        return wrapper
#    return decorator


class TaskQueue(object):
    def __init__(self, logdir='./tmp', MINI_MEM_REMAIN=1024, MAX_ERR_TIMES=5, WAIT_TIME=10):
        self.queue = []
        self.id_give = 0
        self.logdir = logdir
        self.log_file = os.path.join(self.logdir, 'main.log')
        
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        else:
            # del logfiles in log dir
            for logname in os.listdir(self.logdir):
                path = os.path.join(logdir, logname) 
                if os.path.isfile(path):
                    os.remove(path)

        if os.environ.get('GPULIMIT_DEBUG'):
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
            logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(message)s')
        else:
            logging.basicConfig(filename=self.log_file, level=logging.INFO, format='%(asctime)s - %(message)s')
            logging.basicConfig(filename=self.log_file, level=logging.WARNING, format='%(asctime)s - %(message)s')

#        self.func_map = {}
        
        self.MINI_MEM_REMAIN = MINI_MEM_REMAIN
        self.MAX_ERR_TIMES = MAX_ERR_TIMES
        self.WAIT_TIME = WAIT_TIME
        
        self.start_thread = threading.Thread(target=self._thread_start_task)
        self.need_start_tasks = Queue()
        self.lock = threading.RLock()
        self.start_thread.start()
        
    
    def _thread_start_task(self):
        while True:
            if not self.need_start_tasks.empty():
                task = self.need_start_tasks.get()
                if task.status.status in TaskStatus.can_start_list:
                    self.run_task(task)
                    time.sleep(self.WAIT_TIME)
            else:
                time.sleep(1)
    
    @staticmethod
    def _check_input(input_types, extra_args=(), extra_kwargs={}):
        '''
        Example:
            
            input_types = (('1', int), ('start', str))
        '''
        err_msg = ''
        result_input = []
        for value, dtype in input_types:
            try:
                result_input.append(dtype(value))
            except Exception as e:
                result_input.append(None)
                err_msg += f'[error]: input {value} is not type `{dtype.__name__}`.\n'
        for v in extra_args:
            err_msg += f'[error]: can not identify param `{v}`.\n'
        for k, v in extra_kwargs.items():
            err_msg += f'[error]: can not identify param `{k}={v}`.\n'
            
        return result_input, err_msg
    
    def add(self, pwd, cmds, logpath=None):
        if logpath is None:
            logpath = os.path.join(self.logdir, f'{self.id_give}.log')
        task = Task(self, self.id_give, pwd, cmds, logpath)
        self.id_give += 1
        self.queue.append(task)
        result = f'add task(id:{task.id}) to queue(len: {len(self.queue)})'
        logging.info(f'add task(id:{task.id}): {pwd}$ {cmds})')
        err, result_ = self.check_and_start()
        return err, '\n'.join([result, result_])

    def run_task(self, task):
        use_gpu = get_use_gpu()
        errcode, result = task.start(use_gpu.id)   
        return errcode, result

#    @client('ls')
    def ls(self, *, all=False, sort='show'):
        '''
        ls                            ls GPU task queue status
        '''
        (all, sort), err_msg = self._check_input(((all, bool), (sort,str)))
        if err_msg: return 1, err_msg
        
        err_code, err_msg = self._sort_priority(sort)
        if err_msg: return 1, err_msg
        
        result = f'TaskQueue MINI_MEM_REMAIN={self.MINI_MEM_REMAIN}, MAX_ERR_TIMES={self.MAX_ERR_TIMES}\n'
        table = pt.PrettyTable(['[ID]', 'num', 'status', 'run_times', 'pwd', 'cmds'])
        table.border = False
#        result += '[ID]\tnum\t|\tstatus\trun_times\tcmds\n'
        for i, task in enumerate(self.queue):
            status = str(task.status) + f'(GPU:{task.gpu})' if task.gpu is not None else str(task.status)
            if not all:
                table.add_row([task.id, i, status, task.run_times, task.pwd+'#', " ".join(task.cmds)[:80]])
            else:
                table.add_row([task.id, i, status, task.run_times, task.pwd+'#', " ".join(task.cmds)])
#            result += f'{task.id}\t{i}\t|\t{str(task.status)}\t{task.run_times}\t{task.pwd}# {"".join(task.cmds)}\n'
        return 0, result + str(table)

    def rm(self, id):
        '''
        rm [id]                       remove task [id] from manage, if task is running, kill it.
        '''
        (id,), err_msg = self._check_input(((id, int),))
        if err_msg:
            return 1, err_msg
        
        result = ''
        self.lock.acquire()
        for i, task in enumerate(self.queue):
            if task.id == id:
                if str(self.queue[i].status) == 'running':
                    self.queue[i].kill()
                del self.queue[i]
                result += f'[info]: del task {id}'
                break
        self.lock.release()
        if not result:
            return 1, f'[error]: can not found {id} in task queue.'
        else:
            return 0, result

    def kill(self, id):
        '''
        kill [id]                     kill task [id]
        '''
        
        (id,), err_msg = self._check_input(((id, int),))
        if err_msg:
            return 1, err_msg
        
        for i, task in enumerate(self.queue):
            if task.id == id:
                return task.kill()
        return 1, f'[error]: can not found id {id} in task queue.'
        
    def move_to_top(self, id, index=0, *args, **kwargs):
        '''
        move [id] [index(default=0)]  move [id] to [index]
        '''
        (id, index), err_msg = self._check_input(((id, int),(index, int)), args, kwargs)
        if err_msg:
            return 1, err_msg
        
        if index > len(self.queue):
            return 2, f'[error]: index {index} is bigger than task queue length({len(self.queue)})'
        
        pos = None
        for i, task in enumerate(self.queue):
            if task.id == id:
                pos = i
                break
        if pos is not None:
            self.lock.acquire()
            t = self.queue[pos]
            del self.queue[pos]
            self.queue.insert(index, t)
            self.lock.release()
            return 0, f'[info]: move {id} to the first'
        else:
            return 1, f'[error]: can not found task {id}'


    def _sort_priority(self, type='start'):
        if type == 'start':
            sort_type = TaskStatus.start_sort_type
        elif type == 'show':
            sort_type = TaskStatus.show_sort_type
        elif type == 'id':
            sort_type = dict(zip(TaskStatus.status2id.keys(), [1] * len(TaskStatus.status2id)))
        else:
            return 1, f'[Error]: can not found sort type `{type}`, which can use `show` `id` `start`'
            
        self.lock.acquire()
        self.queue = sorted(self.queue, key=lambda x: x.id)
        self.queue = sorted(self.queue, key=lambda x: sort_type[x.status.status])
        self.lock.release()
        return 0, ''

    def check_and_start(self): 
        result = ''
        can_use_gpu = get_use_gpu(self.MINI_MEM_REMAIN)
        if can_use_gpu:
            self._sort_priority('start')
            remain_tasks = list(filter(lambda task: task.status.status in TaskStatus.auto_start_list and not task.is_in_queue, self.queue))
            if remain_tasks:
                self.need_start_tasks.put(remain_tasks[0])
                remain_tasks[0].is_in_queue = True
            else:
                result = f'all task is to be run or completed.'
        else:
            result = 'GPU memory is full. task is waitting for others.'
            
        logging.info(result)
        return 0, result

    def clean(self, *args):
        '''
        clean [type(default=None)]    remove complete task and CMD_ERROR task.
        
        Example:
            
            gpulimit clean            clean all `CMD_ERROR` `complete` status task
            gpulimit clean kill       clean all `kill` status task
        '''
        if not args:
            rm_types = ['CMD_ERROR', 'complete']
        else:
            rm_types = list(args)
            
        rm_ids = []
        rm_cmds = []
        rm_pwds = []
        for task in filter(lambda x:x.status.status in rm_types, self.queue):
            rm_ids.append(task.id)
            rm_cmds.append(task.cmds)
            rm_pwds.append(task.pwd)
        self.lock.acquire()
        self.queue = list(filter(lambda x:x, [None if task.status.status in rm_types else task for task in self.queue]))
        self.lock.release()
        return 0, '\n'.join([f'[info]: rm ID({id_})  {pwd}# {cmds}' for id_, pwd, cmds in zip(rm_ids, rm_pwds, rm_cmds)])

    def set_property(self, name, value):
        '''
        set [name] [value]            set some property.
        
        Example:
            
            gpulimit set WAIT_TIME 1  set `WAIT_TIME=1`
        '''
        
        name2type = {
            'MINI_MEM_REMAIN': int, 
            'MAX_ERR_TIMES': int,
            'WAIT_TIME': int,
        }
        if name in name2type:
            value = name2type[name](value)
            self.__dict__[name] = value
            result = 0, f'[info]: set {name}={value}'
        else:
            result = 1, f'[error]: name `{name}` can not set.'
        logging.info(result[1])
        return result
    
    def start(self, id=None):
        '''
        start [iddefalut=None]        Force start task(s).
        
        Information:
            
            gpulimit start            running `check_and_start`, and auto start new task.
            gpulimit start 1          Force start task [id].
        '''
        
        if id is None:
            return self.check_and_start()
        (id, ), err_msg = self._check_input(((id, int),), )
        if err_msg:
            return 1, err_msg
        
        for task in self.queue:
            if task.id == id:
                return self.run_task(task)

        return 1, f'[error]: can not found task[{id}]'
                
    def get_output_filename(self, id):
        '''
        log [id]                      show [id] output.
        
        Example:
            
            gpulimit log 1            show task(id=1) output.
            gpulimit log main         show manage background log info.
        '''
        
        if id=='main':
            return 0, self.log_file
        
        (id, ), err_msg = self._check_input(((id, int),), )
        if err_msg:
            return 1, err_msg
        
        path = ''
        for i, task in enumerate(self.queue):
            if id == task.id:
                path = os.path.abspath(task.out_path)
        if path:
            return 0, path
        else:
            return 1, 'Error'
        
    def status(self):
        '''
        status                        show GPU status.
        
        Example:
            
            Nothing
        '''
        gpu_data = get_gpu_info()
        task_nums = [0] * len(gpu_data)
        for task in self.queue:
            if task.gpu:
                task_nums[task.gpu] += 1
                
        table = pt.PrettyTable(['GPU[ID]', 'memory total', 'memory free', 'memory used', 'running tasks num'])
        table.border = False
        for info, use_num in zip(gpu_data, task_nums):
            table.add_row([info.id, info.memory_total, info.memory_free, info.memory_used, use_num])
            
        return 0, str(table)
    
    def debug(self, id):
        '''
        debug [id]                    if task [id] is `CMD_ERROR`, use this show error traceback.
        
        Example:
            
            debug 1                   show task 1 error traceback.                
        '''
        (id, ), err_msg = self._check_input(((id, int),), )
        if err_msg:
            return 1, err_msg
        
        for task in self.queue:
            if task.id == id:
                return 0, str(task.debug_msg)
        return 1, f'[error]: can not found task[{id}]'