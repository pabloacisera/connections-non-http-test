import socket

ip_server = '192.168.1.10'
port = 65432

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    #conectar con el servidor
    s.connect((ip_server, port))