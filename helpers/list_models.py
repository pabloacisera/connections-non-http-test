# list_models.py
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")

def get_available_models(client=None):
    """
    Retorna lista de modelos disponibles para chat.
    
    Args:
        client: Opcional, cliente de genai ya configurado
    
    Returns:
        list: Lista de nombres cortos de modelos para chat
    """
    if not gemini_api_key and not client:
        return []
    
    try:
        # Usar cliente existente o crear uno nuevo
        if not client:
            client = genai.Client(api_key=gemini_api_key)
        
        # Obtener todos los modelos
        models = client.models.list()
        
        chat_models = []
        for model in models:
            # Verificar si soporta generateContent
            if hasattr(model, 'supported_generation_methods'):
                if 'generateContent' in model.supported_generation_methods:
                    short_name = model.name.replace("models/", "")
                    chat_models.append(short_name)
        
        # Ordenar alfabéticamente
        chat_models.sort()
        return chat_models
        
    except Exception as e:
        print(f"[ERROR list_models]: {e}")
        return []

def list_all_models_formatted(client=None):
    """
    Retorna string formateado con todos los modelos para chat.
    """
    models = get_available_models(client)
    
    if not models:
        return "No se encontraron modelos disponibles para chat."
    
    result = "\n=== MODELOS DISPONIBLES PARA CHAT ===\n"
    for i, model_name in enumerate(models, 1):
        result += f"{i:3}. {model_name}\n"
    
    result += f"\nTotal: {len(models)} modelos disponibles\n"
    return result

if __name__ == "__main__":
    # Solo para pruebas directas
    print("=" * 80)
    print("LISTANDO MODELOS DISPONIBLES:")
    print("=" * 80)
    
    models_list = get_available_models()
    if models_list:
        for i, model_name in enumerate(models_list, 1):
            print(f"{i:3}. {model_name}")
        print(f"\nTotal: {len(models_list)} modelos")
    else:
        print("No se encontraron modelos disponibles.")