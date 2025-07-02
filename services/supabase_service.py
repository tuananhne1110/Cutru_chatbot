import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_config import supabase
import json
from datetime import datetime

def save_chat_message(session_id, question, answer, sources):
    data = {
        "session_id": session_id,
        "question": question,
        "answer": answer,
        "sources": json.dumps(sources, ensure_ascii=False),
        "created_at": datetime.now().isoformat()
    }
    result = supabase.table("chat_messages").insert(data).execute()
    return result.data[0] if result.data else None

def get_chat_history(session_id, limit=50):
    result = supabase.table("chat_messages")\
        .select("*")\
        .eq("session_id", session_id)\
        .order("created_at", desc=True)\
        .limit(limit)\
        .execute()
    messages = []
    for msg in result.data:
        msg_copy = msg.copy()
        if msg_copy.get('sources'):
            try:
                msg_copy['sources'] = json.loads(msg_copy['sources'])
            except:
                msg_copy['sources'] = []
        messages.append(msg_copy)
    return messages

def create_chat_session(session_id, user_info=None):
    data = {
        "session_id": session_id,
        "user_info": json.dumps(user_info or {}, ensure_ascii=False),
        "created_at": datetime.now().isoformat(),
        "status": "active"
    }
    result = supabase.table("chat_sessions").insert(data).execute()
    return result.data[0] if result.data else None

def search_laws_by_category(query=None, limit=5):
    """
    Tìm kiếm trong bảng laws với category = 'law'
    """
    try:
        query_builder = supabase.table("laws").select("*").eq("category", "law")
        
        if query:
            query_builder = query_builder.text_search("law_name", query)
        
        result = query_builder.limit(limit).execute()
        return result.data
    except Exception as e:
        print(f"Lỗi khi search laws: {e}")
        return []

def search_form_guidance_by_category(query=None, limit=5):
    """
    Tìm kiếm trong bảng form_guidance với category = 'form'
    """
    try:
        query_builder = supabase.table("form_guidance").select("*").eq("category", "form")
        
        if query:
            query_builder = query_builder.text_search("content", query)
        
        result = query_builder.limit(limit).execute()
        return result.data
    except Exception as e:
        print(f"Lỗi khi search form guidance: {e}")
        return []

def get_law_chunks(law_code=None, law_name=None, limit=5):
    """
    Lấy law records với filter tùy chọn
    """
    try:
        query = supabase.table("laws").select("*").eq("category", "law")
        
        if law_code:
            query = query.eq("law_code", law_code)
        if law_name:
            query = query.ilike("law_name", f"%{law_name}%")
        
        result = query.limit(limit).execute()
        return result.data
    except Exception as e:
        print(f"Lỗi khi get law records: {e}")
        return []

def get_form_chunks(form_code=None, form_name=None, chunk_type=None, limit=5):
    """
    Lấy form guidance records với filter tùy chọn
    """
    try:
        query = supabase.table("form_guidance").select("*").eq("category", "form")
        
        if form_code:
            query = query.eq("form_code", form_code)
        if form_name:
            query = query.ilike("form_name", f"%{form_name}%")
        if chunk_type:
            query = query.eq("chunk_type", chunk_type)
        
        result = query.limit(limit).execute()
        return result.data
    except Exception as e:
        print(f"Lỗi khi get form guidance records: {e}")
        return []

