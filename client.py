import socket
import sys

ip_server = '127.0.0.1' 
port = 65432

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip_server, port))
        
        # 1. Recibir confirmación de registro e ID
        id_data = s.recv(1024).decode()
        print(f"[*] Conectado al servidor.")
        print(f"[*] {id_data}")
        print("-" * 30)

        # 2. Bucle infinito de comandos
        while True:
            # Pedir entrada al usuario
            cmd = input("Comando > ").strip()

            if not cmd:
                continue

            # Lógica de salida manual
            if cmd.lower() in ['out', 'exit', 'quit']:
                print("[!] Cerrando conexión...")
                break

            # Enviar el comando al servidor
            s.sendall(cmd.encode('utf-8'))
            
            # Recibir y mostrar la respuesta
            respuesta = s.recv(4096).decode('utf-8') # Buffer más grande para el INFO
            print(f"\n{respuesta}\n")

except ConnectionRefusedError:
    print("[ERROR] No se pudo conectar. ¿Está el servidor encendido?")
except KeyboardInterrupt:
    print("\n[!] Saliendo (Ctrl+C)...")
except Exception as e:
    print(f"[ERROR] Inesperado: {e}")

print("[*] Desconectado.")