# server.py
import socket
import threading
import datetime
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Importaciones propias
from helpers.memory_manage import get_last_summaries, save_message, ai_self_summarize, get_size
from core.security import create_ssl_context
from core.models import ModelManager
from core.commands import create_client_id, get_connection_info, change_model_command, list_models_command

load_dotenv()

# Configuración
IP_SERVER = os.getenv("IP_SERVER", "0.0.0.0")
PORT_SERVER = int(os.getenv("PORT_SERVER", 65432))
USE_TLS = os.getenv("USE_TLS", "true").lower() == "true"

# Estado global
clients_connected = {}
chat_sessions = {}
gemini_client = None
model_manager = None

# Inicializar Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    gemini_client = genai.Client(api_key=api_key)
    model_manager = ModelManager(gemini_client)
    print("[SYSTEM] Gemini API configurada")
else:
    print("[WARNING] GEMINI_API_KEY no encontrada")

def ia_activate(conn, client_id):
    """Modo IA activado"""
    conn.sendall(b"ia-activate")
    
    # Cargar contexto previo
    last_summary = get_last_summaries(client_id)
    if client_id not in chat_sessions:
        chat_sessions[client_id] = {"messages": []}
    
    if last_summary:
        chat_sessions[client_id]["messages"].append({
            "role": "user",
            "content": f"[CONTEXTO ANTERIOR]: {last_summary}"
        })
    
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            
            request = data.decode().strip()
            
            # Salir del modo IA
            if request.lower() == 'ia-deactivate':
                print(f"[SYSTEM] Cerrando sesión IA para {client_id[:8]}")
                current_model = clients_connected[client_id].get('selected_model', 'gemini-2.0-flash')
                ai_self_summarize(client_id, chat_sessions[client_id]['messages'], gemini_client, current_model)
                chat_sessions[client_id]["messages"] = []
                break
            
            # Control de tamaño
            if get_size(chat_sessions[client_id]["messages"]) > 104857600:  # 100MB
                print(f"[SYSTEM] Compactando memoria para {client_id[:8]}")
                current_model = clients_connected[client_id].get('selected_model', 'gemini-2.0-flash')
                ai_self_summarize(client_id, chat_sessions[client_id]['messages'], gemini_client, current_model)
                chat_sessions[client_id]["messages"] = []
            
            # Procesar con Gemini
            try:
                current_model = clients_connected[client_id].get('selected_model', 'gemini-2.0-flash')
                
                # Preparar historial
                gemini_history = []
                for msg in chat_sessions[client_id]["messages"]:
                    gemini_history.append(
                        types.Content(role=msg["role"], parts=[types.Part(text=msg["content"])])
                    )
                
                # Obtener respuesta
                if gemini_client:
                    chat = gemini_client.chats.create(
                        model=f"models/{current_model}",
                        history=gemini_history
                    )
                    response = chat.send_message(request)
                    reply = response.text if response.text else "(sin respuesta)"
                else:
                    reply = "Error: Gemini no configurado"
                
                # Guardar en memoria
                timestamp = datetime.datetime.now()
                chat_sessions[client_id]["messages"].append({
                    "role": "user",
                    "content": request,
                    "timestamp": timestamp
                })
                chat_sessions[client_id]["messages"].append({
                    "role": "model",
                    "content": reply,
                    "timestamp": timestamp
                })
                
                # Persistir en DB
                save_message(client_id, "user", request)
                save_message(client_id, "model", reply)
                
            except Exception as e:
                reply = f"[ERROR]: {str(e)}"
            
            # Enviar respuesta
            conn.sendall(reply.encode())
            
    except Exception as e:
        print(f"[ERROR] Sesión IA {client_id[:8]}: {e}")

def client_handler(conn, addr, client_id):
    """Maneja conexión de cliente"""
    conn.sendall(f"ID:{client_id[:12]}\nConectado a {IP_SERVER}:{PORT_SERVER}".encode())
    
    # Diccionario de comandos
    COMMANDS = {
        "INFO": lambda: get_connection_info(client_id, clients_connected),
        "CHANGE-MODEL": lambda: change_model_command(client_id, clients_connected, chat_sessions, model_manager),
        "LIST-MODELS": lambda: list_models_command(client_id, clients_connected, model_manager)
    }
    
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            
            cmd = data.decode().strip().upper()
            
            # Modo IA
            if cmd == "IA":
                ia_activate(conn, client_id)
                continue
            
            # Comandos normales
            handler = COMMANDS.get(cmd)
            if handler:
                response = handler()
            else:
                response = f"Comando '{cmd}' no reconocido\nComandos: INFO, CHANGE-MODEL, LIST-MODELS, IA"
            
            conn.sendall(response.encode())
            
    except Exception as e:
        print(f"[ERROR] Cliente {client_id[:8]}: {e}")
    finally:
        # Limpiar al desconectar
        if client_id in clients_connected:
            del clients_connected[client_id]
        conn.close()
        print(f"[SYSTEM] Cliente {client_id[:8]} desconectado")

def start_server():
    """Inicia el servidor"""
    print(f"[SYSTEM] Iniciando servidor en {IP_SERVER}:{PORT_SERVER}")
    print(f"[SYSTEM] TLS: {'HABILITADO' if USE_TLS else 'DESHABILITADO'}")
    
    # Configurar TLS
    ssl_context = None
    if USE_TLS:
        ssl_context = create_ssl_context()
        if not ssl_context:
            print("[WARNING] Continuando sin TLS")
    
    # Cargar modelos si hay Gemini
    if model_manager:
        models = model_manager.get_available_models()
        print(f"[SYSTEM] {len(models)} modelos cargados")
    
    # Crear socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((IP_SERVER, PORT_SERVER))
        server_socket.listen(5)
        
        print(f"[SYSTEM] Escuchando conexiones...")
        
        while True:
            conn, addr = server_socket.accept()
            
            # Aplicar TLS si está configurado
            if USE_TLS and ssl_context:
                try:
                    conn = ssl_context.wrap_socket(conn, server_side=True)
                    print(f"[SECURITY] TLS establecido con {addr[0]}")
                except Exception as e:
                    print(f"[ERROR] Fallo TLS: {e}")
                    conn.close()
                    continue
            
            # Registrar cliente
            client_id = create_client_id(addr[0])
            clients_connected[client_id] = {
                'conn': conn,
                'ip': addr[0],
                'port': addr[1],
                'connectedAt': datetime.datetime.now(),
                'selected_model': 'gemini-2.0-flash'
            }
            
            # Iniciar hilo
            thread = threading.Thread(
                target=client_handler,
                args=(conn, addr, client_id),
                daemon=True
            )
            thread.start()
            
            print(f"[SYSTEM] Cliente {client_id[:8]} conectado desde {addr[0]}:{addr[1]}")

if __name__ == "__main__":
    start_server()