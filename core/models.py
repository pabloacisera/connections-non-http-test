# core/models.py
"""
Gestión de modelos de Gemini API
"""
import time

class ModelManager:
    """Gestiona modelos disponibles con cache"""
    
    def __init__(self, gemini_client):
        self.client = gemini_client
        self.cache = None
        self.cache_timestamp = 0
        self.CACHE_DURATION = 300  # 5 minutos
        
    def get_available_models(self, use_cache=True):
        """Obtiene lista de modelos para chat"""
        if not self.client:
            return []
        
        if use_cache and self.cache and (time.time() - self.cache_timestamp < self.CACHE_DURATION):
            return self.cache
        
        try:
            all_models = list(self.client.models.list())
            chat_models = []
            
            for model in all_models:
                model_name = model.name.replace("models/", "")
                
                # Filtrar modelos no-chat
                excluded = ['embedding', 'embed', 'audio', 'video', 'vision', 'veo']
                if any(excl in model_name.lower() for excl in excluded):
                    continue
                
                if any(keyword in model_name.lower() for keyword in ['gemini', 'gemma', 'chat', 'text']):
                    chat_models.append(model_name)
            
            chat_models.sort()
            self.cache = chat_models
            self.cache_timestamp = time.time()
            
            print(f"[MODELS]: {len(chat_models)} modelos disponibles")
            return chat_models
            
        except Exception as e:
            print(f"[ERROR-MODELS]: {e}")
            return self.cache or []