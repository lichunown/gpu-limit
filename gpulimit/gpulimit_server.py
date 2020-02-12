#! /usr/bin/python3
import os, sys
import time
import pickle as pk

import socket
from gpulimit_core.socket_utils import recv_all, send_all_str
from gpulimit_core.task_mutiprocess import TaskQueue

msg = '''
GPU Task Manage Client:
    usage:
        
        client.py -h                  show help
        gpulimit add [cmds]           add task [cmds] to gpulimit queue.
        

    other commands:
        help                          show help
        ls                            ls GPU task queue status
        rm [id]                       del task [id]
        kill [id]                     kill task
        move [id] [index(default=0)]  move [id] to the first
        log [id]                      show [id] output.
        clean [type(default=None)]    remove complete task and CMD_ERROR task.
        
        set [name] [value]            set some property.
'''
def return_help(*args):
    return 0, msg


def create_task(sock, pwd, cmds, task_queue):
    _, result = task_queue.add(pwd, cmds)
    send_all_str(sock, result)
    

def process_commands(sock, pwd, cmds, task_queue):
    func_map = {
        '-h': (return_help, (0,)),
        '--help': (return_help, (0,)),
        'help': (return_help, (0,)),
        
        'ls': (task_queue.ls, (0,)),
        
        'kill': (task_queue.kill, (1,)),
        
        'start': (task_queue.start, (0,1,)),
        
        'rm': (task_queue.rm, (1,)),

        'move': (task_queue.move_to_top, (1,2)),

        'log': (task_queue.get_output_filename, (1,)),

        'clean': (task_queue.clean, tuple(range(10))),
        
        'set': (task_queue.set_property, (2,)),
    }
    
    if func_map.get(cmds[0]):
        func, arg_nums = func_map[cmds[0]]
        if len(cmds[1:]) in arg_nums:
            _, return_msg = func(*cmds[1:])
        else:
            return_msg = f'{cmds[0]} can have {arg_nums} nums args, but you input {len(cmds[1:])} args.'
    else:
        return_msg = '[error]: no cmd found.'
    send_all_str(sock, return_msg)

def process(sock, task_queue):
    msgs = recv_all(sock)
    pwd, cmds = pk.loads(msgs)
    
    if cmds[0] == 'add':
        create_task(sock, pwd, cmds[1:], task_queue)
    else:
        process_commands(sock, pwd, cmds, task_queue)


def main():
    if sys.platform == 'linux':
        server_address = '/tmp/gpulimit_uds_socket'
        try:
            os.unlink(server_address)
        except OSError:
            if os.path.exists(server_address):
                raise RuntimeError('server is running.')
    else:
        server_address = ('0.0.0.0', 5123)
        
    if sys.platform == 'linux':
        task_queue = TaskQueue(logdir='/tmp/', MINI_MEM_REMAIN=1024)
    else:
        task_queue = TaskQueue(logdir='./tmp/', MINI_MEM_REMAIN=1024)
    if isinstance(server_address, str):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    else:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(server_address)
    sock.listen(5)
    print('start gpulimit server.')
    print(f'listening at {server_address}')
    while True:
        connection, client_address = sock.accept()
        process(connection, task_queue)
        connection.close()


if __name__=='__main__':
    main()
