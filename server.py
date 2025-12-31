# packages
import socket
import threading
import datetime
import hashlib
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

ip_range_listen = '0.0.0.0'
port = int(os.getenv("PORT_SERVER", 65432))
gemini_api_key = os.getenv("GEMINI_API_KEY")
model = None
clients_connected = {}
chat_sessions = {}

if gemini_api_key:
    model = genai.Client(api_key=gemini_api_key)

    # Imprime los modelos disponibles para depurar
    #for m in model.models.list():
    #    print(f"Modelo disponible: {m.name}")
else:
    print("[ERROR]: No se encontró GEMINI_API_KEY en el archivo .env")

def createId(ip_client):
    # Codificar el string a bytes antes de hashear
    hash_object = hashlib.sha256(ip_client.encode('utf-8'))

    # Devolver el hash como string hexadecimal
    return hash_object.hexdigest()

def change_model(client_id):
    # Recuperamos la conexión del cliente desde el diccionario global
    cliente_data = clients_connected.get(client_id)
    if not cliente_data:
        return "Error: Cliente no encontrado."
    
    conn = cliente_data['conn']

    options = {
        "1": "models/gemini-3-pro-preview",
        "2": "models/gemini-3-flash-preview",
        "3": "models/gemini-2.5-pro",
        "4": "models/gemini-2.5-flash",
        "5": "models/gemini-2.0-flash-exp",
        "6": "models/gemini-2.0-flash-lite",
        "7": "models/gemma-3-27b-it",
        "8": "models/deep-research-pro-preview",
        "9": "models/gemini-2.5-computer-use-preview",
        "10": "models/gemini-flash-latest"
    }

    # 1. Enviar el menú
    menu_text = "\n--- CAMBIO DE MODELO ---\n"
    for key, name in options.items():
        menu_text += f"{key}. {name}\n"
    menu_text += "Seleccione una opción: "
    
    conn.sendall(menu_text.encode('utf-8'))
    
    # 2. Recibir la elección
    try:
        response = conn.recv(1024).decode('utf-8').strip()
        selected_model = options.get(response)

        clients_connected[client_id]['selected_model'] = selected_model
        # Opcional: Reiniciar historial para evitar errores de compatibilidad entre modelos
        if client_id in chat_sessions:
            chat_sessions[client_id]['messages'] = [] 
            return f"CONFIRMACIÓN: Modelo actualizado a -> {selected_model}"
        else:
            # Si la opción no es válida, usamos uno por defecto
            clients_connected[client_id]['selected_model'] = "models/gemini-2.5-flash"
            return "Opción inválida. Se ha asignado gemini-2.5-flash por defecto."
            
    except Exception as e:
        return f"Error durante el cambio: {str(e)}"

def getConnectionById(id):
    # Buscamos en el diccionario usando el ID (Hash)
    cliente = clients_connected.get(id)
    if not cliente:
        return "La conexion no se encuentra registrada"
    
    # Convertimos el diccionario a un String para poder enviarlo por el socket
    return f"ID: {id} | IP: {cliente['ip']} | Puerto: {cliente['port']} | Desde: {cliente['connectedAt']}"

def iaActivate(conn, client_id):
    conn.sendall("ia-activate".encode('utf-8')) 

    try:
        while True:
            data = conn.recv(1024)
            if not data: 
                break

            request = data.decode('utf-8').strip()
            
            if request.lower() == 'ia-deactivate':
                break

            reply = "No se pudo obtener una respuesta de la IA."

            try:
                # 1. Inicializar sesión si no existe
                if client_id not in chat_sessions:
                    chat_sessions[client_id] = {
                        "messages": [], # Aquí guardamos: {"role":..., "content":..., "timestamp":...}
                        "updated_at": datetime.datetime.now()
                    }
                
                # 2. Preparar el historial para Gemini (solo roles y partes)
                # Filtramos nuestros metadatos para que la IA no se confunda
                gemini_history = []
                for m in chat_sessions[client_id]["messages"]:
                    gemini_history.append(
                        types.Content(
                            role=m["role"],
                            parts=[types.Part(text=m["content"])]
                        )
                    )

                # Buscamos si el cliente tiene un modelo preferido, si no, usamos el flash por defecto
                current_model_name = clients_connected[client_id].get('selected_model', "models/gemini-2.5-flash")

                if model:
                    # 3. Crear el chat con el historial filtrado
                    chat = model.chats.create(
                        model=current_model_name,
                        history=gemini_history
                    )

                    # 4. Enviar mensaje
                    response = chat.send_message(request)
                    reply = response.text if response.text else "Respuesta vacía."

                    # 5. ACTUALIZACIÓN CON FECHAS INDIVIDUALES
                    timestamp_now = datetime.datetime.now()
                    
                    # Guardamos el mensaje del usuario
                    chat_sessions[client_id]["messages"].append({
                        "role": "user",
                        "content": request,
                        "timestamp": timestamp_now
                    })
                    
                    # Guardamos la respuesta de la IA
                    chat_sessions[client_id]["messages"].append({
                        "role": "model",
                        "content": reply,
                        "timestamp": timestamp_now
                    })
                    
                    # Actualizamos la fecha general de la sesión
                    chat_sessions[client_id]["updated_at"] = timestamp_now
                    print(f"session actualizada: {chat_sessions[client_id]}")
                else:
                    reply = "[ERROR-IA]: Servicio no configurado."

            except Exception as e:
                reply = f"[ERROR-IA]: {str(e)}"

            conn.sendall(reply.encode('utf-8'))
            
    except Exception as e:
        print(f"[SYSTEM]: Error en sesión {client_id}: {e}")

COMMANDS = {
    "INFO": getConnectionById,
    "CHANGE-MODEL": change_model,
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
                iaActivate(conn, client_id)
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