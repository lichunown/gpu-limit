#! /usr/bin/python3

import sys, socket, os
from gpulimit_core.socket_utils import send_all, recv_all


server_address = '/tmp/gpulimit_uds_socket'


def connect():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(server_address)
    except socket.error:
        print('server not start.\n\n please use `gpulimit_server` to start server.')
        sys.exit(1)
    return sock

def show_help():
    print('help: this is help')

if __name__=='__main__':
    if len(sys.argv) == 1:
        show_help()
        exit(0)
    sock = connect()
    pwd = os.getcwd()
    cmds = ' '.join(sys.argv[1:])
    send_msg = '|'.join([pwd, cmds])
    send_all(sock, send_msg)
    result = recv_all(sock)
    sock.close()
    print(result)

    if cmds.startswith('-show'):
        if result != 'Error':
            os.system(f'less {result}')
    
    
