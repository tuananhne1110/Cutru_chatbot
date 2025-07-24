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

def load_embedding_config(yaml_path="config/config.yaml"):
    try:
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
            return config.get("embedding", {})
    except Exception:
        return {}
embedding_cfg = load_embedding_config()
embedding_model_name = embedding_cfg.get("model_name", "Alibaba-NLP/gte-multilingual-base")
embedding_model = SentenceTransformer(embedding_model_name, trust_remote_code=True)

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