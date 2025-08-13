from dataclasses import dataclass, field
from enum import Enum
import logging
from typing import Any, Dict, List, Optional
import os
from dotenv import load_dotenv, find_dotenv

_ = load_dotenv(find_dotenv())

# System Settings Classes
@dataclass
class LoggerConfig:
    name: str = "RAGWorkflow"
    log_level: str = "INFO"
    log_file: Optional[str] = None
    enable_performance_logging: bool = True
    enable_model_logging: bool = True

@dataclass
class SystemSettings:
    logger: LoggerConfig = field(default_factory=LoggerConfig)
    
    def setup_logger(self) -> logging.Logger:
        """Setup logger based on configuration"""
        logger = logging.getLogger(self.logger.name)
        logger.setLevel(getattr(logging, self.logger.log_level))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.logger.log_level))
        
        # File handler if specified
        if self.logger.log_file:
            file_handler = logging.FileHandler(self.logger.log_file)
            file_handler.setLevel(getattr(logging, self.logger.log_level))
            logger.addHandler(file_handler)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger

# Models Classes
@dataclass
class LLMModelConfig:
    model_id: str
    region_name: str
    max_tokens: Optional[int] = None
    max_gen_len: Optional[int] = None
    temperature: float = 0.0
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    anthropic_version: Optional[str] = None
    stop_sequences: Optional[List[str]] = None

@dataclass
class EmbeddingModelConfig:
    model_id: Optional[str] = None
    model_name: Optional[str] = None
    output_dimension: Optional[int] = None
    normalize: Optional[bool] = None
    device: Optional[str] = None
    trust_remote_code: Optional[bool] = None
    enabled: Optional[bool] = True
    prompt_name: Optional[str] = None
    model_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class VoiceToTextConfig:
    model_name: str
    batch_size: int = 8
    num_workers: int = 1
    device: Optional[int] = None  # null for auto-detect, 0 for GPU, -1 for CPU
    preload_model: bool = True
    vad_aggressiveness: int = 3
    frame_duration: int = 30
    sample_rate: int = 16000

@dataclass
class VoiceToTextConfig:
    model_name: str
    batch_size: int = 8
    num_workers: int = 1
    device: Optional[int] = None
    preload_model: bool = True
    vad_aggressiveness: int = 3
    frame_duration: int = 30
    sample_rate: int = 16000

@dataclass
class GuardrailsConfig:
    model_id: str
    region_name: str
    guardrail_id: str
    guardrail_version: str = "DRAFT"
    enabled: bool = False

@dataclass
class RerankerModelConfig:
    model_name: str
    device: str = "cuda"
    enabled: bool = True
    model_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AWSBedrockConfig:
    llm_model_configs: Dict[str, LLMModelConfig] = field(default_factory=dict)
    embedding_model_configs: Dict[str, EmbeddingModelConfig] = field(default_factory=dict)
    guardrails: Optional[GuardrailsConfig] = None

@dataclass
class HuggingFaceConfig:
    embedding_model_configs: Dict[str, EmbeddingModelConfig] = field(default_factory=dict)
    reranker_model_configs: Dict[str, RerankerModelConfig] = field(default_factory=dict)
    voice_to_text_config: Optional[VoiceToTextConfig] = None
    voice_to_text_config: Optional[VoiceToTextConfig] = None

@dataclass
class Models:
    aws_bedrock: Optional[AWSBedrockConfig] = None
    hugging_face: Optional[HuggingFaceConfig] = None
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'Models':
        """Create Models instance from configuration dictionary"""
        models = cls()

        # Parse AWS Bedrock config
        if 'aws_bedrock' in config_dict:
            bedrock_config = config_dict['aws_bedrock']
            aws_bedrock = AWSBedrockConfig()
            
            # Parse LLM configs
            if 'llm_model_configs' in bedrock_config:
                for name, config in bedrock_config['llm_model_configs'].items():
                    aws_bedrock.llm_model_configs[name] = LLMModelConfig(**config)
            
            # Parse embedding configs
            if 'embedding_model_configs' in bedrock_config:
                for name, config in bedrock_config['embedding_model_configs'].items():
                    aws_bedrock.embedding_model_configs[name] = EmbeddingModelConfig(**config)
            
            # Parse guardrails
            if 'guardrails' in bedrock_config:
                aws_bedrock.guardrails = GuardrailsConfig(
                    model_id = bedrock_config['guardrails']['model_id'],
                    region_name= bedrock_config['guardrails']['region_name'],
                    guardrail_id = os.getenv('GUARDRAIL_ID', bedrock_config['guardrails']['guardrail_id']),
                    guardrail_version= os.getenv('GUARDRAIL_VERSION', bedrock_config['guardrails']['guardrail_version']),
                    enabled=True,
                )
            
            models.aws_bedrock = aws_bedrock
        
        # Parse HuggingFace config
        if 'hugging_face' in config_dict:
            hf_config = config_dict['hugging_face']
            hugging_face = HuggingFaceConfig()
                
            if 'embedding_model_configs' in hf_config:
                for name, config in  hf_config['embedding_model_configs'].items():
                    hugging_face.embedding_model_configs[name] = EmbeddingModelConfig(**config)
            
            if 'reranker_model_configs' in hf_config:
                for name, config in  hf_config['reranker_model_configs'].items():
                    hugging_face.reranker_model_configs[name] = RerankerModelConfig(**config)
            
            if 'voice_to_text_config' in hf_config:
                hugging_face.voice_to_text_config = VoiceToTextConfig(**hf_config['voice_to_text_config'])
            
            models.hugging_face = hugging_face
        
        return models

# Database Classes
@dataclass
class Collection:
    name: str
    description: str
    domain: str
    collection_name: str

@dataclass
class QdrantConfig:
    database_name: str = "qdrant"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None
    collections: List[Collection] = field(default_factory=list)

@dataclass
class Database:
    db_type: List[QdrantConfig] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'Database':
        """Create Database instance from configuration dictionary"""
        database = cls()
        
        if 'db_type' in config_dict:
            for db_config in config_dict['db_type']:
                qdrant_config = QdrantConfig(
                    database_name=db_config.get('database_name', 'qdrant'),
                    qdrant_host=db_config.get('qdrant_host', 'localhost'),
                    qdrant_port=db_config.get('qdrant_port', 6333),
                    qdrant_url = os.getenv('QDRANT_URL', db_config.get('qdrant_url')), 
                    qdrant_api_key=os.getenv('QDRANT_API_KEY', db_config.get('qdrant_api_key')), 
                )
                
                # Parse collections
                if 'collections' in db_config:
                    for coll in db_config['collections']:
                        collection = Collection(
                            name=coll['name'],
                            description=coll['description'],
                            domain=coll['domain'],
                            collection_name=coll['collection_name']
                        )
                        qdrant_config.collections.append(collection)
                
                database.db_type.append(qdrant_config)
        
        return database
    
    def get_collection_by_name(self, name: str) -> Optional[Collection]:
        """Get collection by name"""
        for db in self.db_type:
            for collection in db.collections:
                if collection.name == name:
                    return collection
        return None
    
    def get_collections_by_domain(self, domain: str) -> List[Collection]:
        """Get all collections for a specific domain"""
        collections = []
        for db in self.db_type:
            for collection in db.collections:
                if collection.domain == domain:
                    collections.append(collection)
        return collections

# Intent Classes
@dataclass
class IntentConfig:
    intent_to_collections: Dict[str, List[str]] = field(default_factory=dict)
    keywords: Dict[str, List[str]] = field(default_factory=dict)

# Cache Classes
@dataclass
class CacheConfig:
    cache_limit: int = 1000
    chunk_size: int = 100
    threshold: float = 0.85
    paraphrase_cache_prefix: str = "paraphrase_cache:"
    cache_key: str = "semantic_prompt_cache"

# LangSmith Classes
@dataclass
class LangSmithConfig:
    project_name: str = "cutru-chatbot"
    api_url: str = "https://api.smith.langchain.com"
    tracing_enabled: bool = True
    tags: List[str] = field(default_factory=lambda: ["development", "rag-workflow", "vietnamese-legal"])
    metadata: Dict[str, str] = field(default_factory=lambda: {
        "application": "cutru-chatbot",
        "version": "2.0.0",
        "environment": "development"
    })

# LLM Classes
@dataclass
class LLMConfig:
    prompt_version: str = "v1"
    default_model_name: str = "us.meta.llama4-scout-17b-instruct-v1:0"
