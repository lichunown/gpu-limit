from utils.func2cui import ParseFunction, ParseModule
from gpulimit_core.run_task_core import TaskManage


MAIN_HELP = '''
GPU Task Manage:
    usage:
        
        client.py -h                  show help
        gpulimit add [cmds]           add task [cmds] to gpulimit queue.
        

    other commands:\n\n
'''


parse = ParseModule()

@parse.sub_module('ls')
def ls(*, all:bool=False, sort='show'):
    print(f'call ls {all} {sort}')
    
    
def add(args):
    print(f'call add `{args}`')
    
parse.add_sub_parse('add', add)

# @parse.sub_module('ls')
# def ls(*, all:bool=False, sort:str='show'):
#     '''
#         ls                            ls GPU task queue status
        
#         Options:
            
#             --all                     default ls only show <80 commands, 
#                                       use `all` to show all commands. 
#             --sort                    show by different sort type. 
#                                       can use: ['id', 'priority', 'show', 'run']
#     '''
    
#     (all, sort), err_msg = check_input(((all, bool), (sort, str)))
#     if err_msg: return 1, err_msg
    
# #    print(sort)
#     tasks = Sort.sort(task_manage.tasks, sort)
#     if not isinstance(tasks, list): return 1, tasks
    
#     table = pt.PrettyTable(['[ID]', 'num', 'status', 'run_times', 'pwd', 'cmds'])
#     table.border = False
#     for i, task in enumerate(tasks):
#         status = str(task.status) + f'(GPU:{task.gpu})' if task.gpu is not None else str(task.status)
#         if not all:
#             table.add_row([task.id, i, status, task.run_times, task.pwd+'#', " ".join(task.cmds)[:80]])
#         else:
#             table.add_row([task.id, i, status, task.run_times, task.pwd+'#', " ".join(task.cmds)])
# #    print(str(table))
#     return 0, str(table)


# @parse.sub_module('show')
# def show(id):
#     '''
#         show [id]                     show task [id] details.

#     '''
    
#     (id,), err_msg = check_input(((id, int),))
#     if err_msg:
#         return 1, err_msg
    
#     task = task_manage.get_task(id)
#     if task is None:
#         return 1, f'[error]: can not found id {id} in task queue.'
    
#     table = pt.PrettyTable(['name', 'value'])
#     table.border = False
#     table.align = 'l'
#     table.add_row(['task id:', task.id])
#     table.add_row(['task pid:', task.pid])
#     table.add_row(['priority:', task.priority])
#     table.add_row(['use gpu:', task.gpu])
#     table.add_row(['error times:', task.run_times])
#     table.add_row(['status:', task.status.status])
#     table.add_row(['out file:', task.out_path])
#     table.add_row(['pwd:', task.pwd])
#     table.add_row(['cmds:', " ".join(task.cmds)])
#     return 0, str(table)

# @task_manage.client('rm')
# def rm(id):
#     '''
#         rm [id]                       remove task [id] from manage, if task is running, kill it.
#     '''
#     (id,), err_msg = check_input(((id, int),))
#     if err_msg:
#         return 1, err_msg
    
#     if task_manage.rm_task(id):
#         return 0, f'[info]: del task {id}'
#     else:
#         return 1, f'[error]: can not found {id} in task queue.'


# @task_manage.client('clean')
# def clean(*args):
#     '''
#         clean [type(default=None)]    remove complete task and CMD_ERROR task.
        
#         Example:
            
#             gpulimit clean            clean all `CMD_ERROR` `complete` status task
#             gpulimit clean kill       clean all `kill` status task
#     '''
#     if not args:
#         rm_types = ['CMD_ERROR', 'complete']
#     else:
#         rm_types = list(args)
        
#     rm_tasks = []
#     for task in task_manage.tasks:
#         if task.status.status in rm_types:
#             rm_tasks.append(task)
            
#     for task in rm_tasks:
#         task_manage.rm_task(task.id)
        
#     table = pt.PrettyTable(['id', 'status', 'run_times', 'pwd', 'cmds'])
#     table.border = False
#     table.align = 'l'
#     for task in rm_tasks:
#         table.add_row([task.id, task.status.status, task.run_times, task.pwd, task.cmds])
        
#     return 0, '[info]: rm task as follows:\n' + str(table)


# @task_manage.client('kill')
# def kill(id):
#     '''
#         kill [id]                     kill task [id]
#     '''
    
#     (id,), err_msg = check_input(((id, int),))
#     if err_msg:
#         return 1, err_msg
    
#     task = task_manage.get_task(id)
#     if task is None:
#         return 1, f'[error]: can not found id {id} in task queue.'
#     return task.kill()
    

# @task_manage.client('mv') 
# def mv(id, index=0, *args, **kwargs):
#     '''
#         move [id] [index(default=0)]  move [id] to [index]
#     '''
#     (id, index), err_msg = check_input(((id, int),(index, int)), args, kwargs)
#     if err_msg:
#         return 1, err_msg
    
#     if index > len(task_manage):
#         return 2, f'[error]: index {index} is bigger than task queue length({len(task_manage)})'
    
#     if task_manage.mv_task(id, index):
#         return 0, f'[info]: move {id} to the first'
#     else:
#         return 1, f'[error]: can not found task {id}'


# @task_manage.client('set') 
# def set_property(name=None, value=None):
#     '''
#         set [name] [value]            set some property.
#                                       If no input, show all param setted value.
                                      
#         Can Set Params:
            
#             'MINI_MEM_REMAIN':        MINI_MEM_REMAIN,
#             'MAX_ERR_TIMES':          MAX_ERR_TIMES,
#             'WAIT_TIME':              WAIT_TIME,
            
#         Example:
            
#             gpulimit set WAIT_TIME 1  set `WAIT_TIME=1`
#     '''
#     if name is None:
#         return 0, '\n'.join([f'{k} = {v}' for k,v in task_manage.setter_param.items()])
    
#     if name in task_manage.setter_param:
#         if value is None:
#             return 0, f'{name} = {task_manage.setter_param[name]}'
        
#         value = int(value)
#         task_manage.setter_param[name] = value
#         if name in self.scheduling.param:
#             self.scheduling.param[name] = value
#         result = 0, f'[info]: seted {name} = {value}'
#     else:
#         result = 1, f'[error]: name `{name}` can not set.'
#     logging.info(result[1])
#     return result
    

# @task_manage.client('start') 
# def start(id=None):
#     '''
#         start [iddefalut=None]        Force start task(s).
        
#         Information:
            
#             gpulimit start            running `check_and_start`, and auto start new task.
#             gpulimit start 1          Force start task [id].
#     '''
    
#     if id is None:
#         return task_manage.scheduling.user_start_scheduling(task_manage)
#     (id, ), err_msg = check_input(((id, int),), )
#     if err_msg:
#         return 1, err_msg
#     return task_manage.scheduling.user_start_scheduling(task_manage, id)


# @task_manage.client('log')          
# def get_output_filename(id):
#     '''
#         log [id]                      show [id] output.
        
#         Example:
            
#             gpulimit log 1            show task(id=1) output.
#             gpulimit log main         show manage background log info.
#     '''
    
#     if id=='main':
#         return 0, task_manage.log_file
    
#     (id, ), err_msg = check_input(((id, int),), )
#     if err_msg:
#         return 1, err_msg
    
#     task = task_manage.get_task(id)
#     if task is None:
#         return 1, 'Error'
#     return 0, os.path.abspath(task.out_path)


# @task_manage.client('status')   
# def status():
#     '''
#         status                        show System status.
        
#         Example:
            
#             Nothing
#     '''
#     all_info = system_info()
#     gpu_data = all_info.gpu
    
    
#     task_nums = [0] * len(gpu_data)
#     for task in task_manage.tasks:
#         if task.gpu:
#             task_nums[task.gpu] += 1
#     result = ''
#     table = pt.PrettyTable(['CPU utilization', 'memory total', 'memory free', 'memory used'])
#     table.border = False
#     table.add_row([all_info.CPU_utilization, all_info.memory.total, all_info.memory.free, all_info.memory.used])
#     result += str(table)
#     result += '\n\n'
#     table = pt.PrettyTable(['GPU[ID]', 'memory total', 'memory free', 'memory used', 'utilization', 'running tasks num'])
#     table.border = False
#     for info, use_num in zip(gpu_data, task_nums):
#         table.add_row([info.id, info.memory_total, info.memory_free, info.memory_used, info.utilization, use_num])
#     result += str(table)
    
#     return 0, result


# @task_manage.client('debug')   
# def debug(id):
#     '''
#         debug [id]                    if task [id] is `CMD_ERROR`, use this show error traceback.
        
#         Example:
            
#             debug 1                   show task 1 error traceback.                
#     '''
#     (id, ), err_msg = check_input(((id, int),), )
#     if err_msg:
#         return 1, err_msg
    
#     task = task_manage.get_task(id)
#     if task is None:
#         return 1, f'[error]: can not found task[{id}]'
    
#     return 0, str(task.debug_msg)
