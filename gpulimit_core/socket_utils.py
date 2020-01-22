import socket
import struct


def send_all(sock, msg):
    msg = bytes(msg, encoding='utf8')
    sock.send(struct.pack('>Q', len(msg)))
    sock.sendall(msg)
    
def recv_all(sock, buffer_size=8192):
    msg_len = sock.recv(8)
    msg_len = struct.unpack('>Q', msg_len)[0]
    msg = b''
    while len(msg) < msg_len:
        msg += sock.recv(buffer_size)
    return msg.decode('utf8')
    

#%%
    
#sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#sock.bind(('0.0.0.0', 19999))
#sock.listen(1)
#
#conn,addr = sock.accept() 
#print(recv_all(conn))
#send_all(conn, 'dqwwwdwd')
#sock.close()

#%%

#sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#sock.connect(('127.0.0.1', 19999))
#send_all(sock, 'awsefwseefeewfdsifdslxc')
#print(recv_all(sock))
