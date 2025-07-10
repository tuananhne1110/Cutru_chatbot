#!/usr/bin/env python3
"""
Script khởi động chatbot với AWS Bedrock
"""

import uvicorn
import logging
from main import app

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Khởi động chatbot server"""
    print("🚀 Starting Legal Assistant Chatbot with AWS Bedrock")
    print("="*60)
    print("📋 Configuration:")
    print("  - Backend: FastAPI with LangGraph")
    print("  - LLM: AWS Bedrock (Llama 3.1 8B)")
    print("  - Vector DB: Qdrant")
    print("  - Database: Supabase")
    print("  - Frontend: React (port 3000)")
    print("="*60)
    
    try:
        # Khởi động server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 