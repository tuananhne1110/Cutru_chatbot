import os
from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional, Union
from .logger_utils import get_logger
from dotenv import load_dotenv, find_dotenv
import yaml
_ = load_dotenv(find_dotenv())
logger = get_logger(__name__)


def read_yaml_file(file_path):
    """
    Đọc nội dung từ file YAML và trả về dưới dạng dict.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
            return data
    except FileNotFoundError:
        print(f"Không tìm thấy file: {file_path}")
    except yaml.YAMLError as e:
        print(f"Lỗi khi phân tích YAML: {e}")
    return None

CONFIG = read_yaml_file(r'D:\SDT_solution\sdt_agent\chatbot\backend\configs.yaml')

@dataclass
class BaseConfig:
    """One and only configuration."""
    llm_name: str = field(
        default=CONFIG['models']['aws_bedrock']['llm_model_configs']['llama']['model_id'],
        metadata={"help": "Class name indicating which LLM model to use."}
    )
 
    max_new_tokens: Union[None, int] = field(
        default=CONFIG['models']['aws_bedrock']['llm_model_configs']['llama']['max_gen_len'],
        metadata={"help": "Max new tokens to generate in each inference."}
    )

    temperature: float = field(
        default=CONFIG['models']['aws_bedrock']['llm_model_configs']['llama']['temperature'],
        metadata={"help": "Temperature for sampling in each inference."}
    )

    response_format: Union[dict, None] = field(
        default_factory=lambda: { "type": "json_object" },
        metadata={"help": "Specifying the format that the model must output."}
    )

    # 2. Cấu hình gọi API bất đồng bộ
    ## LLM specific attributes -> Async hyperparameters
    max_retry_attempts: int = field(
        default=CONFIG['models']['max_retry_attempts'],
        metadata={"help": "Max number of retry attempts for an asynchronous API calling."}
    )
    
    # 3. Cấu hình embedding
    # Embedding specific attributes
    embedding_model_name: str = field(
        default=CONFIG['models']['hugging_face']['embedding_model_configs']['qwen']['model_name'],
        metadata={"help": "Class name indicating which embedding model to use."}
    )
    embedding_device: str = field(
        default=CONFIG['models']['hugging_face']['embedding_model_configs']['qwen']['device'],
        metadata={"help": "The device name (e.g. 'cuda', 'cuda') used to run the user embedding model.."}
    )
    embedding_batch_size: int = field(
        default=CONFIG['models']['hugging_face']['embedding_model_configs']['qwen']['batch_size'],
        metadata={"help": "Batch size of calling embedding model."}
    )
    embedding_return_as_normalized: bool = field(
        default=CONFIG['models']['hugging_face']['embedding_model_configs']['qwen']['normalized'],
        metadata={"help": "Whether to normalize encoded embeddings not."}
    )
    embedding_max_seq_len: int = field(
        default=CONFIG['models']['hugging_face']['embedding_model_configs']['qwen']['max_seq_len'],
        metadata={"help": "Max sequence length for the embedding model."}
    )
    embedding_model_dtype: Literal["float16", "float32", "bfloat16", "auto"] = field(
        default="auto",
        metadata={"help": "Data type for local embedding model."}
    )
    
    
    # 4. Cấu hình reranker
    # reranker specific attributes
    
    reranker_model_name: str = field(
        default=CONFIG['models']['hugging_face']['reranker_model_configs']['bge']['model_name'],
        metadata={"help": "Class name indicating which reranker model to use."}
    )
    reranker_device: str = field(
        default=CONFIG['models']['hugging_face']['reranker_model_configs']['bge']['device'],
        metadata={"help": "The device name (e.g. 'cuda', 'cuda') used to run the user reranker model.."}
    )

    reranker_quantize_int8: bool = field(
        default= True,
        metadata= {"help": ""}
    )
    
    reranker_quant_backend: str = field(
        default="pytorch_dynamic",
        metadata={"help": ""}
    )

    max_length: int = field(
        default=512,
        metadata={"help": "Maximum total tokens for (query + paragraph)."}
    )

    batch_size: int = field(
        default=8,
        metadata={"help": "Batch size when calculating scores for multiple passages."}
    )

    apply_sigmoid: bool = field(
        default=True,
        metadata={"help": "Use sigmoid to scale the score to [0,1]. If False use raw logits."}
    )
    # ===== Post-processing =====
    top_k: int = field(
        default=5,
        metadata={"help": "Number of results retained after rerank."}
    )

    # 5. Cấu hình automate filtering

    filter_llm_name: str = field(
        default="us.meta.llama4-scout-17b-instruct-v1:0",
        metadata={"help": "Class name indicating which LLM model to use."}
    )


    # 6. Cấu hình vector database

    database_name: str = field(
        default="qdrant",
        metadata= {"help": ""}
    )

    qdrant_host: str = field(
        default="localhost",
        metadata= {"help": ""}
    )

    qdrant_port: int = field(
        default= 6333,
        metadata= {"help": ""}
    )

    qdrant_url: str = field(
        default=os.getenv('QDRANT_URL', "http://localhost:6333"),
        metadata={"help": "URL endpoint of the Qdrant vector database service."}
    )

    qdrant_api_key: str = field(
        default=os.getenv('QDRANT_API_KEY', None),
        metadata={"help": "API key used to authenticate requests to the Qdrant service."}
    )


    # 7. Cấu hình Guardrails
    guardrails_id : str = field(
        default=os.getenv('GUARDRAIL_ID', None),
        metadata={"help": ""}
    )

    guardrails_version : str = field(
        default=os.getenv('GUARDRAIL_VERSION', None),
        metadata={"help": ""}
    )

    guardrails_region_name : str = field(
        default=os.getenv('REGION_NAME', "us-east-1"),
        metadata={"help": ""}
    )
    # Retrieval specific attributes

    retrieval_top_k: int = field(
        default=10,
        metadata={"help": "Retrieving k documents at each step"}
    )

    # Save dir (highest level directory)
    save_dir: str = field(
        default='backend/src/langgraph_rag/cache',
        metadata={"help": "Directory to save all related information. If it's given, will overwrite all default save_dir setups. If it's not given, then if we're not running specific datasets, default to `outputs`, otherwise, default to a dataset-customized output dir."}
    )

    # redis config (cache)

    redis_enabled: bool = field(
        default=CONFIG['services']['redis']['enabled'],
        metadata={"help": "Bật/tắt Redis cache toàn hệ thống."}
    )
    redis_url: Optional[str] = field(
        default=CONFIG['services']['redis'].get('url'),
        metadata={"help": "DSN dạng redis://[:password]@host:port/db. Ưu tiên dùng nếu có."}
    )
    redis_host: str = field(
        default=CONFIG['services']['redis']['host'],
        metadata={"help": "Địa chỉ Redis host (nếu không dùng redis_url)."}
    )
    redis_port: int = field(
        default=CONFIG['services']['redis']['port'],
        metadata={"help": "Cổng Redis (nếu không dùng redis_url)."}
    )
    redis_db: int = field(
        default=CONFIG['services']['redis']['db'],
        metadata={"help": "Chỉ số database của Redis (nếu không dùng redis_url)."}
    )
    redis_password: Optional[str] = field(
        default=CONFIG['services']['redis'].get('password'),
        metadata={"help": "Mật khẩu Redis (nếu có, và không dùng redis_url)."}
    )
    redis_ttl_seconds: int = field(
        default=CONFIG['services']['redis']['ttl_seconds'],
        metadata={"help": "Thời gian sống của cache (giây)."}
    )
    redis_prefix: str = field(
        default=CONFIG['services']['redis']['prefix'],
        metadata={"help": "Tiền tố (namespace) cho key Redis, ví dụ: 'rag'."}
    )
    redis_socket_timeout: float = field(
        default=CONFIG['services']['redis']['socket_timeout'],
        metadata={"help": "Socket timeout khi gọi Redis (giây)."}
    )
    redis_retry_on_timeout: bool = field(
        default=CONFIG['services']['redis']['retry_on_timeout'],
        metadata={"help": "Tự động thử lại khi timeout."}
    )
    redis_max_connections: int = field(
        default=CONFIG['services']['redis']['max_connections'],
        metadata={"help": "Số kết nối tối đa trong connection pool."}
    )

    # Helper: trả về DSN cuối cùng để client dùng
    def get_redis_dsn(self) -> Optional[str]:
        if not self.redis_enabled:
            return None
        if self.redis_url:
            return self.redis_url
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"