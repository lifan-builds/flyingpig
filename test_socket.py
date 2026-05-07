import socket
s = socket.socket()
s.bind(('127.0.0.1', 0))
print(s.getsockname())
