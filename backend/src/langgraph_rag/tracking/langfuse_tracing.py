from langfuse import get_client, observe
from dotenv import load_dotenv
from ..utils.logger_utils import get_logger

logger = get_logger(__name__)
load_dotenv()
LANGFUSE = get_client()

if LANGFUSE.auth_check():
    logger.info("Langfuse client is authenticated and ready!")
else:
    logger.info("Authentication failed. Please check your credentials and host.")

    
