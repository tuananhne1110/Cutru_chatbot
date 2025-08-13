# services/graph_rag_monitoring.py
import logging
import time
from typing import Dict, Any
from dataclasses import dataclass, asdict
import json

@dataclass
class GraphRAGMetrics:
    """Metrics cho Graph RAG performance"""
    graph_retrieval_time: float = 0.0
    vector_retrieval_time: float = 0.0
    graph_entities_found: int = 0
    graph_context_length: int = 0
    vector_docs_found: int = 0
    context_combination_time: float = 0.0
    total_processing_time: float = 0.0
    rag_type_used: str = "hybrid"

class GraphRAGMonitor:
    """Monitor Graph RAG performance"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics_history = []
    
    def log_query_metrics(self, metrics: GraphRAGMetrics, query: str):
        """Log metrics for a query"""
        self.logger.info(f"Graph RAG Metrics for query: '{query[:50]}...'")
        self.logger.info(f"  Graph retrieval: {metrics.graph_retrieval_time:.3f}s")
        self.logger.info(f"  Vector retrieval: {metrics.vector_retrieval_time:.3f}s")
        self.logger.info(f"  Graph entities: {metrics.graph_entities_found}")
        self.logger.info(f"  Vector docs: {metrics.vector_docs_found}")
        self.logger.info(f"  Context length: {metrics.graph_context_length}")
        self.logger.info(f"  RAG type: {metrics.rag_type_used}")
        self.logger.info(f"  Total time: {metrics.total_processing_time:.3f}s")
        
        # Store for analysis
        self.metrics_history.append({
            "timestamp": time.time(),
            "query": query[:100],  # Truncated for privacy
            "metrics": asdict(metrics)
        })
        
        # Keep only last 1000 queries
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.metrics_history:
            return {"error": "No metrics available"}
        
        recent_metrics = [entry["metrics"] for entry in self.metrics_history[-100:]]
        
        avg_graph_time = sum(m["graph_retrieval_time"] for m in recent_metrics) / len(recent_metrics)
        avg_vector_time = sum(m["vector_retrieval_time"] for m in recent_metrics) / len(recent_metrics)
        avg_total_time = sum(m["total_processing_time"] for m in recent_metrics) / len(recent_metrics)
        
        rag_types = [m["rag_type_used"] for m in recent_metrics]
        rag_type_counts = {rt: rag_types.count(rt) for rt in set(rag_types)}
        
        return {
            "recent_queries": len(recent_metrics),
            "avg_graph_retrieval_time": avg_graph_time,
            "avg_vector_retrieval_time": avg_vector_time,
            "avg_total_processing_time": avg_total_time,
            "rag_type_distribution": rag_type_counts,
            "avg_graph_entities": sum(m["graph_entities_found"] for m in recent_metrics) / len(recent_metrics),
            "avg_vector_docs": sum(m["vector_docs_found"] for m in recent_metrics) / len(recent_metrics)
        }

# Global monitor instance
graph_rag_monitor = GraphRAGMonitor()