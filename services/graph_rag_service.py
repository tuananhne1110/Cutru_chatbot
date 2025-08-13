# services/graph_rag_service.py
import json
import logging
import re
from typing import Dict, List, Set, Tuple, Any, Optional
import networkx as nx
import spacy
from sentence_transformers import SentenceTransformer
import numpy as np
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class Entity:
    """Thực thể trong knowledge graph"""
    id: str
    name: str
    type: str  # LAW, ARTICLE, CHAPTER, ORGANIZATION, PROCEDURE, etc.
    properties: Dict[str, Any]
    
@dataclass 
class Relationship:
    """Mối quan hệ giữa các thực thể"""
    source: str
    target: str
    relation_type: str  # REFERENCES, BELONGS_TO, REGULATES, etc.
    properties: Dict[str, Any]

@dataclass
class GraphContext:
    """Context được trích xuất từ knowledge graph"""
    entities: List[Entity]
    relationships: List[Relationship]
    subgraph_text: str
    confidence: float

class LegalKnowledgeGraph:
    """Knowledge Graph cho dữ liệu pháp luật"""
    
    def __init__(self, embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"):
        self.graph = nx.MultiDiGraph()
        self.nlp = None  # Sẽ load khi cần
        self.embedding_model = SentenceTransformer(embedding_model)
        self.entity_embeddings = {}
        self.entity_index = {}
        
    def _load_nlp_model(self):
        """Lazy load spaCy model để tránh chậm khởi động"""
        if self.nlp is None:
            try:
                self.nlp = spacy.load("vi_core_news_lg")
                logger.info("Loaded Vietnamese spaCy model")
            except OSError:
                logger.warning("Vietnamese spaCy model not found, using basic model")
                self.nlp = spacy.load("en_core_web_sm")
                
    def extract_legal_entities(self, law_data: Dict) -> List[Entity]:
        """Trích xuất entities từ dữ liệu luật"""
        entities = []
        
        # 1. Law entity
        law_entity = Entity(
            id=f"law_{law_data['id']}",
            name=law_data['law_name'],
            type="LAW",
            properties={
                "law_code": law_data.get('law_code'),
                "promulgation_date": law_data.get('promulgation_date'),
                "promulgator": law_data.get('promulgator'),
                "law_type": law_data.get('law_type'),
                "category": law_data.get('category')
            }
        )
        entities.append(law_entity)
        
        # 2. Chapter entity
        if law_data.get('chapter'):
            chapter_entity = Entity(
                id=f"chapter_{law_data['id']}",
                name=law_data['chapter'],
                type="CHAPTER", 
                properties={
                    "content": law_data.get('chapter_content'),
                    "law_id": law_data['id']
                }
            )
            entities.append(chapter_entity)
            
        # 3. Extract articles từ content
        content = law_data.get('content', '')
        articles = self._extract_articles(content, law_data['id'])
        entities.extend(articles)
        
        # 4. Extract organizations
        organizations = self._extract_organizations(content, law_data['id'])
        entities.extend(organizations)
        
        # 5. Extract legal concepts
        concepts = self._extract_legal_concepts(content, law_data['id'])
        entities.extend(concepts)
        
        return entities
    
    def _extract_articles(self, content: str, law_id: str) -> List[Entity]:
        """Trích xuất các điều luật từ nội dung"""
        entities = []
        
        # Pattern để tìm điều luật: "Điều X.", "Điều X:", "Khoản X", etc.
        article_pattern = r'(Điều\s+\d+[a-z]*\.?|Khoản\s+\d+[a-z]*\.?|Điểm\s+[a-z]+\.?)'
        matches = re.finditer(article_pattern, content, re.IGNORECASE)
        
        for match in matches:
            article_text = match.group(1)
            start_pos = match.start()
            
            # Lấy nội dung của điều (tối đa 500 ký tự)
            article_content = content[start_pos:start_pos + 500]
            
            entity = Entity(
                id=f"article_{law_id}_{len(entities)}",
                name=article_text,
                type="ARTICLE",
                properties={
                    "content": article_content,
                    "law_id": law_id,
                    "position": start_pos
                }
            )
            entities.append(entity)
            
        return entities
    
    def _extract_organizations(self, content: str, law_id: str) -> List[Entity]:
        """Trích xuất tên cơ quan từ nội dung"""
        entities = []
        
        # Các pattern cho cơ quan nhà nước Việt Nam
        org_patterns = [
            r'(Bộ\s+[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ\s]*)',
            r'(Ủy\s+ban\s+[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ\s]*)',
            r'(Tòa\s+án\s+[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ\s]*)',
            r'(Viện\s+kiểm\s+sát\s+[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ][a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ\s]*)',
            r'(Công\s+an\s+[a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ\s]*)',
        ]
        
        found_orgs = set()
        for pattern in org_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                org_name = match.group(1).strip()
                if len(org_name) > 5 and org_name not in found_orgs:  # Tránh trùng lặp
                    found_orgs.add(org_name)
                    
                    entity = Entity(
                        id=f"org_{law_id}_{len(entities)}",
                        name=org_name,
                        type="ORGANIZATION",
                        properties={
                            "law_id": law_id,
                            "context": content[max(0, match.start()-50):match.end()+50]
                        }
                    )
                    entities.append(entity)
        
        return entities
    
    def _extract_legal_concepts(self, content: str, law_id: str) -> List[Entity]:
        """Trích xuất các khái niệm pháp lý"""
        entities = []
        
        # Các khái niệm pháp lý quan trọng về cư trú
        legal_concepts = [
            "cư trú", "tạm trú", "thường trú", "tạm vắng", "lưu trú",
            "đăng ký cư trú", "thay đổi cư trú", "hộ khẩu", "thường trực",
            "xuất nhập cảnh", "thị thực", "thẻ tạm trú", "thẻ thường trú",
            "giấy phép lao động", "visa", "hộ chiếu", "chứng minh nhân dân",
            "căn cước công dân", "giấy khai sinh", "sổ hộ khẩu",
            "phường", "xã", "quận", "huyện", "tỉnh", "thành phố"
        ]
        
        for concept in legal_concepts:
            if concept.lower() in content.lower():
                # Tìm context xung quanh khái niệm
                concept_matches = list(re.finditer(re.escape(concept), content, re.IGNORECASE))
                if concept_matches:
                    match = concept_matches[0]  # Lấy lần xuất hiện đầu tiên
                    context = content[max(0, match.start()-100):match.end()+100]
                    
                    entity = Entity(
                        id=f"concept_{law_id}_{concept.replace(' ', '_')}",
                        name=concept,
                        type="LEGAL_CONCEPT",
                        properties={
                            "law_id": law_id,
                            "context": context,
                            "frequency": len(concept_matches)
                        }
                    )
                    entities.append(entity)
        
        return entities
    
    def extract_relationships(self, entities: List[Entity], law_data: Dict) -> List[Relationship]:
        """Trích xuất mối quan hệ giữa các thực thể"""
        relationships = []
        
        law_entity = next((e for e in entities if e.type == "LAW"), None)
        if not law_entity:
            return relationships
            
        # 1. Quan hệ LAW -> CHAPTER
        for entity in entities:
            if entity.type == "CHAPTER":
                rel = Relationship(
                    source=law_entity.id,
                    target=entity.id,
                    relation_type="CONTAINS",
                    properties={"description": "Law contains chapter"}
                )
                relationships.append(rel)
                
        # 2. Quan hệ CHAPTER -> ARTICLE
        chapter_entities = [e for e in entities if e.type == "CHAPTER"]
        for chapter in chapter_entities:
            for entity in entities:
                if entity.type == "ARTICLE":
                    rel = Relationship(
                        source=chapter.id,
                        target=entity.id,
                        relation_type="CONTAINS",
                        properties={"description": "Chapter contains article"}
                    )
                    relationships.append(rel)
                    
        # 3. Quan hệ LAW -> ORGANIZATION (regulates)
        for entity in entities:
            if entity.type == "ORGANIZATION":
                rel = Relationship(
                    source=law_entity.id,
                    target=entity.id,
                    relation_type="REGULATES",
                    properties={"description": "Law regulates organization"}
                )
                relationships.append(rel)
                
        # 4. Quan hệ LAW -> LEGAL_CONCEPT (defines)
        for entity in entities:
            if entity.type == "LEGAL_CONCEPT":
                rel = Relationship(
                    source=law_entity.id,
                    target=entity.id,
                    relation_type="DEFINES",
                    properties={"description": "Law defines legal concept"}
                )
                relationships.append(rel)
                
        # 5. Cross-references between articles
        articles = [e for e in entities if e.type == "ARTICLE"]
        for i, article1 in enumerate(articles):
            for article2 in articles[i+1:]:
                # Check if articles reference each other by content similarity
                similarity = self._calculate_content_similarity(
                    article1.properties.get('content', ''),
                    article2.properties.get('content', '')
                )
                if similarity > 0.7:  # High similarity threshold
                    rel = Relationship(
                        source=article1.id,
                        target=article2.id,
                        relation_type="REFERENCES",
                        properties={
                            "description": "Articles reference each other",
                            "similarity": similarity
                        }
                    )
                    relationships.append(rel)
        
        return relationships
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Tính độ tương đồng giữa 2 đoạn nội dung"""
        if not content1 or not content2:
            return 0.0
            
        try:
            emb1 = self.embedding_model.encode(content1[:500])  # Limit content length
            emb2 = self.embedding_model.encode(content2[:500])
            
            # Cosine similarity
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            return float(similarity)
        except Exception as e:
            logger.warning(f"Error calculating similarity: {e}")
            return 0.0
    
    def build_graph_from_legal_data(self, legal_data_path: str):
        """Xây dựng knowledge graph từ dữ liệu pháp luật"""
        logger.info("Building knowledge graph from legal data...")
        
        with open(legal_data_path, 'r', encoding='utf-8') as f:
            legal_data = json.load(f)
        
        total_entities = 0
        total_relationships = 0
        
        for i, law_data in enumerate(legal_data):
            if i % 10 == 0:
                logger.info(f"Processing law {i+1}/{len(legal_data)}")
                
            # Extract entities
            entities = self.extract_legal_entities(law_data)
            
            # Extract relationships
            relationships = self.extract_relationships(entities, law_data)
            
            # Add to graph
            for entity in entities:
                self.graph.add_node(
                    entity.id,
                    name=entity.name,
                    type=entity.type,
                    **entity.properties
                )
                
                # Create embedding for entity
                entity_text = f"{entity.name} {entity.properties.get('content', '')}"
                self.entity_embeddings[entity.id] = self.embedding_model.encode(entity_text)
                
            for relationship in relationships:
                self.graph.add_edge(
                    relationship.source,
                    relationship.target,
                    relation_type=relationship.relation_type,
                    **relationship.properties
                )
                
            total_entities += len(entities)
            total_relationships += len(relationships)
        
        logger.info(f"Knowledge graph built: {total_entities} entities, {total_relationships} relationships")
        logger.info(f"Graph has {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
        
    def semantic_search_entities(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Tìm kiếm entities có liên quan đến query"""
        if not self.entity_embeddings:
            return []
            
        query_embedding = self.embedding_model.encode(query)
        
        similarities = []
        for entity_id, entity_embedding in self.entity_embeddings.items():
            similarity = np.dot(query_embedding, entity_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(entity_embedding)
            )
            similarities.append((entity_id, float(similarity)))
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def get_subgraph_around_entities(self, entity_ids: List[str], max_depth: int = 2) -> nx.Graph:
        """Lấy subgraph xung quanh các entities"""
        subgraph_nodes = set(entity_ids)
        
        # Expand to neighbors within max_depth
        for depth in range(max_depth):
            new_nodes = set()
            for node in list(subgraph_nodes):
                if node in self.graph:
                    # Add neighbors
                    neighbors = list(self.graph.neighbors(node))
                    new_nodes.update(neighbors)
                    
                    # Add predecessors
                    predecessors = list(self.graph.predecessors(node))
                    new_nodes.update(predecessors)
            
            subgraph_nodes.update(new_nodes)
        
        return self.graph.subgraph(subgraph_nodes)
    
    def extract_graph_context(self, query: str, top_k: int = 5, max_depth: int = 2) -> GraphContext:
        """Trích xuất context từ knowledge graph dựa trên query"""
        
        # 1. Find relevant entities
        relevant_entities_scores = self.semantic_search_entities(query, top_k)
        relevant_entity_ids = [entity_id for entity_id, score in relevant_entities_scores]
        
        if not relevant_entity_ids:
            return GraphContext(entities=[], relationships=[], subgraph_text="", confidence=0.0)
        
        # 2. Get subgraph
        subgraph = self.get_subgraph_around_entities(relevant_entity_ids, max_depth)
        
        # 3. Extract entities and relationships from subgraph
        entities = []
        relationships = []
        
        for node_id in subgraph.nodes():
            node_data = self.graph.nodes[node_id]
            entity = Entity(
                id=node_id,
                name=node_data.get('name', ''),
                type=node_data.get('type', ''),
                properties={k: v for k, v in node_data.items() if k not in ['name', 'type']}
            )
            entities.append(entity)
        
        for source, target, edge_data in subgraph.edges(data=True):
            relationship = Relationship(
                source=source,
                target=target,
                relation_type=edge_data.get('relation_type', ''),
                properties={k: v for k, v in edge_data.items() if k != 'relation_type'}
            )
            relationships.append(relationship)
        
        # 4. Create subgraph text description
        subgraph_text = self._create_subgraph_text(entities, relationships)
        
        # 5. Calculate confidence based on similarity scores
        confidence = np.mean([score for _, score in relevant_entities_scores[:3]]) if relevant_entities_scores else 0.0
        
        return GraphContext(
            entities=entities,
            relationships=relationships,
            subgraph_text=subgraph_text,
            confidence=confidence
        )
    
    def _create_subgraph_text(self, entities: List[Entity], relationships: List[Relationship]) -> str:
        """Tạo mô tả text từ subgraph"""
        text_parts = []
        
        # Group entities by type
        entities_by_type = defaultdict(list)
        for entity in entities:
            entities_by_type[entity.type].append(entity)
        
        # Describe entities
        for entity_type, entity_list in entities_by_type.items():
            if entity_type == "LAW":
                law_info = []
                for entity in entity_list:
                    law_name = entity.name
                    law_code = entity.properties.get('law_code', '')
                    law_info.append(f"{law_name} ({law_code})")
                text_parts.append(f"Văn bản pháp luật: {', '.join(law_info)}")
                
            elif entity_type == "ARTICLE":
                articles = [entity.name for entity in entity_list]
                text_parts.append(f"Các điều luật: {', '.join(articles)}")
                
            elif entity_type == "ORGANIZATION":
                orgs = [entity.name for entity in entity_list]
                text_parts.append(f"Cơ quan: {', '.join(orgs)}")
                
            elif entity_type == "LEGAL_CONCEPT":
                concepts = [entity.name for entity in entity_list]
                text_parts.append(f"Khái niệm pháp lý: {', '.join(concepts)}")
        
        # Describe key relationships
        reg_relationships = [r for r in relationships if r.relation_type == "REGULATES"]
        if reg_relationships:
            text_parts.append("Mối quan hệ điều chỉnh giữa các văn bản và cơ quan được thiết lập.")
            
        contains_relationships = [r for r in relationships if r.relation_type == "CONTAINS"]
        if contains_relationships:
            text_parts.append("Cấu trúc phân cấp giữa luật, chương và điều được xác định.")
        
        return " ".join(text_parts)

# Graph RAG integration service
class GraphRAGService:
    """Service tích hợp Graph RAG với RAG truyền thống"""
    
    def __init__(self, knowledge_graph: LegalKnowledgeGraph):
        self.knowledge_graph = knowledge_graph
        
    def get_graph_context(self, query: str) -> Optional[str]:
        """Lấy context từ knowledge graph"""
        try:
            graph_context = self.knowledge_graph.extract_graph_context(query)
            
            if graph_context.confidence > 0.3:  # Threshold for using graph context
                return graph_context.subgraph_text
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting graph context: {e}")
            return None
    
    def combine_contexts(self, vector_context: str, graph_context: str) -> str:
        """Kết hợp context từ vector search và graph"""
        if not graph_context:
            return vector_context
            
        if not vector_context:
            return f"Thông tin từ knowledge graph:\n{graph_context}"
            
        return f"Thông tin từ knowledge graph:\n{graph_context}\n\nThông tin chi tiết:\n{vector_context}"