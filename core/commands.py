# core/commands.py
"""
Comandos disponibles para clientes
"""
import hashlib

def create_client_id(ip_address):
    """Genera ID único para cliente"""
    return hashlib.sha256(ip_address.encode()).hexdigest()

def get_connection_info(client_id, clients_connected):
    """Retorna información de conexión"""
    client = clients_connected.get(client_id)
    if not client:
        return "Cliente no encontrado"
    
    return f"ID: {client_id[:12]} | IP: {client['ip']} | Puerto: {client['port']} | Conectado: {client['connectedAt'].strftime('%H:%M:%S')}"

def change_model_command(client_id, clients_connected, chat_sessions, model_manager):
    """Maneja cambio de modelo"""
    client = clients_connected.get(client_id)
    if not client:
        return "Error: Cliente no encontrado"
    
    conn = client['conn']
    available_models = model_manager.get_available_models(use_cache=False)
    
    if not available_models:
        return "Error: No se pudieron cargar modelos"
    
    # Enviar menú
    menu = "\n--- CAMBIO DE MODELO ---\n"
    menu += "Seleccione modelo:\n"
    
    options = {}
    for i, model_name in enumerate(available_models[:15], 1):
        options[str(i)] = model_name
        menu += f"{i}. {model_name}\n"
    
    menu += "\n0. Cancelar\n> "
    conn.sendall(menu.encode())
    
    try:
        choice = conn.recv(1024).decode().strip()
        if choice == "0":
            return "Operación cancelada"
        
        selected = options.get(choice)
        if selected:
            clients_connected[client_id]['selected_model'] = selected
            if client_id in chat_sessions:
                chat_sessions[client_id]['messages'] = []
            return f"✅ Modelo cambiado a: {selected}"
        else:
            return "❌ Opción inválida"
            
    except Exception as e:
        return f"Error: {str(e)}"

def list_models_command(client_id, clients_connected, model_manager):
    """Lista modelos disponibles"""
    available_models = model_manager.get_available_models(use_cache=False)
    
    if not available_models:
        return "No hay modelos disponibles"
    
    response = "\n=== MODELOS DISPONIBLES ===\n"
    for i, model_name in enumerate(available_models, 1):
        response += f"{i:3}. {model_name}\n"
    
    current = clients_connected[client_id].get('selected_model', 'gemini-2.0-flash')
    response += f"\n📌 Modelo actual: {current}\n"
    
    return response