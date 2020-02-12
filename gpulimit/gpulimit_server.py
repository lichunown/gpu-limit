#! /usr/bin/python3
import os, sys, inspect
import time
import socket

import pickle as pk

from gpulimit_core.socket_utils import recv_all, send_all_str
from gpulimit_core.task_mutiprocess import TaskQueue, _get_gpu_info


"""
GPU Task Manage Server
"""


class Server(object):
    def __init__(self):
        if sys.platform == 'linux':
            server_address = '/tmp/gpulimit_uds_socket'
            try:
                os.unlink(server_address)
            except OSError:
                if os.path.exists(server_address):
                    raise RuntimeError('server is running.')
        else:
            server_address = ('0.0.0.0', 5123)
        self.server_address = server_address
        
        if sys.platform == 'linux':
            self.task_queue = TaskQueue(logdir='/tmp/', MINI_MEM_REMAIN=1024)
        else:
            self.task_queue = TaskQueue(logdir='./tmp/', MINI_MEM_REMAIN=1024)
            
        self.func_map = {
                
            '-h': self._help,
            '--help': self._help,
            'help': self._help, 
            
            'ls': self.task_queue.ls,
            
            'kill': self.task_queue.kill, 
            
            'start': self.task_queue.start,
            
            'rm': self.task_queue.rm, 
    
            'move': self.task_queue.move_to_top, 
    
            'log': self.task_queue.get_output_filename, 
    
            'clean': self.task_queue.clean, 
            
            'set': self.task_queue.set_property, 
            
        }
    def start(self):
        if isinstance(self.server_address, str):
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(self.server_address)
        sock.listen(5)
        print('start gpulimit server.')
        print(f'listening at {self.server_address}')
        while True:
            connection, client_address = sock.accept()
            self._process(connection)
            connection.close()
            
    def _process(self, sock):
        msgs = recv_all(sock)
        pwd, cmds = pk.loads(msgs)
        
        if cmds[0] == 'add':
            self._create_task(sock, pwd, cmds[1:])
        else:
            self._process_commands(sock, pwd, cmds)
            
    def _create_task(self, sock, pwd, cmds):
        _, result = self.task_queue.add(pwd, cmds)
        send_all_str(sock, result)
        
    def _process_commands(self, sock, pwd, cmds):
        if self.func_map.get(cmds[0]):
            func = self.func_map[cmds[0]]
            
            argspec = inspect.getargspec(func)
            args_nums = len(argspec.args) - 1 if argspec.args[0] == 'self' else len(argspec.args)
                
            if ( argspec.varargs is None and argspec.keywords is None and \
                len(cmds[1:]) > args_nums ) or \
                len(cmds[1:]) < args_nums - (len(argspec.defaults) if argspec.defaults is not None else 0):
                    send_all_str(sock, f'[Error]: {cmds[0]} have {len(argspec.args)} nums args, which {(len(argspec.defaults) if argspec.defaults is not None else 0)} have set default. but you input {len(cmds[1:])} args.')
                    return
                
            args = []
            kwargs = {}
            for cmd in cmds[1:]:
                if cmd.startswith('--'):
                    cmd = cmd.lstrip('--')
                    splits = cmd.split('=')
                    if len(splits) == 1:
                        kwargs[cmd] = False
                        continue
                    key = splits[0]
                    value = '='.join(splits[1:])
                    kwargs[key] = value
                else:
                    args.append(cmd)
                    
            _, return_msg = func(*args, **kwargs)

        else:
            return_msg = '[error]: no cmd found.'
        send_all_str(sock, return_msg)
        
    def _help(self, cmd=None):
        '''
        help [cmd]                    show help
        '''
        
        header = '''
GPU Task Manage:
    usage:
        
        client.py -h                  show help
        gpulimit add [cmds]           add task [cmds] to gpulimit queue.
        

    other commands:\n'''
    
        if cmd is not None:
            if self.func_map.get(cmd):
                func = self.func_map.get(cmd)
                if func.__doc__ is not None:
                    return 0, func.__doc__
                else:
                    return 0, f'\n        {cmd}\t\tno info\n'
            else:
                return 1, f'[Error]: Can not found command: `{cmd}`.\n Please use help to find more infomation.'
        
        func_info = ''
        for cmd, func in self.func_map.items():
            if not cmd.startswith('-'):
                if func.__doc__ is not None:
                    func_info += list(filter(lambda x: x, func.__doc__.split('\n')))[0] + '\n'
                else:
                    func_info += f'        {cmd}\t\tno info\n'

        return 0, header + func_info
    

def main():
    server = Server()
    server.start()
    

if __name__=='__main__':
    main()
