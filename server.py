# packages
import socket
import threading
import datetime
import hashlib
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

ip_range_listen = '0.0.0.0'
port = int(os.getenv("PORT_SERVER", 65432))
gemini_api_key = os.getenv("GEMINI_API_KEY")
model = None

if gemini_api_key:
    model = genai.Client(api_key=gemini_api_key)

    # Imprime los modelos disponibles para depurar
    for m in model.models.list():
        print(f"Modelo disponible: {m.name}")
else:
    print("[ERROR]: No se encontró GEMINI_API_KEY en el archivo .env")


clients_connected = {}

def createId(ip_client):
    # Codificar el string a bytes antes de hashear
    hash_object = hashlib.sha256(ip_client.encode('utf-8'))

    # Devolver el hash como string hexadecimal
    return hash_object.hexdigest()

def getConnectionById(id):
    # Buscamos en el diccionario usando el ID (Hash)
    cliente = clients_connected.get(id)
    if not cliente:
        return "La conexion no se encuentra registrada"
    
    # Convertimos el diccionario a un String para poder enviarlo por el socket
    return f"ID: {id} | IP: {cliente['ip']} | Puerto: {cliente['port']} | Desde: {cliente['connectedAt']}"

def iaActivate(conn):
    conn.sendall("ia-activate".encode('utf-8')) 

    try:
        while True:
            data = conn.recv(1024)
            if not data: break

            request = data.decode('utf-8').strip()
            
            if request.lower() == 'ia-deactivate':
                break

            # Inicializamos reply con un mensaje por defecto
            reply = "No se pudo obtener una respuesta de la IA."

            try:
                # Verificamos si el cliente de IA existe
                if model:
                    response = model.models.generate_content(
                        model='models/gemini-2.5-flash-lite',
                        contents=request
                    )
                    # Usamos getattr o una validación simple para asegurar el string
                    reply = response.text if response.text else "La IA devolvió una respuesta vacía."
                else:
                    reply = "[ERROR-IA]: El servicio de IA no está configurado (falta API KEY)."
            except Exception as e:
                reply = f"[ERROR-IA]: {e}"

            # Ahora estamos seguros de que reply es un string
            conn.sendall(reply.encode('utf-8'))
            
    except Exception as e:
        print(f"[SYSTEM]: error en la consulta {e}")

COMMANDS = {
    "INFO": getConnectionById,
}

def client_handler(conn, addr, client_id):
    # envio del id
    conn.sendall(f"ID_ASIGNADO:{client_id}".encode())

    try:
        # matenemos escuchando
        while True:
            # configuracion de mensaje recibido
            data = conn.recv(1024)
            if not data: break

            request = data.decode('utf-8').strip().upper()

            if request == 'IA':
                iaActivate(conn)
                continue

            commandExists = COMMANDS.get(request)

            if commandExists:
                response = commandExists(client_id)
            else:
                response = "El comando seleccionado no existe o no se encuentra disponible"

            conn.sendall(response.encode("utf-8"))
    except Exception as e:
        print(f'Error con el cliente {client_id}: {e}')
    finally:
        # Limpieza: eliminar del registro al desconectar
        if client_id in clients_connected:
            del clients_connected[client_id]
        conn.close()

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

            print(f'Nueva conexion exitosa')

            # Acceder a la IP del cliente
            client_ip = addr[0]  # Esto es '192.168.1.14'
            client_port = addr[1]  # Esto es 53044

            print(f'Generando id...')
            client_id = createId(client_ip)
            
            print(f'Id generado. Almacenando cliente...{client_id}')

            clients_connected[client_id]={
                'conn': conn,
                'ip': client_ip,
                'port': client_port,
                'connectedAt': datetime.datetime.now()
            }

            print("Clientes almacenados: ", clients_connected)

            # creamos un hilo y un handler para ese hilo
            thread = threading.Thread(target=client_handler, args=(conn, addr, client_id))
            thread.start()
            
init_server()