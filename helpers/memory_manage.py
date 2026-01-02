import os
import sys
import datetime
from database.database import get_connection

def save_message(client_id, role, content):
    """ Persistencia real en SQLite """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (client_id, role, content, timestamp) VALUES (?, ?, ?, ?)", 
                (client_id, role, content, datetime.datetime.now())
            )
            conn.commit()
    except Exception as e:
        print(f"[ERROR-DB]: No se pudo guardar el mensaje: {e}")

def get_last_summaries(client_id):
    """ Recupera contexto histórico (Capa 3) """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            # CORRECCIÓN: Se agregó el "=" faltante después de client_id
            cursor.execute(
                "SELECT summary_text FROM summaries WHERE client_id = ? ORDER BY created_at DESC LIMIT 1", 
                (client_id,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        print(f"[ERROR-DB]: Error al recuperar resumen: {e}")
        return None
    
def get_size(obj, seen=None):
    """ Calcula el tamaño real en bytes de un objeto y sus contenidos """
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__dict__'):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    return size
    
def ai_self_summarize(client_id, messages_list, genai_client, model_selected):
    """ Gemini resume la conversación y guarda en DB """
    if not messages_list: return None

    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages_list])

    prompt_instruction = (
        "Actúa como un gestor de memoria. Resume de forma técnica y concisa esta conversación "
        "para que pueda ser retomada en el futuro sin perder información clave:\n\n"
        f"{history_text}"
    )

    try:
        response = genai_client.models.generate_content(
            model=model_selected,
            contents=prompt_instruction
        )
        summary_result = response.text

        with get_connection() as conn:
            cursor = conn.cursor()
            # Guardar nuevo resumen
            cursor.execute(
                "INSERT INTO summaries (client_id, summary_text, created_at) VALUES (?, ?, ?)", 
                (client_id, summary_result, datetime.datetime.now())
            )
            # Mantener solo los últimos 50
            cursor.execute(''' 
                DELETE FROM summaries 
                WHERE client_id = ? AND id NOT IN (
                    SELECT id FROM summaries WHERE client_id = ? ORDER BY created_at DESC LIMIT 50
                ) 
            ''', (client_id, client_id))
            conn.commit()
        return summary_result
    except Exception as e:
        print(f"[ERROR-IA]: Error en auto-resumen: {e}")
        return None