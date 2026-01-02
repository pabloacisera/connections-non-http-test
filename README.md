AI-Socket Terminal Bridge
Una arquitectura Cliente-Servidor robusta basada en TCP Sockets que permite la ejecución de comandos remotos y la interacción con modelos de Inteligencia Artificial (Gemini API) manteniendo el estado de la sesión y el contexto de la conversación.

🏗️ Arquitectura del Sistema
La aplicación sigue un modelo de comunicación persistente de bajo nivel, permitiendo una latencia mínima y un control total sobre el flujo de datos sin la sobrecarga de protocolos de capa superior como HTTP.

Componentes Principales
Servidor (server.py):

Gestiona múltiples conexiones simultáneas mediante hilos (threading).

Implementa un sistema de identificación única mediante el hash SHA-256 de la IP del cliente.

Actúa como orquestador entre el cliente y la API de Gemini, gestionando el historial de mensajes para mantener el contexto.

Cliente (client.py):

Interfaz de línea de comandos (CLI) interactiva.

Maneja un sistema de estados dual: Modo Comando (gestión) y Modo IA (chat interactivo).

🛠️ Especificaciones Técnicas
Gestión de Identidad y Sesión
El servidor utiliza un diccionario global clients_connected para rastrear a los usuarios activos. Cada cliente es identificado por un hash único generado al momento de la conexión:

Python

def createId(ip_client):
    hash_object = hashlib.sha256(ip_client.encode('utf-8'))
    return hash_object.hexdigest()
Protocolo de Comandos
El sistema responde a comandos específicos antes de entrar en modo IA:

INFO: Devuelve detalles técnicos de la conexión actual (IP, puerto, ID, timestamp).

CHANGE-MODEL: Permite al usuario cambiar dinámicamente entre diferentes versiones de modelos (Gemini 2.5, 2.0, Flash, etc.) durante la sesión activa.

IA: Activa el puente de comunicación con el modelo de lenguaje.

Gestión de Contexto (IA)
A diferencia de las peticiones REST tradicionales, el servidor almacena un historial estructurado en chat_sessions. Esto permite que la IA "recuerde" los mensajes anteriores de la sesión actual, enviando el objeto history completo en cada interacción.

🚀 Flujo de Operación
Conexión: El cliente establece un túnel TCP con el servidor.

Handshake: El servidor registra al cliente y le asigna su ID único.

Interacción:

En Modo Comando, el servidor busca funciones mapeadas en el diccionario COMMANDS.

Al recibir el comando IA, el servidor entra en un bucle iaActivate, donde todo el tráfico se redirige al modelo de IA seleccionado.

Finalización: El comando BACK o EXIT cierra el flujo de IA o la conexión socket de forma segura, limpiando los registros del servidor.

📋 Requisitos e Instalación
Variables de Entorno: Configurar un archivo .env con:

GEMINI_API_KEY: Tu clave de Google AI.

PORT_SERVER: Puerto de escucha (ej. 65432).

IP_SERVER: IP del servidor (para el cliente).

Dependencias:

Bash

pip install google-genai python-dotenv
Ejecución:

Bash

# En la terminal del servidor
python server.py

# En la terminal del cliente
python client.py
