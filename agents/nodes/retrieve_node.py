import time
import asyncio
import logging
from typing import List, Dict, Any
from langchain_core.documents import Document
from agents.utils.intent_detector import intent_detector, IntentType
from agents.state import ChatState
from services.embedding import get_embedding
from services.qdrant_service import search_qdrant, search_qdrant_by_parent_id, search_qdrant_by_id
from services.reranker_service import get_reranker
from langfuse.decorators import observe

logger = logging.getLogger(__name__)

@observe()
async def retrieve_context(state: ChatState) -> ChatState:
    start_time = time.time()
    
    # Kiểm tra nếu đã có error từ guardrails
    if state.get("error") == "input_validation_failed":
        logger.info(f"[Retrieve] Skipping retrieval due to guardrails error")
        state["processing_time"]["context_retrieval"] = time.time() - start_time
        return state
    
    query = state.get("rewritten_query") or state["question"] or ""
    # Nếu query quá ngắn hoặc là follow-up, nối với câu hỏi trước
    if len(query.split()) < 6 and len(state["messages"]) > 1:
        # Tìm câu hỏi gần nhất của user trước đó
        prev_user_msg = None
        for m in reversed(state["messages"][:-1]):
            if hasattr(m, 'type') and getattr(m, 'type', None) == 'human':
                prev_user_msg = m.content
                break
            elif isinstance(m, dict) and m.get('role') == 'user':
                prev_user_msg = m.get('content', '')
                break
        if prev_user_msg:
            query = prev_user_msg.strip() + ' ' + query.strip()
            logger.info(f"[Retrieve] Follow-up detected, merged query: {query}")
    all_intents = state.get("all_intents", [])
    primary_intent = state["intent"]
    # KHÔNG tạo trace mới ở đây nữa, chỉ tạo trace root ở node generate_answer
    if primary_intent is None:
        logger.error("[Retrieve] Intent is None. State: %s", state)
        raise ValueError("Intent must not be None in retrieve_context")
    all_collections = set()
    for intent, confidence in all_intents:
        if confidence > 0.1:  # Chỉ xét intent có confidence > 10%
            if intent == IntentType.LAW:
                all_collections.add("legal_chunks")
            elif intent == IntentType.FORM:
                all_collections.add("form_chunks")
            elif intent == IntentType.TERM:
                all_collections.add("term_chunks")
            elif intent == IntentType.PROCEDURE:
                all_collections.add("procedure_chunks")
            elif intent == IntentType.GENERAL:
                all_collections.add("general_chunks")
    collections = list(all_collections)
    logger.info(f"[Retrieve] Collections to search (from all intents): {collections}")
    if not collections:
        logger.warning("[Retrieve] No collections found for intents")
        state["context_docs"] = []
        state["processing_time"]["context_retrieval"] = time.time() - start_time
        return state
    loop = asyncio.get_running_loop()
    embedding = await loop.run_in_executor(None, get_embedding, query)
    logger.info(f"[Retrieve] Getting embedding for query: {query}")
    all_docs = []
    for collection in collections:
        try:
            results = await loop.run_in_executor(None, search_qdrant, collection, embedding, 30)
            logger.info(f"[Retrieve] Found {len(results)} docs in {collection}")
            for r in results:
                if hasattr(r, 'payload') and r.payload:
                    content = r.payload.get("content") or r.payload.get("text", "")
                    all_docs.append(Document(page_content=content, metadata=r.payload))
                elif isinstance(r, dict):
                    content = r.get("content") or r.get("text", "")
                    all_docs.append(Document(page_content=content, metadata=r))
        except Exception as e:
            logger.warning(f"[Retrieve] Skipping collection: {collection}")
            continue
    logger.info(f"[Retrieve] Total docs before rerank: {len(all_docs)}")
    if all_docs:
        reranker = get_reranker()
        logger.info(f"[Retrieve] Running reranker on {len(all_docs)} docs")
        reranked_docs = await loop.run_in_executor(None, reranker.rerank, query or "", [{"content": doc.page_content} for doc in all_docs], 30)
        for i, doc in enumerate(all_docs[:len(reranked_docs)]):
            doc.metadata["rerank_score"] = reranked_docs[i].get("rerank_score", 0.0)
        logger.info(f"[Retrieve] Rerank completed. Top rerank score: {reranked_docs[0].get('rerank_score', 0.0) if reranked_docs else 'N/A'}")
    if primary_intent == IntentType.LAW:
        logger.info("[Retrieve] LAW intent detected - starting parent_id grouping and expansion...")
        expanded_docs = await _expand_law_chunks_with_structure(all_docs, collections, loop)
        logger.info(f"[Retrieve] After expansion: {len(expanded_docs)} law docs")
        merged_docs = _group_law_chunks_tree(expanded_docs)
        logger.info(f"[Retrieve] Merged law docs: {len(merged_docs)}")
        state["context_docs"] = merged_docs[:20]
    else:
        state["context_docs"] = all_docs[:30]
    logger.info(f"[Retrieve] Retrieval completed: {len(state['context_docs'])} docs")
    duration = time.time() - start_time
    state["processing_time"]["context_retrieval"] = duration
    logger.info(f"[Retrieve] Retrieval time: {duration:.4f}s")
    return state

async def _expand_law_chunks_with_structure(semantic_docs: List[Document], collections: list, loop) -> List[Document]:
    logger.info(f"[Retrieve] _expand_law_chunks_with_structure: {len(semantic_docs)} semantic docs, collections: {collections}")
    id_to_doc = {doc.metadata.get("id"): doc for doc in semantic_docs if doc.metadata.get("id")}
    parent_ids_needed = set()
    for doc in semantic_docs:
        doc_id = doc.metadata.get("id")
        parent_id = doc.metadata.get("parent_id")
        doc_type = doc.metadata.get("type")
        if doc_type in ["điểm", "khoản"] and parent_id:
            parent_ids_needed.add(parent_id)
    # Truy vấn mở rộng parent_id cho điểm/khoản (ra khoản/điều)
    expansion_docs = []
    for parent_id in parent_ids_needed:
        for collection in collections:
            results_list = search_qdrant_by_parent_id(collection, parent_id, 30)
            logger.info(f"[Retrieve] Found {len(results_list)} expansion docs for parent_id {parent_id} in {collection}")
            for r in results_list:
                if hasattr(r, 'payload') and r.payload:
                    content = r.payload.get("content") or r.payload.get("text", "")
                    expansion_docs.append(Document(page_content=content, metadata=r.payload))
                elif isinstance(r, dict):
                    content = r.get("content") or r.get("text", "")
                    expansion_docs.append(Document(page_content=content, metadata=r))
    # Bổ sung: Nếu có khoản, lấy parent_id của khoản (ra điều), truy vấn thêm các điều cha
    khoan_docs = [doc for doc in semantic_docs + expansion_docs if doc.metadata.get("type") == "khoản"]
    dieu_ids = set(doc.metadata.get("parent_id") for doc in khoan_docs if doc.metadata.get("parent_id"))
    dieu_expansion_docs = []
    for dieu_id in dieu_ids:
        for collection in collections:
            # Truy vấn theo id (not parent_id) để lấy đúng điều
            results_list = search_qdrant_by_id(collection, dieu_id, 1)
            logger.info(f"[Retrieve] Found {len(results_list)} expansion docs for dieu_id {dieu_id} in {collection}")
            for r in results_list:
                if hasattr(r, 'payload') and r.payload:
                    content = r.payload.get("content") or r.payload.get("text", "")
                    dieu_expansion_docs.append(Document(page_content=content, metadata=r.payload))
                elif isinstance(r, dict):
                    content = r.get("content") or r.get("text", "")
                    dieu_expansion_docs.append(Document(page_content=content, metadata=r))
            # BỔ SUNG: Lấy tất cả các khoản có parent_id = dieu_id (các khoản khác cùng điều)
            all_khoan_results = search_qdrant_by_parent_id(collection, dieu_id, 50)  # Tăng limit để lấy hết
            logger.info(f"[Retrieve] Found {len(all_khoan_results)} khoản docs for dieu_id {dieu_id} in {collection}")
            for r in all_khoan_results:
                if hasattr(r, 'payload') and r.payload:
                    content = r.payload.get("content") or r.payload.get("text", "")
                    dieu_expansion_docs.append(Document(page_content=content, metadata=r.payload))
                elif isinstance(r, dict):
                    content = r.get("content") or r.get("text", "")
                    dieu_expansion_docs.append(Document(page_content=content, metadata=r))
            # BỔ SUNG: Với mỗi khoản, lấy tất cả điểm con
            for r in all_khoan_results:
                khoan_id = r.payload.get("id") if hasattr(r, 'payload') and r.payload else r.get("id")
                if khoan_id:
                    diem_results = search_qdrant_by_parent_id(collection, khoan_id, 30)
                    logger.info(f"[Retrieve] Found {len(diem_results)} điểm docs for khoan_id {khoan_id} in {collection}")
                    for diem_r in diem_results:
                        if hasattr(diem_r, 'payload') and diem_r.payload:
                            content = diem_r.payload.get("content") or diem_r.payload.get("text", "")
                            dieu_expansion_docs.append(Document(page_content=content, metadata=diem_r.payload))
                        elif isinstance(diem_r, dict):
                            content = diem_r.get("content") or diem_r.get("text", "")
                            dieu_expansion_docs.append(Document(page_content=content, metadata=diem_r))
    all_docs = {doc.metadata.get("id"): doc for doc in semantic_docs + expansion_docs + dieu_expansion_docs if doc.metadata.get("id")}
    logger.info(f"[Retrieve] Law chunk expansion: semantic={len(semantic_docs)}, expanded={len(expansion_docs)}, dieu_expanded={len(dieu_expansion_docs)}, total={len(all_docs)}")
    return list(all_docs.values())

def _group_law_chunks_tree(all_docs: List[Document]) -> List[Document]:
    """Nhóm các đoạn luật thành cây Điều → Khoản → Điểm, trả về list Document đã merge theo đúng cấu trúc pháp lý."""
    import logging
    logger = logging.getLogger("agents.nodes.retrieve_node")
    logger.info(f"[MergeLaw] Tổng số doc đầu vào: {len(all_docs)}")
    n_diem = sum(1 for doc in all_docs if doc.metadata.get("type") == "điểm")
    n_khoan = sum(1 for doc in all_docs if doc.metadata.get("type") == "khoản")
    n_dieu = sum(1 for doc in all_docs if doc.metadata.get("type") == "điều")
    logger.info(f"[MergeLaw] Số điều: {n_dieu}, số khoản: {n_khoan}, số điểm: {n_diem}")
    # Bước 1: Tạo index theo id
    id_to_doc = {doc.metadata.get("id"): doc for doc in all_docs if doc.metadata.get("id")}
    # Bước 2: Gom nhóm các điểm vào khoản cha
    clause_id_to_points = {}
    for doc in all_docs:
        meta = doc.metadata
        if meta.get("type") == "điểm":
            parent_id = meta.get("parent_id")
            if parent_id:
                clause_id_to_points.setdefault(parent_id, []).append(doc)
    logger.info(f"[MergeLaw] Số khoản có điểm: {len(clause_id_to_points)}")
    # Bước 3: Gom nhóm các khoản vào điều cha, kèm các điểm con
    article_id_to_clauses = {}
    for doc in all_docs:
        meta = doc.metadata
        if meta.get("type") == "khoản":
            parent_id = meta.get("parent_id")
            if parent_id:
                # Gắn các điểm con vào khoản này
                points = clause_id_to_points.get(meta.get("id"), [])
                doc_points = sorted(points, key=lambda d: d.metadata.get("point", ""))
                doc.metadata["_points"] = doc_points
                article_id_to_clauses.setdefault(parent_id, []).append(doc)
    logger.info(f"[MergeLaw] Số điều có khoản: {len(article_id_to_clauses)}")
    # Bước 4: Gom nhóm các điều, kèm các khoản con (và điểm con trong khoản)
    merged_docs = []
    for doc in all_docs:
        meta = doc.metadata
        if meta.get("type") == "điều":
            article_id = meta.get("id")
            law_name = meta.get("law_name", "")
            chapter = meta.get("chapter", "")
            article = meta.get("article", "")
            title = f"{law_name}"
            if chapter:
                title += f" - {chapter}"
            if article:
                title += f" - Điều {article}"
            content_lines = []
            # Nội dung của điều (nếu có)
            if doc.page_content.strip():
                content_lines.append(doc.page_content.strip())
            # Các khoản con
            clauses = article_id_to_clauses.get(article_id, [])
            clauses = sorted(clauses, key=lambda d: int(d.metadata.get("clause", "99")))
            for clause_doc in clauses:
                clause = clause_doc.metadata.get("clause", "")
                clause_content = clause_doc.page_content.strip()
                content_lines.append(f"- Khoản {clause}: {clause_content}")
                # Các điểm con của khoản này
                points = clause_doc.metadata.get("_points", [])
                points = sorted(points, key=lambda d: d.metadata.get("point", ""))
                for point_doc in points:
                    point = point_doc.metadata.get("point", "")
                    point_content = point_doc.page_content.strip()
                    content_lines.append(f"  + Điểm {point}: {point_content}")
            merged_text = "\n".join(content_lines)
            merged_docs.append(Document(page_content=f"{title}\n{merged_text}", metadata=meta))
    logger.info(f"[MergeLaw] Số doc sau merge: {len(merged_docs)}")
    for i, doc in enumerate(merged_docs[:3]):
        logger.info(f"[MergeLaw] Doc {i+1}: {doc.metadata}, content: {doc.page_content[:200]}")
    return merged_docs 