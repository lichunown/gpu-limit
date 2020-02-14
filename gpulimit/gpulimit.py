#! /usr/bin/python3

import sys, socket, os
import pickle as pk
from gpulimit.gpulimit_core.socket_utils import send_all, recv_all_str


if sys.platform == 'linux':
    server_address = '/tmp/gpulimit_uds_socket'
else:
    server_address = ('localhost', 5123)


def connect():
    if isinstance(server_address, str):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    else:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(server_address)
    except socket.error:
        print('server not start.\n\n please use `gpulimit_server` to start server.')
        sys.exit(1)
    return sock


def show_help():
    print('help: this is help')


def main():
    if len(sys.argv) == 1:
        print(f'use `{sys.argv[0]} help` to show help message.')
        exit(0)
    sock = connect()
    pwd = os.getcwd()
    
    send_all(sock, pk.dumps([pwd, sys.argv[1:]]))
    result = recv_all_str(sock)
    sock.close()
    print(f'{result}')

    if sys.argv[1] == 'log':
        if result != 'Error':
            os.system(f'less {result}')
        else:
            print('[error]: please check task id.')


if __name__=='__main__':
    main()
