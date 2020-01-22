#! /usr/bin/python3
import os
import time


import socket
from gpulimit_core.socket_utils import send_all, recv_all
from gpulimit_core.task_mutiprocess import TaskQueue

msg = '''
GPU Task Manage Client:
    usage:

        client.py cmd arg1, arg2, ...
        client.py [-h]

    optional arguments:
        -h          show help
        -ls         ls GPU task queue status
        -rm [id]    del task [id]
        -f [id]     move [id] to the first
        -show [id]  show [id] output.
        -clean      remove complete task and CMD_ERROR task.
'''
def return_help(*args):
    return 0, msg


def process_commands(sock, pwd, cmds, task_queue):
    func_map = {
        '-h': return_help,
        '--help': return_help,

        '-l': task_queue.ls,
        '-ls': task_queue.ls,
        '--ls': task_queue.ls,

        '-rm': task_queue.rm,
        '--rm': task_queue.rm,

        '-f': task_queue.move_to_top,
        '--move-to-top': task_queue.move_to_top,

        '--show': task_queue.get_output_filename,
        '-show': task_queue.get_output_filename,
        '-s': task_queue.get_output_filename,

        '--clean': task_queue.clean,
        '-clean': task_queue.clean,
    }
    if func_map.get(cmds[0]):
        _, return_msg = func_map[cmds[0]](*cmds[1:])
    else:
        return_msg = 'Error: no cmd found.'
    send_all(sock, return_msg)

def create_task(sock, pwd, cmds, task_queue):
    _, result = task_queue.add(pwd, ' '.join(cmds))
    send_all(sock, result)

def process(sock, task_queue):
    msgs = recv_all(sock)
    pwd = msgs.split('|')[0]
    cmds = '|'.join(msgs.split('|')[1:])
    cmds = cmds.split()
    if cmds[0].startswith('-'):
        process_commands(sock, pwd, cmds, task_queue)
    else:
        create_task(sock, pwd, cmds, task_queue)



if __name__=='__main__':
    server_address = '/tmp/gpulimit_uds_socket'
    try:
        os.unlink(server_address)
    except OSError:
        if os.path.exists(server_address):
            raise RuntimeError('server is running.')

    task_queue = TaskQueue(logdir='/tmp/', CHECK_INT=10, MINI_MEM_REMAIN=1024)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(server_address)
    sock.listen(5)

    while True:
        connection, client_address = sock.accept()
        process(connection, task_queue)
        connection.close()