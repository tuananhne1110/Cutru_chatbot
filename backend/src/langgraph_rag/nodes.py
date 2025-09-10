from typing import List, Dict, Any
from .guardrails.bedrock_guardrails import BedrockGuardrails
from .utils.logger_utils import get_logger
from .utils.llm_utils import TextChatMessage, DocumentProcessor
from .utils.config_utils import BaseConfig
from .prompts.query_route import QueryRoute
from .prompts.system_prompt import GenerateAnswer

from .embeddings.qwen_embedding_model import QwenEmbeddingModel
from .database.qdrant_client import QdrantDatabase
from .reranker.bge_reranker import BGEReranker
from .search.vector_search import VectorRetriever
from .search.hybird_search import HybridRetriever
from .state import RagState
# Langfuse tracking removed

logger = get_logger(__name__)


def create_default_rag_state(question: str, conversation_history: List[TextChatMessage] = None) -> RagState:
    return {
        "question": question,
        "conversation_history": conversation_history or [],
        "final_response": None,

        "current_status": "INIT",
        "error_count": 0,

        "processing_steps": [],
        "execution_metadata": {},

        'total_token': 0
    }

def _preview_text(x: Any, max_len: int = 200) -> str:
    try:
        s = str(x)
        return s[:max_len] + ("…" if len(s) > max_len else "")
    except Exception:
        return "<unserializable>"

class RAGWorkflowNodes:
    def __init__(self, global_config: BaseConfig):
        self.global_config = global_config

        self.bedrock_guardrails = BedrockGuardrails(global_config= global_config)
        self.query_route = QueryRoute(global_config= global_config)

        self.embedding = QwenEmbeddingModel(global_config=global_config)
        self.database = QdrantDatabase(global_config=global_config)
        self.reranker = BGEReranker(global_config=global_config)
        self.vector_search = VectorRetriever(embedding=self.embedding, database= self.database)
        self.hybird_search = HybridRetriever(vector_retriever=self.vector_search, reranker= self.reranker)

        self.generate_answer = GenerateAnswer(global_config= global_config)
        self.document_processor = DocumentProcessor()


        self.MAX_HISTORY = 20

    def _append_history(self, state: RagState, role: str, content: Any) -> None:
        history = state['conversation_history']
        history.append({"role": role, "content": content})
        if len(history) > self.MAX_HISTORY:
            history[:] = history[-self.MAX_HISTORY:]
        state["conversation_history"] = history

    def _extract_guardrail_message(self, guardrail_result: Dict[str, Any]) -> str:
        """Trích xuất thông báo từ kết quả guardrail"""
        try:
            outputs = guardrail_result.get("outputs", [])
            if outputs and len(outputs) > 0:
                return outputs[0].get("text", "Nội dung vi phạm chính sách.")
            return "Nội dung vi phạm chính sách."
        except:
            return "Nội dung vi phạm chính sách."



    def input_validation_node(self, state: RagState) -> RagState:
        logger.info("--- NODE: INPUT VALIDATION & GUARDRAIL ---")
        quesion = state["question"]
        try:
            result = self.bedrock_guardrails.apply_guardrail(
                text=quesion,
                source_type="INPUT"
            )

                
            action = result.get("action", "NONE")
            state["input_guardrail_status"] = action

            state["total_token"] += result['assessments'][-1]['invocationMetrics']['guardrailCoverage']['textCharacters']['total']

            
            if action == "GUARDRAIL_INTERVENED":
                state["current_status"] = "INPUT_BLOCKED"
                state["final_response"] = self._extract_guardrail_message(result)
                logger.error(f"Input blocked by guardrail: {state['final_response']}")
            else:
                state["current_status"] = "INPUT_VALIDATED"
                logger.info(f"Input validation passed: '{quesion}'")

        except Exception as e:
            logger.error(f"Error in input validation: {str(e)}")
            state["current_status"] = "VALIDATION_ERROR"
            state["error_count"] = state.get("error_count", 0) + 1

        state["processing_steps"] = state.get("processing_steps", []) + ["input_validated"]
        return state
    
    def query_analysis_node(self, state: RagState) -> RagState:
        if state["current_status"] == "INPUT_BLOCKED":
            logger.info("Input was blocked, skipping intent routing")
            return state
        logger.info("--- NODE: INTENT ANALYSIS & QUERY ROUTING ---")
        
        quesion = state["question"]
        

        intents, total_token = self.query_route.query_route(quesion)

        logger.info(f"Intent routing results:\n {intents} ")
        state['intents'] = intents
        state['total_token'] += total_token
        try:
            if (
                isinstance(intents, dict)
                and intents.get("general", False)
                and sum(bool(v) for k, v in intents.items() if k != "general") == 0
                ):
                state["current_status"] = "GENERAL_QUERY"
                logger.info("General query detected, skip retrieval and go to LLM answer.")
            else:
                state["current_status"] = "INTENT_ANALYZED"

        except Exception as e:
            logger.error(f"Error in intent routing: {str(e)}")
            state["current_status"] = "ROUTING_ERROR"
            state["error_count"] = state.get("error_count", 0) + 1
        
        state["processing_steps"] = state.get("processing_steps", []) + ["intent_routed"]

        return state
    
    def document_retrieval_node(self, state: RagState) -> RagState:
        """Node 3: Truy xuất tài liệu từ các collection"""
        
        if state["current_status"] in ["INPUT_BLOCKED", "ROUTING_ERROR", "GENERAL_QUERY"]:
            return state
        logger.info("--- NODE: DOCUMENT RETRIEVAL ---")

        try:
            all_documents = []
            # keyworks = []
            intents = state["intents"]
            quesion = state["question"]

            # collections = [
            #     key
            #     for key, val in intents.items()
            #     if val
            # ]

            collections = []
            for key, val in intents.items():
                if val:
                    if key == "legal":
                        collections.append("legal_quantization")
                    elif key == "procedure":
                        collections.append("procedure_quantization")
                    else:
                        collections.append(key)

            
            for collection_name in collections:
                    

                    # # test quantization
                    # if collection_name == ""

                    # filter_condition = self.retrieval_service.generate_filter_from_query(
                    #     query=user_query,
                    #     collection_name=collection_name
                    #     )
                    # if filter_condition:
                    #     filter_condition = filter_condition.to_qdrant_filter()
                    #     keyworks.extend(extract_filter_keys(filter_obj=filter_condition))
                    # else:
                    #     filter_condition = None

                    docs = self.hybird_search.retrieve(
                        query=quesion,
                        collection_name=collection_name, 
                        filters=None, 
                        limit=10,
                        top_k=5
                    )
                    
                    all_documents.extend(docs)
                    if docs and "question" in docs[0]['payload'].keys() and "answer" in docs[0]['payload'].keys():
                        break


            if all_documents and "question" in all_documents[0]['payload'].keys() and "answer" in all_documents[0]['payload'].keys():
                state["current_status"] = "QDRANT_CACHE_ANSWER"
                state["generated_answer"] = all_documents[0]['payload']['answer']

            else: 
                if all_documents:
                    filtered_content = ""
                    for idx, document in enumerate(all_documents):
                        formatted_doc = self.document_processor.format_document_content(
                            payload=document['payload'], 
                            doc_id=idx+1,
                        )
                        filtered_content += formatted_doc

                    state["raw_documents"] = all_documents
                    state["relevant_context"] = filtered_content
                    state["current_status"] = "DOCUMENTS_RETRIEVED"
                    
                    logger.info(f"Retrieved {len(all_documents)} documents")
                    logger.info(f"relevant_context: \n{filtered_content}")
                else:
                    # No documents found, switch to general query mode
                    logger.warning("No documents found, switching to general query mode")
                    state["current_status"] = "GENERAL_QUERY"

            
        except Exception as e:
            logger.error(f"Error in document retrieval: {str(e)}")
            state["current_status"] = "RETRIEVAL_ERROR"
            state["error_count"] = state.get("error_count", 0) + 1
        
        state["processing_steps"] = state.get("processing_steps", []) + ["documents_retrieved"]
        
        return state
    
    def answer_generation_node(self, state: RagState) -> RagState:
        if state["current_status"] not in ["DOCUMENTS_RETRIEVED", "GENERAL_QUERY"]:
            return state
        logger.info("--- NODE: ANSWER GENERATION ---")
        
        try:
            quesion = state["question"]
            conversation_history = state["conversation_history"]
            if state["current_status"] == "GENERAL_QUERY":
                generated_answer, total_token = self.generate_answer.generate_general(
                    question=quesion, conversation_history=conversation_history
                )
            else:
                relevant_context = state["relevant_context"]
                generated_answer, total_token = self.generate_answer.generate_intent(
                    question=quesion, related_text=relevant_context, conversation_history=conversation_history
                )
            
            state["generated_answer"] = generated_answer
            state['total_token'] += total_token
            state["current_status"] = "ANSWER_GENERATED"
            logger.info("Answer generation completed")

        except Exception as e:
            logger.error(f"Error in answer generation: {str(e)}")
            state["current_status"] = "GENERATION_ERROR"
            state["error_count"] = state.get("error_count", 0) + 1
        
        state["processing_steps"] = state.get("processing_steps", []) + ["answer_generated"]
        
        return state
    
    def output_validation_node(self, state: RagState) -> RagState:
        if state["current_status"] not in ["ANSWER_GENERATED", "QDRANT_CACHE_ANSWER"]:
            return state
        logger.info("--- NODE: OUTPUT VALIDATION & GUARDRAIL ---")
        
        try:
            answer = state["generated_answer"]
    
            # result = self.bedrock_guardrails.apply_guardrail(
            #     text=answer,
            #     source_type="OUTPUT"
            # )

            result = self.bedrock_guardrails.apply_guardrail(
                text=answer,
                source_type="OUTPUT"
            )

            action = result.get("action", "NONE")
            state["total_token"] += result['assessments'][-1]['invocationMetrics']['guardrailCoverage']['textCharacters']['total']
            if action == "GUARDRAIL_INTERVENED":
                state["current_status"] = "OUTPUT_BLOCKED"
                blocked_message = self._extract_guardrail_message(result)
                state["final_response"] = blocked_message
                logger.warning(f"Output blocked by guardrail")
            else:
                state["current_status"] = "OUTPUT_VALIDATED"
                state["final_response"] = answer
                logger.info("Output validation passed")
            
            self._append_history(state, role="user", content=state["question"])
            self._append_history(state, role="assistant", content=state["final_response"])
        except Exception as e:
            logger.error(f"Error in output validation: {str(e)}")
            state["current_status"] = "OUTPUT_VALIDATION_ERROR"
            state["error_count"] = state.get("error_count", 0) + 1
        
        state["processing_steps"] = state.get("processing_steps", []) + ["output_validated"]
        
        return state
    
    def upload_memory(self, state: RagState) -> RagState:
        pass