import os
import sys
import datetime
from database.database import get_connection

def save_message(client_id, role, content):
    """ persistencia real en sqlite """
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("INSERT INTO messages (client_id, role, content, timestamp) VALUES(?, ?, ?, ?)", (client_id, role, content, datetime.datetime.now()))

        conn.commit()

def get_last_summaries(client_id):
    """ recupera contexto historico """
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT summary_text FROM summaries WHERE client_id ? ORDER BY created_at DESC LIMIT 1", (client_id,))

        row = cursor.fetchone()

        return row[0] if row else None
    
def get_size(obj, seen=None):
    """Calcula el tamaño real en bytes de un objeto y sus contenidos (recursivo)."""
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
    """ gemini resume los puntos principales de la conversacion guuardada en ram y si corresponde la limpia"""

    if not messages_list: return

    # verificar el limite de ram de 100mb
    current_ram = get_size(messages_list)
    if current_ram > 104857600:
        print(f"[ALERT]: Memoria excedida. RAM: {current_ram} bytes. Forzando auto-resumen")

    # convertir historial a texto para procesarlo
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages_list])

    prompt_instruction = (
        "Actúa como un gestor de memoria. Resume de forma tecnica y concisa esta conversación para que pueda ser retomada en el futuro sin perder información clave o contexto"
        f"\n\n{history_text}"
    )

    # la ia se resume a si misma
    try:
        response = genai_client.models.generate_content(
            model = model_selected,
            contents = prompt_instruction
        )

        summary_result = response.text

        # guardar con limite de 50 por client_id
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("INSERT INTO summaries (client_id, summary_text, created_at) VALUES(?, ?, ?)", (client_id, summary_result, datetime.datetime.now()))

            # limpieza de registros antiguos, mantemos los ultimo 50
            cursor.execute(''' DELETE FROM summaries WHERE client_id = ? AND id NOT IN (SELECT id FROM summaries WHERE client_id = ? ORDER BY created_at DESC LIMIT 50) ''', (client_id, client_id))

            conn.commit()
        return summary_result
    except Exception as e:
        print(f"[ERROR]: into summary: {e}")
        return None

