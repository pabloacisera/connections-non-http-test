# packages
import socket
import threading
import datetime
import hashlib
import os
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Importación de tus módulos locales
from helpers.memory_manage import get_last_summaries, save_message, ai_self_summarize, get_size

load_dotenv()

ip_range_listen = '0.0.0.0'
port = int(os.getenv("PORT_SERVER", 65432))
gemini_api_key = os.getenv("GEMINI_API_KEY")
model = None
clients_connected = {}
chat_sessions = {}

# Cache para modelos
available_models_cache = None
cache_timestamp = 0
CACHE_DURATION = 300  # 5 minutos en segundos

# =========== CORRECCIÓN CRÍTICA: NO FORZAR API v1 ===========
if gemini_api_key:
    model = genai.Client(api_key=gemini_api_key)
    print(f"[SYSTEM]: Gemini API configurada (versión más reciente)")
else:
    print("[ERROR]: No se encontró GEMINI_API_KEY en el archivo .env")

def createId(ip_client):
    hash_object = hashlib.sha256(ip_client.encode('utf-8'))
    return hash_object.hexdigest()

def get_available_models_list(use_cache=True):
    """Obtiene lista de modelos disponibles para chat - Optimizado"""
    global available_models_cache, cache_timestamp
    
    if not model:
        return []
    
    # Usar cache si está disponible y no está expirado
    if use_cache and available_models_cache is not None:
        current_time = time.time()
        if current_time - cache_timestamp < CACHE_DURATION:
            return available_models_cache
    
    try:
        models = list(model.models.list())
        print(f"[DEBUG]: Total modelos obtenidos desde API: {len(models)}")
        
        chat_models = []
        
        for m in models:
            model_name = m.name.replace("models/", "")
            
            # Filtro rápido por nombre - excluir modelos que claramente no son de chat
            excluded_keywords = ['embedding', 'embed', 'audio', 'video', 'vision', 'veo']
            if any(excl in model_name.lower() for excl in excluded_keywords):
                continue
            
            # Para acelerar, solo probar modelos que contengan 'gemini', 'gemma', o 'chat' en el nombre
            if any(keyword in model_name.lower() for keyword in ['gemini', 'gemma', 'chat', 'text']):
                try:
                    # Prueba rápida - ver si tiene atributos de chat
                    if hasattr(m, 'supported_generation_methods'):
                        methods = m.supported_generation_methods
                        if methods and any('generate' in str(method).lower() for method in methods):
                            chat_models.append(model_name)
                    else:
                        # Si no tiene el atributo, asumir que es de chat si pasa el filtro de nombre
                        chat_models.append(model_name)
                        
                except Exception:
                    # Si hay error, incluirlo de todas formas (fallback seguro)
                    chat_models.append(model_name)
        
        # Ordenar y cachear
        chat_models.sort()
        available_models_cache = chat_models
        cache_timestamp = time.time()
        
        print(f"[DEBUG]: {len(chat_models)} modelos identificados para chat")
        return chat_models
        
    except Exception as e:
        print(f"[ERROR get_available_models]: {e}")
        # Si hay error, devolver cache si existe
        if available_models_cache:
            return available_models_cache
        return []

def change_model(client_id):
    cliente_data = clients_connected.get(client_id)
    if not cliente_data:
        return "Error: Cliente no encontrado."
    
    conn = cliente_data['conn']
    
    # Obtener modelos disponibles (sin cache para asegurar frescura)
    available_models = get_available_models_list(use_cache=False)
    
    if not available_models:
        return "Error: No se pudieron cargar los modelos disponibles. Usando modelo por defecto."
    
    # Crear opciones basadas en modelos disponibles
    options = {}
    for i, model_name in enumerate(available_models[:20], 1):  # Limitar a 20 modelos
        options[str(i)] = model_name
    
    menu_text = "\n--- CAMBIO DE MODELO ---\n"
    menu_text += "Modelos disponibles:\n"
    for key, name in options.items():
        menu_text += f"{key}. {name}\n"
    
    if len(available_models) > 20:
        menu_text += f"... y {len(available_models) - 20} modelos más\n"
        menu_text += f"Usa LIST-MODELS para ver todos los {len(available_models)} modelos\n"
    
    menu_text += "\nSeleccione una opción (o '0' para cancelar): "
    
    conn.sendall(menu_text.encode('utf-8'))
    
    try:
        response = conn.recv(1024).decode('utf-8').strip()
        
        if response == "0":
            return "Cambio de modelo cancelado."
        
        selected_model = options.get(response)

        if selected_model:
            # Guardamos el nombre siempre limpio
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

def list_models_command(client_id):
    """COMANDO: Listar modelos disponibles - Muestra todos los modelos"""
    if not model:
        return "Error: Servicio Gemini no configurado."
    
    # Obtener modelos (sin cache para información actualizada)
    available_models = get_available_models_list(use_cache=False)
    
    if not available_models:
        return "No se encontraron modelos disponibles para chat."
    
    # Crear lista paginada si hay muchos modelos
    result = "\n=== MODELOS DISPONIBLES PARA CHAT ===\n"
    result += f"Total: {len(available_models)} modelos\n\n"
    
    # Mostrar todos los modelos, 10 por línea para mejor legibilidad
    for i, model_name in enumerate(available_models, 1):
        result += f"{i:3}. {model_name}\n"
    
    # Información adicional
    current_model = clients_connected[client_id].get('selected_model', 'gemini-2.0-flash')
    result += f"\nModelo actualmente seleccionado: {current_model}\n"
    result += "Usa CHANGE-MODEL para cambiar de modelo\n"
    
    return result

def iaActivate(conn, client_id):
    """
    Modo IA con Persistencia Dual (RAM + SQLite) y Auto-Resumen.
    """
    conn.sendall("ia-activate".encode('utf-8')) 

    last_summary = get_last_summaries(client_id)
    if client_id not in chat_sessions:
        chat_sessions[client_id] = {"messages": []}

    if last_summary:
        chat_sessions[client_id]["messages"].append({
            "role": "user", 
            "content": f"[SYSTEM]: Contexto de sesiones previas: {last_summary}" 
        })

    try:
        while True:
            data = conn.recv(1024)
            if not data: break

            request = data.decode('utf-8').strip()
            
            # Obtenemos el modelo seleccionado o usamos uno por defecto
            raw_name = clients_connected[client_id].get('selected_model', "gemini-2.0-flash")
            current_model_name = raw_name.replace("models/", "")

            if request.lower() == 'ia-deactivate':
                print(f"[SYSTEM]: Generando resumen de cierre para {client_id}...")
                ai_self_summarize(client_id, chat_sessions[client_id]['messages'], model, current_model_name)
                chat_sessions[client_id]["messages"] = [] 
                break

            if get_size(chat_sessions[client_id]["messages"]) > 104857600:
                print(f"[ALERTA]: 100MB excedidos. Compactando memoria para {client_id}...")
                ai_self_summarize(client_id, chat_sessions[client_id]['messages'], model, current_model_name)
                chat_sessions[client_id]["messages"] = []

            try:
                gemini_history = []
                for m in chat_sessions[client_id]["messages"]:
                    gemini_history.append(
                        types.Content(role=m["role"], parts=[types.Part(text=m["content"])])
                    )

                if model:
                    try:
                        chat = model.chats.create(
                            model=f"models/{current_model_name}", 
                            history=gemini_history
                        )
                        response = chat.send_message(request)
                        reply = response.text if response.text else "Respuesta vacía."
                        
                    except Exception as model_error:
                        print(f"[WARNING]: Modelo {current_model_name} no disponible, usando gemini-2.0-flash")
                        chat = model.chats.create(
                            model="models/gemini-2.0-flash", 
                            history=gemini_history
                        )
                        response = chat.send_message(request)
                        reply = f"[Modelo automático: gemini-2.0-flash]\n{response.text if response.text else 'Respuesta vacía.'}"

                    timestamp_now = datetime.datetime.now()
                    chat_sessions[client_id]["messages"].append({"role": "user", "content": request, "timestamp": timestamp_now})
                    chat_sessions[client_id]["messages"].append({"role": "model", "content": reply, "timestamp": timestamp_now})
                    
                    save_message(client_id, "user", request)
                    save_message(client_id, "model", reply)
                    
                    chat_sessions[client_id]["updated_at"] = timestamp_now
                else:
                    reply = "[ERROR-IA]: Servicio Gemini no configurado."

            except Exception as e:
                reply = f"[ERROR-IA]: {str(e)}"

            conn.sendall(reply.encode('utf-8'))
            
    except Exception as e:
        print(f"[SYSTEM]: Error en sesión {client_id}: {e}")

COMMANDS = {
    "INFO": getConnectionById,
    "CHANGE-MODEL": change_model,
    "LIST-MODELS": list_models_command
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
    
    # Cargar modelos disponibles al iniciar (solo muestra información básica)
    if model:
        print("\n[SYSTEM]: Cargando información de modelos...")
        try:
            # Obtener conteo rápido sin probar todos los modelos
            all_models = list(model.models.list())
            gemini_models = []
            for m in all_models:
                model_name = m.name.replace("models/", "")
                if 'gemini' in model_name.lower() and not any(excl in model_name.lower() 
                       for excl in ['embed', 'audio', 'video', 'vision', 'veo']):
                    gemini_models.append(model_name)
            
            print(f"[SYSTEM]: {len(gemini_models)} modelos Gemini identificados")
            
            if gemini_models:
                # Mostrar algunos ejemplos
                sample_models = gemini_models[:5]
                print(f"[SYSTEM]: Ejemplos: {', '.join(sample_models)}")
                
                # Inicializar cache con modelos básicos
                global available_models_cache, cache_timestamp
                available_models_cache = gemini_models
                cache_timestamp = time.time()
                
        except Exception as e:
            print(f"[SYSTEM]: Error obteniendo información de modelos: {e}")
    
    print(f"[SYSTEM]: Modelo por defecto: gemini-2.0-flash")
    print(f"[SYSTEM]: Escuchando en puerto: {port}")
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((ip_range_listen, port))
        s.listen()
        print(f"[SYSTEM]: Servidor listo para conexiones...")

        while True:
            conn, addr = s.accept()
            client_id = createId(addr[0])
            clients_connected[client_id] = {
                'conn': conn,
                'ip': addr[0],
                'port': addr[1],
                'connectedAt': datetime.datetime.now(),
                'selected_model': 'gemini-2.0-flash'
            }
            thread = threading.Thread(target=client_handler, args=(conn, addr, client_id))
            thread.start()
            print(f"[SYSTEM]: Cliente {client_id[:8]}... conectado desde {addr[0]}:{addr[1]}")

if __name__ == "__main__":
    init_server()