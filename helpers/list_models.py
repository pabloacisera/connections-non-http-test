# list_models.py
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")

if not gemini_api_key:
    print("[ERROR]: No se encontró GEMINI_API_KEY en el archivo .env")
    print("Asegúrate de tener un archivo .env con: GEMINI_API_KEY=tu_clave_aqui")
    exit(1)

print("=" * 80)
print("LISTANDO MODELOS DISPONIBLES:")
print("=" * 80)

try:
    # Cliente sin forzar versión específica
    client = genai.Client(api_key=gemini_api_key)
    
    # Obtener todos los modelos
    models = client.models.list()
    
    model_count = 0
    for model in models:
        model_count += 1
        print(f"\n{model_count}. Nombre: {model.name}")
        
        # Extraer nombre corto
        if "models/" in model.name:
            short_name = model.name.split("models/")[1]
            print(f"   Nombre corto: {short_name}")
        
        # Mostrar métodos soportados
        if hasattr(model, 'supported_generation_methods'):
            methods = model.supported_generation_methods
            print(f"   Métodos: {', '.join(methods)}")
            
            # Verificar si soporta generateContent (importante para chat)
            if 'generateContent' in methods:
                print(f"   ✓ Soportado para chat")
    
    print(f"\n" + "=" * 80)
    print(f"TOTAL: {model_count} modelos encontrados")
    
except Exception as e:
    print(f"[ERROR]: {e}")