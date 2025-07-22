import time
import asyncio
import logging
from typing import List, Dict, Any
from langchain_core.documents import Document
from agents.utils.intent_detector import intent_detector, IntentType
from agents.state import ChatState
from services.embedding import get_embedding
from services.qdrant_service import search_qdrant, search_qdrant_by_parent_id
from services.reranker_service import get_reranker

logger = logging.getLogger(__name__)

async def retrieve_context(state: ChatState) -> ChatState:
    start_time = time.time()
    query = state.get("rewritten_query") or state["question"] or ""
    all_intents = state.get("all_intents", [])
    primary_intent = state["intent"]
    if primary_intent is None:
        raise ValueError("Intent must not be None in retrieve_context")
    all_collections = set()
    for intent_tuple in all_intents:
        intent, _ = intent_tuple
        collections = intent_detector.get_search_collections([(intent, query)])
        all_collections.update(collections)
    collections = list(all_collections)
    logger.info(f"[LangGraph] Collections to search (from all intents): {collections}")
    loop = asyncio.get_running_loop()
    embedding = await loop.run_in_executor(None, get_embedding, query)
    all_docs = []
    for collection in collections:
        if collection == "general_chunks":
            continue
        results, filter_condition = await loop.run_in_executor(None, search_qdrant, collection, embedding, query, 50)
        results_list = results if isinstance(results, list) else [results]
        logger.info(f"[LangGraph] Collection {collection}: found {len(results_list)} results")
        docs = []
        for r in results_list:
            if hasattr(r, 'payload') and r.payload:
                content = r.payload.get("content") or r.payload.get("text", "")
                docs.append(Document(page_content=content, metadata=r.payload))
            elif isinstance(r, dict):
                content = r.get("content") or r.get("text", "")
                docs.append(Document(page_content=content, metadata=r))
        all_docs.extend(docs)
    if all_docs:
        reranker = get_reranker()
        reranked_docs = await loop.run_in_executor(None, reranker.rerank, query or "", [{"content": doc.page_content} for doc in all_docs], 50)
        for i, doc in enumerate(all_docs[:len(reranked_docs)]):
            doc.metadata["rerank_score"] = reranked_docs[i].get("rerank_score", 0.0)
    if primary_intent == IntentType.LAW:
        logger.info("[LangGraph] LAW intent detected - starting parent_id grouping and expansion...")
        expanded_docs = await _expand_law_chunks_with_structure(all_docs, collections, loop)
        group_map = _group_law_chunks_by_parent(expanded_docs)
        merged_docs = _merge_and_format_law_chunks(group_map)
        state["context_docs"] = merged_docs[:8]
    else:
        state["context_docs"] = all_docs[:8]
    logger.info(f"[LangGraph] Retrieval completed: {len(state['context_docs'])} docs")
    duration = time.time() - start_time
    state["processing_time"]["context_retrieval"] = duration
    logger.info(f"[LangGraph] Retrieval time: {duration:.4f}s")
    return state

async def _expand_law_chunks_with_structure(semantic_docs: List[Document], collections: list, loop) -> List[Document]:
    id_to_doc = {doc.metadata.get("id"): doc for doc in semantic_docs if doc.metadata.get("id")}
    parent_ids_needed = set()
    for doc in semantic_docs:
        doc_id = doc.metadata.get("id")
        parent_id = doc.metadata.get("parent_id")
        doc_type = doc.metadata.get("type")
        if doc_type in ["khoản", "điểm"] and parent_id and parent_id not in id_to_doc:
            parent_ids_needed.add(parent_id)
        if doc_type in ["khoản", "điểm"] and parent_id:
            siblings = [d for d in semantic_docs if d.metadata.get("parent_id") == parent_id and d.metadata.get("type") == doc_type]
            if len(siblings) == 1:
                parent_ids_needed.add(parent_id)
    for doc in semantic_docs:
        if doc.metadata.get("type") == "điều":
            doc_id = doc.metadata.get("id")
            if doc_id:
                parent_ids_needed.add(doc_id)
    expansion_docs = []
    for parent_id in parent_ids_needed:
        for collection in collections:
            if collection == "general_chunks":
                continue
            results_list = await loop.run_in_executor(
                None,
                lambda: search_qdrant_by_parent_id(collection, parent_id, 30)
            )
            for r in results_list:
                if hasattr(r, 'payload') and r.payload:
                    content = r.payload.get("content") or r.payload.get("text", "")
                    expansion_docs.append(Document(page_content=content, metadata=r.payload))
                elif isinstance(r, dict):
                    content = r.get("content") or r.get("text", "")
                    expansion_docs.append(Document(page_content=content, metadata=r))
    all_docs = {doc.metadata.get("id"): doc for doc in semantic_docs + expansion_docs if doc.metadata.get("id")}
    logger.info(f"[LangGraph] Law chunk expansion: semantic={len(semantic_docs)}, expanded={len(expansion_docs)}, total={len(all_docs)}")
    return list(all_docs.values())

def _group_law_chunks_by_parent(all_docs: List[Document]) -> Dict[str, List[Document]]:
    logger.info("[LangGraph] Starting _group_law_chunks_by_parent...")
    id_to_doc = {}
    for doc in all_docs:
        doc_id = doc.metadata.get("id")
        if doc_id:
            id_to_doc[doc_id] = doc
    group_map = {}
    for doc in all_docs:
        meta = doc.metadata
        doc_id = meta.get("id")
        parent_id = meta.get("parent_id")
        doc_type = meta.get("type", "")
        if doc_type == "điều":
            if doc_id:
                if doc_id not in group_map:
                    group_map[doc_id] = []
                group_map[doc_id].append(doc)
        elif parent_id:
            if parent_id not in group_map:
                group_map[parent_id] = []
            group_map[parent_id].append(doc)
    for parent_id, group in group_map.items():
        if parent_id in id_to_doc and id_to_doc[parent_id] not in group:
            group.insert(0, id_to_doc[parent_id])
    logger.info(f"[LangGraph] Final group_map has {len(group_map)} groups")
    return group_map

def _merge_and_format_law_chunks(group_map: Dict[str, List[Document]]) -> List[Document]:
    logger.info("[LangGraph] Starting _merge_and_format_law_chunks...")
    merged_docs = []
    for parent_id, group in group_map.items():
        if not group:
            continue
        def sort_key(doc):
            meta = doc.metadata
            clause = meta.get("clause", "")
            point = meta.get("point", "")
            if meta.get("type") == "điều":
                return (0, 0, 0)
            try:
                clause_num = int(clause) if clause.isdigit() else 99
            except:
                clause_num = 99
            try:
                point_num = ord(point.lower()) - ord('a') if point and point.isalpha() else 99
            except:
                point_num = 99
            return (1, clause_num, point_num)
        group_sorted = sorted(group, key=sort_key)
        meta = group_sorted[0].metadata
        law_name = meta.get("law_name", "")
        chapter = meta.get("chapter", "")
        article = meta.get("article", "")
        title = f"{law_name}"
        if chapter:
            title += f" - {chapter}"
        if article:
            title += f" - Điều {article}"
        content_lines = []
        for doc in group_sorted:
            m = doc.metadata
            t = m.get("type", "")
            clause = m.get("clause", "")
            point = m.get("point", "")
            if t == "điều":
                if doc.page_content.strip() and len(group_sorted) == 1:
                    content_lines.append(doc.page_content.strip())
                elif doc.page_content.strip() and len(group_sorted) > 1 and doc.page_content.strip() not in [d.page_content.strip() for d in group_sorted[1:]]:
                    content_lines.append(doc.page_content.strip())
            elif t == "khoản":
                content_lines.append(f"- Khoản {clause}: {doc.page_content.strip()}")
            elif t == "điểm":
                content_lines.append(f"  + Điểm {point}: {doc.page_content.strip()}")
            else:
                content_lines.append(doc.page_content.strip())
        merged_text = "\n".join(content_lines)
        merged_docs.append(Document(page_content=f"{title}\n{merged_text}", metadata=meta))
    logger.info(f"[LangGraph] Total merged docs created: {len(merged_docs)}")
    return merged_docs 