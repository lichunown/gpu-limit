#! /usr/bin/python3
import os, sys, inspect
import time
import socket
import traceback

import pickle as pk

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
sys.path.insert(0, parentdir) 

from gpulimit.gpulimit_core import recv_all, send_all_str
from gpulimit.gpulimit_core import task_manage


"""
GPU Task Manage
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
        
        self.task_manage = task_manage
        if sys.platform == 'linux':
            self.task_manage.start(logdir='/tmp/')
        else:
            self.task_manage.start(logdir='./tmp/')
        
        self.func_map = {
                
            '-h': self._help,
            '--help': self._help,
            'help': self._help, 
            
            'add': self.task_manage.add,
            
        }
#        print(self.task_manage.func_map)
        self.func_map.update(self.task_manage.func_map)
        
        
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
        
        try:
            if cmds[0] == 'add':
                
                msg = self._create_task(pwd, cmds)
            else:
                msg = self._process_commands(pwd, cmds)
        except Exception:
            msg = traceback.format_exc()
            
        send_all_str(sock, msg)  
        
    def _get_args(self, cmds, get_all=True):
        add_arg = True
        
        args = []
        kwargs = {}
        for cmd in cmds:
            if not cmd.startswith('--'):
                if not get_all:
                    add_arg = False
                    
            if cmd.startswith('--'):
                cmd = cmd.lstrip('--')
                splits = cmd.split('=')
                if len(splits) == 1:
                    kwargs[cmd] = True
                    continue
                key = splits[0]
                value = '='.join(splits[1:])
                kwargs[key] = value
            else:
                if add_arg:
                    args.append(cmd)
                    
        return args, kwargs
        
    def _check_input(self, func, args, kwargs):
        fullargspec = inspect.getfullargspec(func)
        return_msg = ''
        if fullargspec.varkw is None:
            for key in kwargs:
                if not key in fullargspec.kwonlyargs:
                    return_msg += f'[Error]: not support param `{key}`. \n'
        if fullargspec.varargs is None:
            if len(fullargspec.args) == 0:
                max_args_len = 0
            else:
                max_args_len = len(fullargspec.args)-1 if fullargspec.args[0] == 'self' else len(fullargspec.args)
            defaults_nums = 0 if fullargspec.defaults is None else len(fullargspec.defaults)
            min_args_len = max_args_len - defaults_nums
            if len(args) < min_args_len:
                return_msg += f'[Error]: have min {min_args_len} input, but you input {len(args)} args. \n'
            if max_args_len < len(args):
                return_msg += f'[Error]: have max {max_args_len} input, but you input {len(args)} args. \n'
        return return_msg
    
        
    def _create_task(self, pwd, cmds):
        args, kwargs = self._get_args(cmds[1:], False)
        i = -1
        for i, cmd in enumerate(cmds[1:]):
            if not cmd.startswith('--'):
                break
        cmds = cmds[i + 1:]
        if len(cmds) == 0:
            return f'[Error]: you input args {kwargs}, but no cmd input.'
        
        err_msg = ''
        for arg in args:
            err_msg += f'[Error]: add not support args {arg}'
        for kwarg in kwargs:
            if kwarg not in inspect.getfullargspec(self.task_manage.add).kwonlyargs:
                err_msg += f'[Error]: add not support kwargs {kwarg}'
        if err_msg: return err_msg
        
        _, result = self.task_manage.add(pwd, cmds, **kwargs)
        return result
        
    def _process_commands(self, pwd, cmds):
        if self.func_map.get(cmds[0]):
            func = self.func_map[cmds[0]]
            
            args, kwargs = self._get_args(cmds[1:])         
            err_msg = self._check_input(func, args, kwargs)
            if err_msg: return err_msg
            
            _, return_msg = func(*args, **kwargs)

        else:
            return_msg = '[error]: no cmd found.'
        return return_msg
        
    def _help(self, cmd=None):
        '''
        help [cmd]                    show help
        '''
        
        header = '''
GPU Task Manage:
    usage:
        
        client.py -h                  show help
        gpulimit add [cmds]           add task [cmds] to gpulimit queue.
        

    other commands:\n\n'''
    
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
