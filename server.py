# packages
import socket
import threading
import datetime
import hashlib
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Importación corregida de tus módulos locales
from helpers.memory_manage import get_last_summaries, save_message, ai_self_summarize, get_size

load_dotenv()

ip_range_listen = '0.0.0.0'
port = int(os.getenv("PORT_SERVER", 65432))
gemini_api_key = os.getenv("GEMINI_API_KEY")
model = None
clients_connected = {}
chat_sessions = {}

if gemini_api_key:
    model = genai.Client(api_key=gemini_api_key, http_options={'api_version': 'v1'})
else:
    print("[ERROR]: No se encontró GEMINI_API_KEY en el archivo .env")

def createId(ip_client):
    hash_object = hashlib.sha256(ip_client.encode('utf-8'))
    return hash_object.hexdigest()

def change_model(client_id):
    cliente_data = clients_connected.get(client_id)
    if not cliente_data:
        return "Error: Cliente no encontrado."
    
    conn = cliente_data['conn']
    options = {
        "1": "gemini-2.0-flash",
        "2": "gemini-2.0-flash-lite",
        "3": "gemini-1.5-pro",
        "4": "gemini-1.5-flash",
        "5": "gemini-1.0-pro"
    }

    menu_text = "\n--- CAMBIO DE MODELO ---\n"
    for key, name in options.items():
        menu_text += f"{key}. {name}\n"
    menu_text += "Seleccione una opción: "
    
    conn.sendall(menu_text.encode('utf-8'))
    
    try:
        response = conn.recv(1024).decode('utf-8').strip()
        selected_model = options.get(response)

        if selected_model:
            # LIMPIEZA E INDENTACIÓN CORREGIDA:
            # Eliminamos cualquier prefijo accidental para que el SDK no se confunda
            clean_model_name = selected_model.replace("models/", "") 
            clients_connected[client_id]['selected_model'] = clean_model_name
            
            if client_id in chat_sessions:
                chat_sessions[client_id]['messages'] = [] 
            
            return f"CONFIRMACIÓN: Modelo actualizado a -> {clean_model_name}"
        else:
            return "Opción inválida. No se realizaron cambios."
            
    except Exception as e:
        return f"Error durante el cambio: {str(e)}"

def getConnectionById(id):
    cliente = clients_connected.get(id)
    if not cliente:
        return "La conexion no se encuentra registrada"
    return f"ID: {id} | IP: {cliente['ip']} | Puerto: {cliente['port']} | Desde: {cliente['connectedAt']}"

def iaActivate(conn, client_id):
    """
    Modo IA con Persistencia Dual (RAM + SQLite) y Auto-Resumen.
    """
    conn.sendall("ia-activate".encode('utf-8')) 

    # CARGAR contexto histórico de Capa 3 (Resúmenes)
    last_summary = get_last_summaries(client_id)
    if client_id not in chat_sessions:
        chat_sessions[client_id] = {"messages": []}

    if last_summary:
        # Inyectamos el resumen en RAM para dar contexto a la IA
        chat_sessions[client_id]["messages"].append({
            "role": "user", 
            "content": f"[SYSTEM]: Contexto de sesiones previas: {last_summary}" 
        })

    try:
        while True:
            data = conn.recv(1024)
            if not data: break

            request = data.decode('utf-8').strip()
            
            # Buscamos el modelo actual del cliente para todas las operaciones
            current_model_name = clients_connected[client_id].get('selected_model', "gemini-2.0-flash")

            # SALIDA: Generar resumen final y limpiar RAM
            if request.lower() == 'ia-deactivate':
                print(f"[SYSTEM]: Generando resumen de cierre para {client_id}...")
                ai_self_summarize(client_id, chat_sessions[client_id]['messages'], model, current_model_name)
                chat_sessions[client_id]["messages"] = [] 
                break

            # VERIFICACIÓN DE RAM (Umbral 100MB): Auto-resumen proactivo
            if get_size(chat_sessions[client_id]["messages"]) > 104857600:
                print(f"[ALERTA]: 100MB excedidos. Compactando memoria para {client_id}...")
                ai_self_summarize(client_id, chat_sessions[client_id]['messages'], model, current_model_name)
                chat_sessions[client_id]["messages"] = []

            try:
                # Preparar el historial filtrado para Gemini
                gemini_history = []
                for m in chat_sessions[client_id]["messages"]:
                    gemini_history.append(
                        types.Content(role=m["role"], parts=[types.Part(text=m["content"])])
                    )

                if model:
                    chat = model.chats.create(model=current_model_name, history=gemini_history)
                    response = chat.send_message(request)
                    reply = response.text if response.text else "Respuesta vacía."

                    # --- PERSISTENCIA DUAL ---
                    timestamp_now = datetime.datetime.now()
                    
                    # 1. Guardar en RAM (Capa 1)
                    chat_sessions[client_id]["messages"].append({"role": "user", "content": request, "timestamp": timestamp_now})
                    chat_sessions[client_id]["messages"].append({"role": "model", "content": reply, "timestamp": timestamp_now})
                    
                    # 2. Guardar en SQLITE (Capa 2: Mensajes crudos)
                    save_message(client_id, "user", request)
                    save_message(client_id, "model", reply)
                    
                    chat_sessions[client_id]["updated_at"] = timestamp_now
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
    conn.sendall(f"ID_ASIGNADO:{client_id}".encode())
    try:
        while True:
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
                response = "El comando seleccionado no existe."

            conn.sendall(response.encode("utf-8"))
    except Exception as e:
        print(f'Error con el cliente {client_id}: {e}')
    finally:
        if client_id in clients_connected:
            del clients_connected[client_id]
        conn.close()

def init_server():
    print(f"Servidor iniciado {datetime.datetime.now()}.")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((ip_range_listen, port))
        s.listen()
        print(f"Escuchando en puerto: {port}")

        while True:
            conn, addr = s.accept()
            client_id = createId(addr[0])
            clients_connected[client_id] = {
                'conn': conn,
                'ip': addr[0],
                'port': addr[1],
                'connectedAt': datetime.datetime.now()
            }
            thread = threading.Thread(target=client_handler, args=(conn, addr, client_id))
            thread.start()

if __name__ == "__main__":
    init_server()