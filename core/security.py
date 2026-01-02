# core/security.py
"""
Manejo de seguridad y encriptación TLS
"""
import ssl
import os

def create_ssl_context():
    """Crea contexto SSL para servidor seguro"""
    certfile = os.getenv("SSL_CERTFILE", "server.crt")
    keyfile = os.getenv("SSL_KEYFILE", "server.key")
    
    if not os.path.exists(certfile) or not os.path.exists(keyfile):
        print(f"[ERROR]: Certificados no encontrados: {certfile}, {keyfile}")
        return None
    
    try:
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=certfile, keyfile=keyfile)
        print(f"[SECURITY]: Contexto TLS creado con {certfile}")
        return context
    except Exception as e:
        print(f"[ERROR]: Fallo al crear contexto SSL: {e}")
        return None

def wrap_client_socket(sock, server_hostname):
    """Envuelve socket cliente con TLS"""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    try:
        return context.wrap_socket(sock, server_hostname=server_hostname)
    except Exception as e:
        print(f"[ERROR]: Fallo al envolver socket cliente: {e}")
        return sock