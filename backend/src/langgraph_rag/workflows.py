from .nodes import RAGWorkflowNodes
from .state import RagState
from langgraph.graph import StateGraph, END

def create_rag_workflow(rag_nodes: RAGWorkflowNodes):
    """
    Tạo đồ thị workflow theo thứ tự:
    input_validation -> query_analysis -> document_retrieval -> answer_generation -> output_validation -> END
    Các node tự kiểm tra state["current_status"] để bỏ qua nếu cần.
    """
    graph = StateGraph(RagState)

    graph.add_node("input_validation", rag_nodes.input_validation_node)
    # thêm semactic_cache ở đây
    
    graph.add_node("query_analysis", rag_nodes.query_analysis_node)
    graph.add_node("document_retrieval", rag_nodes.document_retrieval_node)
    graph.add_node("answer_generation", rag_nodes.answer_generation_node)
    graph.add_node("output_validation", rag_nodes.output_validation_node)

    graph.set_entry_point("input_validation")
    graph.add_edge("input_validation", "query_analysis")
    graph.add_edge("query_analysis", "document_retrieval")
    graph.add_edge("document_retrieval", "answer_generation")
    graph.add_edge("answer_generation", "output_validation")
    graph.add_edge("output_validation", END)

    return graph.compile()


