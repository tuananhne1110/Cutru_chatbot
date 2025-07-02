import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import pickle
from qdrant_client import QdrantClient
from supabase import create_client, Client

load_dotenv()

# Load env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
QDRANT_PATH = os.getenv("QDRANT_PATH", "qdrant_client.pkl")

# Initialization model embedding
embedding_model = SentenceTransformer('VoVanPhuc/sup-SimCSE-VietNamese-phobert-base')

# Initialization QDrant client
try:
    with open(QDRANT_PATH, "rb") as f:
        qdrant_client = pickle.load(f)
    print("Loaded QDrant client")
except Exception as e:
    print(f"Error loading QDrant client: {e}")
    qdrant_client = None

# Initialization Supabase client
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"Connected to Supabase: {SUPABASE_URL}")
except Exception as e:
    print(f"Failed to connect to Supabase: {e}")
    supabase = None 