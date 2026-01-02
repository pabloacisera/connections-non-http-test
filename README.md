
# AI-Socket Terminal Bridge

Una arquitectura Cliente-Servidor de alto rendimiento basada en TCP Sockets que permite la interacción con modelos de Inteligencia Artificial (Gemini API) mediante una interfaz de línea de comandos, manteniendo persistencia dual en RAM/SQLite y soportando TLS para comunicaciones seguras.

---

## 🎯 ¿Para quién es esta aplicación?

### Casos de Uso Principales

**1. Desarrolladores Backend & DevOps**
- Integración de IA en scripts de automatización sin dependencias pesadas de HTTP
- Testing de modelos de lenguaje en entornos de producción con control total del socket
- Despliegue en servidores sin interfaz gráfica (headless servers)

**2. Investigadores & Data Scientists**
- Experimentación con diferentes modelos de Gemini sin cambiar código
- Análisis de latencia y throughput en comunicaciones de bajo nivel
- Prototipado rápido de agentes conversacionales con memoria persistente

**3. Administradores de Sistemas**
- Gestión remota de infraestructura con asistencia IA
- Logs y debugging en tiempo real con contexto histórico
- Alternativa ligera a interfaces web para servidores de producción

**4. Estudiantes & Educadores**
- Aprendizaje de arquitecturas cliente-servidor con casos reales
- Comprensión de protocolos de bajo nivel (TCP/IP, TLS)
- Implementación de sistemas con estado y gestión de sesiones

---

## 🏗️ Arquitectura del Sistema

### Modelo de Comunicación

```
┌─────────────┐         TCP Socket (TLS)          ┌─────────────┐
│   Cliente   │◄─────────────────────────────────►│  Servidor   │
│  (CLI)      │         Puerto 65432              │  (Python)   │
└─────────────┘                                    └──────┬──────┘
                                                          │
                                                          ▼
                                                   ┌──────────────┐
                                                   │ Gemini API   │
                                                   │ (Múltiples   │
                                                   │  Modelos)    │
                                                   └──────────────┘
```

### Componentes Principales

#### 1. **Servidor (`server.py`)**
- **Multithreading**: Gestión concurrente de múltiples clientes mediante `threading.Thread`
- **Identificación Única**: Hash SHA-256 de la IP del cliente como identificador inmutable
- **Orquestador IA**: Proxy entre cliente y Gemini API con gestión de historial
- **Seguridad TLS**: Soporte opcional de cifrado con certificados autofirmados
- **Persistencia Dual**: 
  - **Capa 1 (RAM)**: Diccionario `chat_sessions` para acceso ultra-rápido
  - **Capa 2 (SQLite)**: Tabla `messages` para persistencia entre reinicios

#### 2. **Cliente (`client.py`)**
- **CLI Interactiva**: Interfaz de comandos con efecto typewriter
- **Dual Mode**: 
  - **Modo Comando**: Gestión de conexión y configuración
  - **Modo IA**: Chat interactivo full-duplex con el modelo
- **TLS Automático**: Detección y aplicación de cifrado según `.env`

#### 3. **Sistema de Memoria (`memory_manage.py`)**
- **Resúmenes Automáticos**: Cuando la RAM excede 100MB, Gemini auto-resume la conversación
- **Contexto Histórico**: Recuperación de resúmenes previos al iniciar sesión
- **Límite de Resúmenes**: Mantiene últimos 50 resúmenes por cliente en SQLite

#### 4. **Gestión de Modelos (`models.py`)**
- **Caché de Modelos**: Evita peticiones redundantes a Gemini API (5 min TTL)
- **Filtrado Inteligente**: Excluye modelos de embedding, audio y video
- **Hot-Swapping**: Cambio de modelo sin reiniciar el servidor

---

## 🔐 Seguridad TLS

### Generación de Certificados Autofirmados

```bash
# Generar clave privada y certificado (válido 365 días)
openssl req -x509 -newkey rsa:4096 -keyout server.key -out server.crt \
  -days 365 -nodes -subj "/CN=localhost"
```

### Configuración en `.env`

```env
USE_TLS=true
SSL_CERTFILE=server.crt
SSL_KEYFILE=server.key
```

### Flujo de Handshake TLS

1. Cliente solicita conexión → `socket.connect()`
2. Servidor envuelve socket → `ssl_context.wrap_socket()`
3. Negociación de cipher suite (AES-256-GCM recomendado)
4. Verificación de certificado (deshabilitada en cliente para autofirmados)
5. Canal cifrado establecido ✅

---

## 📊 Persistencia de Datos

### Esquema de Base de Datos (SQLite)

```sql
-- Mensajes individuales
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- 'user' | 'model'
    content TEXT NOT NULL,
    timestamp DATETIME NOT NULL
);

-- Resúmenes de conversaciones
CREATE TABLE summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL,
    summary_text TEXT NOT NULL,
    created_at DATETIME NOT NULL
);
```

### Estrategia de Memoria

```python
# Capa 1: RAM (acceso O(1))
chat_sessions[client_id] = {
    "messages": [
        {"role": "user", "content": "...", "timestamp": datetime},
        {"role": "model", "content": "...", "timestamp": datetime}
    ]
}

# Capa 2: SQLite (persistencia)
save_message(client_id, role, content)  # Ejecuta INSERT asíncrono
```

### Control de Tamaño

- **Límite RAM**: 100 MB por sesión
- **Acción al exceder**: Auto-resumen vía Gemini + limpieza de RAM + guardado en SQLite
- **Prompt de resumen**:
```python
"Actúa como un gestor de memoria. Resume de forma técnica y concisa 
esta conversación para que pueda ser retomada en el futuro sin perder 
información clave..."
```

---

## 🎮 Protocolo de Comandos

### Comandos Disponibles

| Comando | Descripción | Respuesta |
|---------|-------------|-----------|
| `INFO` | Detalles de conexión | `ID: abc123... \| IP: 192.168.1.10 \| Puerto: 54321 \| Conectado: 14:30:25` |
| `LIST-MODELS` | Modelos disponibles | Lista numerada + modelo actual |
| `CHANGE-MODEL` | Cambiar modelo activo | Menú interactivo → Confirmación |
| `IA` | Activar modo chat | Entra en bucle IA |
| `EXIT` / `QUIT` | Desconectar | Cierra socket |

### Flujo de Cambio de Modelo

```
Cliente: CHANGE-MODEL
Servidor: [Envía menú con 15 modelos]
Cliente: 3
Servidor: ✅ Modelo cambiado a: gemini-2.0-flash-exp
         [Limpia historial de RAM]
```

---

## 🚀 Instalación y Uso

### Requisitos

```bash
# Python 3.8+
pip install -r requirements.txt
```

**Dependencias principales**:
- `google-genai==1.56.0` - SDK oficial de Gemini
- `python-dotenv==1.2.1` - Gestión de variables de entorno
- `pyOpenSSL==25.3.0` - Soporte TLS

### Configuración

**Archivo `.env`**:
```env
IP_SERVER=192.168.1.10
PORT_SERVER=65432
GEMINI_API_KEY=AIzaSy...  # Tu API key de Google AI Studio

# Seguridad
USE_TLS=true
SSL_CERTFILE=server.crt
SSL_KEYFILE=server.key

# Base de Datos
DB_PATH=ai_bridge.db
```

### Ejecución

```bash
# Terminal 1: Servidor
python server.py
# [SYSTEM] Iniciando servidor en 192.168.1.10:65432
# [SYSTEM] TLS: HABILITADO
# [SYSTEM] 12 modelos cargados
# [SYSTEM] Escuchando conexiones...

# Terminal 2: Cliente
python client.py
# [CLIENT] Conectando a 192.168.1.10:65432...
# [CLIENT] Conexión TLS establecida
# [SERVER] ID:a3f8b2e1... | Conectado a 192.168.1.10:65432
```

### Ejemplo de Sesión

```
Comando > LIST-MODELS

=== MODELOS DISPONIBLES ===
  1. gemini-2.0-flash
  2. gemini-2.0-flash-exp
  3. gemini-2.5-flash
  4. gemini-pro
...
📌 Modelo actual: gemini-2.0-flash

Comando > IA
[SERVER] Modo IA activado. Escribe 'back' para salir.

IA > Explica qué es un socket TCP en 50 palabras
============================================================
Un socket TCP es una abstracción de software que representa
un punto final de comunicación bidireccional entre dos 
procesos en una red. Utiliza el protocolo TCP para garantizar
entrega ordenada y sin errores mediante handshakes, números
de secuencia y acknowledgements.
============================================================

IA > back
[SERVER] Saliendo del modo IA...
```

---

## 🔧 Especificaciones Técnicas

### Gestión de Identidad

```python
def create_client_id(ip_address):
    """Genera ID único basado en SHA-256 de la IP"""
    return hashlib.sha256(ip_address.encode()).hexdigest()
```

**Ventajas**:
- Inmutable durante la sesión
- Sin colisiones (probabilidad < 1e-60)
- No requiere base de datos para generación

### Gestión de Contexto IA

```python
# Preparar historial para Gemini API
gemini_history = []
for msg in chat_sessions[client_id]["messages"]:
    gemini_history.append(
        types.Content(
            role=msg["role"], 
            parts=[types.Part(text=msg["content"])]
        )
    )

# Enviar con contexto completo
chat = gemini_client.chats.create(
    model=f"models/{current_model}",
    history=gemini_history
)
response = chat.send_message(user_input)
```

### Manejo de Errores

```python
try:
    sock.settimeout(30)  # Timeout de 30 segundos
    sock.connect((IP_SERVER, PORT_SERVER))
except ConnectionRefusedError:
    print("[ERROR] Servidor no disponible")
except socket.timeout:
    print("[ERROR] Timeout de conexión")
except ssl.SSLError as e:
    print(f"[ERROR] Fallo TLS: {e}")
```

---

## 📈 Ventajas sobre REST/HTTP

| Aspecto | TCP Socket (Este Proyecto) | REST API |
|---------|---------------------------|----------|
| **Latencia** | ~5-10ms (conexión persistente) | ~50-100ms (handshake por request) |
| **Overhead** | Mínimo (raw bytes) | Headers HTTP (~200-500 bytes/request) |
| **Estado** | Nativo (socket abierto) | Stateless (requiere tokens/cookies) |
| **Streaming** | Full-duplex nativo | Requiere SSE/WebSockets |
| **Memoria** | Control total (RAM + SQLite) | Depende del framework |

---

## 🛠️ Estructura del Proyecto

```
ai-socket-bridge/
├── server.py              # Servidor principal
├── client.py              # Cliente CLI
├── requirements.txt       # Dependencias Python
├── .env                   # Variables de entorno
├── server.crt             # Certificado TLS
├── server.key             # Clave privada TLS
├── ai_bridge.db           # Base de datos SQLite
├── core/
│   ├── security.py        # Manejo TLS
│   ├── models.py          # Gestión de modelos Gemini
│   └── commands.py        # Comandos del cliente
├── helpers/
│   └── memory_manage.py   # Sistema de memoria
└── database/
    └── database.py        # Inicialización SQLite
```

---

## 🤝 Contribuciones

Las mejoras sugeridas incluyen:
- Implementación de autenticación JWT sobre TLS
- Soporte para múltiples APIs (OpenAI, Claude, etc.)
- Dashboard web opcional para monitoreo
- Exportación de conversaciones a Markdown/JSON

---

## 📜 Licencia

Este proyecto es de código abierto. Consulta el archivo `LICENSE` para más detalles.

---

## 🔗 Enlaces Útiles

- [Documentación Gemini API](https://ai.google.dev/gemini-api/docs)
- [Python Socket Programming](https://docs.python.org/3/library/socket.html)
- [OpenSSL Certificate Generation](https://www.openssl.org/docs/man1.1.1/man1/req.html)

---

**Versión**: 0.2.0  
**Última actualización**: Enero 2026  
**Mantenedor**: testdeveloperrandom@gmail.com
