# client.py - ACTUALIZADO
import socket
import ssl
import time
import os
from dotenv import load_dotenv
from core.security import wrap_client_socket

load_dotenv()

IP_SERVER = os.getenv("IP_SERVER", "localhost")
PORT_SERVER = int(os.getenv("PORT_SERVER", 65432))
USE_TLS = os.getenv("USE_TLS", "true").lower() == "true"

def typewriter_print(text, delay=0.001):
    """Imprime con efecto máquina de escribir"""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def main():
    try:
        print(f"[CLIENT] Conectando a {IP_SERVER}:{PORT_SERVER}...")
        
        # Crear socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        
        # Aplicar TLS si está configurado
        if USE_TLS:
            sock = wrap_client_socket(sock, IP_SERVER)
            print("[CLIENT] Conexión TLS establecida")
        
        # Conectar
        sock.connect((IP_SERVER, PORT_SERVER))
        
        # Recibir ID
        welcome = sock.recv(1024).decode()
        typewriter_print(f"[SERVER] {welcome}", 0.01)
        print("-" * 40)
        
        # Bucle principal
        while True:
            cmd = input("\nComando > ").strip()
            
            if not cmd:
                continue
            
            if cmd.lower() in ['exit', 'quit', 'salir']:
                print("[CLIENT] Desconectando...")
                break
            
            # Enviar comando
            sock.sendall(cmd.encode())
            
            # Recibir respuesta
            response = sock.recv(4096).decode()
            
            # Modo IA
            if response == "ia-activate":
                typewriter_print("[SERVER] Modo IA activado. Escribe 'back' para salir.", 0.01)
                
                while True:
                    user_input = input("IA > ").strip()
                    
                    if user_input.lower() in ['back', 'salir']:
                        sock.sendall(b"ia-deactivate")
                        typewriter_print("[SERVER] Saliendo del modo IA...", 0.01)
                        break
                    
                    sock.sendall(user_input.encode())
                    ai_response = sock.recv(8192).decode()
                    
                    print("\n" + "=" * 60)
                    typewriter_print(ai_response, 0.001)
                    print("=" * 60 + "\n")
            else:
                # Respuesta normal
                print("\n" + "=" * 60)
                typewriter_print(response, 0.01)
                print("=" * 60)
                
    except ConnectionRefusedError:
        print("[ERROR] No se pudo conectar. Verifica que el servidor esté ejecutándose.")
    except socket.timeout:
        print("[ERROR] Timeout de conexión")
    except KeyboardInterrupt:
        print("\n[CLIENT] Desconectado por usuario")
    except Exception as e:
        print(f"[ERROR] {e}")
    
    print("[CLIENT] Conexión cerrada")

if __name__ == "__main__":
    main()