import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from supabase import create_client, Client
from typing import Optional
import yaml

load_dotenv()

# Load env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# LangSmith configuration
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "true")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "cutru-chatbot")
LANGSMITH_API_URL = os.getenv("LANGSMITH_API_URL", "https://api.smith.langchain.com")

def load_config(yaml_path="config/config.yaml"):
    try:
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
            return config
    except Exception:
        return {}

def load_embedding_config(yaml_path="config/config.yaml"):
    config = load_config(yaml_path)
    return config.get("embedding", {})

def load_langsmith_config(yaml_path="config/config.yaml"):
    config = load_config(yaml_path)
    return config.get("langsmith", {})

# Load configurations
embedding_cfg = load_embedding_config()
langsmith_cfg = load_langsmith_config()
embedding_model_name = embedding_cfg.get("model_name", "Alibaba-NLP/gte-multilingual-base")
embedding_model = SentenceTransformer(embedding_model_name, trust_remote_code=True)

# Initialize LangSmith tracing if enabled
if langsmith_cfg.get("tracing_enabled", False) and LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = langsmith_cfg.get("project_name", LANGCHAIN_PROJECT)
    os.environ["LANGSMITH_API_URL"] = langsmith_cfg.get("api_url", LANGSMITH_API_URL)
    print(f"LangSmith tracing enabled for project: {langsmith_cfg.get('project_name', LANGCHAIN_PROJECT)}")
else:
    print("LangSmith tracing disabled or API key not found")

qdrant_client = QdrantClient(
    # url=os.getenv("QDRANT_URL"),
    # api_key=os.getenv("QDRANT_API_KEY"),
    host="localhost",
    port=6333
)

# Initialization Supabase client
supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"Connected to Supabase: {SUPABASE_URL}")
    except Exception as e:
        print(f"Failed to connect to Supabase: {e}")
        supabase = None
else:
    print("Supabase URL or KEY not found in environment variables") 