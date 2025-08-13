# services/graph_rag_init.py
import os
import logging
from services.graph_rag_service import LegalKnowledgeGraph, GraphRAGService

logger = logging.getLogger(__name__)

# Global instances
knowledge_graph = None
graph_rag_service = None

def initialize_graph_rag():
    """Khởi tạo Graph RAG system"""
    global knowledge_graph, graph_rag_service
    
    try:
        logger.info("Initializing Graph RAG system...")
        
        # Initialize knowledge graph
        knowledge_graph = LegalKnowledgeGraph()
        
        # Build graph from legal data
        legal_data_path = "data/chunking/output_json/all_laws.json"
        if os.path.exists(legal_data_path):
            knowledge_graph.build_graph_from_legal_data(legal_data_path)
        else:
            logger.warning(f"Legal data file not found: {legal_data_path}")
            return False
        
        # Initialize service
        graph_rag_service = GraphRAGService(knowledge_graph)
        
        logger.info("Graph RAG system initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Graph RAG: {e}")
        return False

def get_graph_rag_service() -> GraphRAGService:
    """Get Graph RAG service instance"""
    global graph_rag_service
    if graph_rag_service is None:
        initialize_graph_rag()
    return graph_rag_service