import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import pickle
from qdrant_client import QdrantClient
from supabase import create_client, Client
from typing import Optional

load_dotenv()

# Load env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
QDRANT_PATH = os.getenv("QDRANT_PATH", "qdrant_client.pkl")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# AWS Bedrock Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "meta.llama3-8b-instruct-v1:0")
# Initialization model embedding
embedding_model = SentenceTransformer("Alibaba-NLP/gte-multilingual-base", trust_remote_code=True)

# Initialization QDrant client
qdrant_client = QdrantClient(host="localhost", port=6333)

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