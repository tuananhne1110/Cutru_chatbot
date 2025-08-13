from dataclasses import dataclass
from typing import Optional
import boto3
from instructor import from_bedrock, Mode, Instructor

import yaml
from config.configs import LoggerConfig, Models, Database, \
    SystemSettings, EmbeddingModelConfig, QdrantConfig, \
        RerankerModelConfig, LLMModelConfig, VoiceToTextConfig


# from utils import CONFIG
# from configs import LoggerConfig, Models, Database, SystemSettings, EmbeddingModelConfig, QdrantConfig, RerankerModelConfig, LLMModelConfig

@dataclass
class RetrievalSettings:
    qdrant_config: Optional[QdrantConfig]
    embedding_config: Optional[EmbeddingModelConfig]
    reranker_config: Optional[RerankerModelConfig]
    llm_filter_client: Optional[Instructor]



class Settings:
    def __init__(self, config_path: str = "config/configs.yaml"):
        self.config_path = config_path
        self._config = self._load_yaml_config()
        
        self.models = Models.from_dict(self._config['models'])

        self.system_settings = SystemSettings(
                logger=LoggerConfig(**self._config['system_settings']['logger'])
            )
        self.logger = self.system_settings.setup_logger()
        self.database = Database.from_dict(self._config['database'])

        self.llm_model_settings = self.models.aws_bedrock.llm_model_configs

        self.guardrails_settings = self.models.aws_bedrock.guardrails

        self.retrieval_settings = RetrievalSettings(
            qdrant_config= self._setup_qdrant_config(),
            embedding_config= self.models.hugging_face.embedding_model_configs['qwen'],
            # embedding_config= self.models.aws_bedrock.embedding_model_configs['titan'],
            reranker_config=self.models.hugging_face.reranker_model_configs['bge'],
            llm_filter_client=self._setup_llm_client(),
        )
        
        # Voice config
        self.voice_config = self.models.hugging_face.voice_to_text_config
        
        # Intent config
        self.intent_config = self._config.get('intent', {})
        
        # Cache config
        self.cache_config = self._config.get('cache', {})
        
        # LangSmith config
        self.langsmith_config = self._config.get('langsmith', {})
        
        # LLM config
        self.llm_config = self._config.get('llm', {})
    
    def _load_yaml_config(self) -> dict:
        """Load YAML configuration"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"Warning: Config file {self.config_path} not found")
            return {}
        except yaml.YAMLError as e:
            print(f"Error parsing YAML config: {e}")
            return {}
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}

    def _setup_llm_client(self):
        bedrock_runtime = boto3.client("bedrock-runtime", region_name=self.models.aws_bedrock.llm_model_configs['llama'].region_name)
        return from_bedrock(
            client=bedrock_runtime,
            model=self.models.aws_bedrock.llm_model_configs['llama'].model_id,
            mode=Mode.BEDROCK_JSON,
        )
    
    def _setup_qdrant_config(self) -> QdrantConfig:
        for db_type in self.database.db_type:
            if db_type.database_name == "qdrant":
                return db_type
        return None


# Create global settings instance
settings = Settings()