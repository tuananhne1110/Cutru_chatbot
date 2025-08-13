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
        with open(yaml_path, 'r', encoding = "utf-8-sig") as f:
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

def load_voice_config(yaml_path="config/config.yaml"):
    config = load_config(yaml_path)
    return config.get("voice_to_text", {})

# Load configurations
embedding_cfg = load_embedding_config()
langsmith_cfg = load_langsmith_config()
voice_cfg = load_voice_config()

# embedding_model_name = embedding_cfg.get("model_name", "Alibaba-NLP/gte-multilingual-base")
embedding_model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")

# Preload voice-to-text model if enabled
from config.voice_init import initialize_voice_model, get_voice_model_info

voice_model = initialize_voice_model(voice_cfg)
voice_model_info = get_voice_model_info(voice_cfg)

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
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),

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