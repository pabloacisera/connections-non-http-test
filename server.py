# packages
import socket
import threading
import datetime
import hashlib

ip_range_listen = '0.0.0.0'
port = 65432
clients_connected = {}

def createId(ip_client):

    hash_object = hashlib.sha256(ip_client)

    return hash_object

def init_server():

    print(f"Servidor iniciado {datetime.datetime.now()}. Esperando conexiones entrantes")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # evita error de puerto ocupado
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # crea una instancia de conexion
        s.bind((ip_range_listen, port))
        # escucha
        s.listen()
        print(f"Servidor corriendo en puerto: {port}")

        # mientras haya conexión
        while True:
            conn, addr = s.accept()

            print(f'Conexion establecida: {conn, addr}')

init_server()