import socket
import sys
import os
from dotenv import load_dotenv

load_dotenv()

ip_server = os.getenv("IP_SERVER")
server_port = int(os.getenv("PORT_SERVER", 65432))

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip_server, server_port))
        
        # 1. Recibir confirmación de registro e ID
        id_data = s.recv(1024).decode()
        print(f"[SYSTEM]: Conectado al servidor.")
        print(f"[SYSTEM]: {id_data}")
        print("-" * 30)

        # 2. Bucle infinito de comandos
        while True:
            # Pedir entrada al usuario
            cmd = input("Comando > ").strip()

            if not cmd:
                continue

            # Lógica de salida manual
            if cmd.lower() in ['out', 'exit', 'quit']:
                print("[SYSTEM]: Cerrando conexión...")
                break

            # Enviar el comando al servidor
            s.sendall(cmd.encode('utf-8'))
            
            # Recibir y mostrar la respuesta
            response = s.recv(4096).decode('utf-8') # Buffer más grande para el INFO

            # --- Lógica de Activación de IA ---
            if response == 'ia-activate':
                print("[SYSTEM]: Modo IA activado. Escribe 'back' para salir del modo consulta.")
                
                while True:
                    pregunta = input("IA > ").strip()
                    
                    if not pregunta:
                        continue
                    
                    # Opción para salir del modo IA y volver a comandos normales
                    if pregunta.lower() in ['back', 'exit']:
                        s.sendall(b'ia-deactivate') # Avisamos al servidor si es necesario
                        print("[SYSTEM]: Volviendo a modo comando...")
                        break
                    
                    s.sendall(pregunta.encode('utf-8'))
                    res_ia = s.recv(4096).decode('utf-8')
                    print(f"\n{res_ia}\n")
            else:
                # Respuesta normal del servidor
                print(f"\n{response}\n")

except ConnectionRefusedError:
    print("[ERROR] No se pudo conectar. ¿Está el servidor encendido?")
except KeyboardInterrupt:
    print("\n[!] Saliendo (Ctrl+C)...")
except Exception as e:
    print(f"[ERROR] Inesperado: {e}")

print("[*] Desconectado.")