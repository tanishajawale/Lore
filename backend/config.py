import os
from dotenv import load_dotenv

# Load environment variables from api_config.env file
root_dir = os.path.dirname(os.path.dirname(__file__))
env_path = os.path.join(root_dir, "api_config.env")
load_dotenv(env_path)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MAX_TOKENS = 1024
TEMPERATURE = 0.7
SUMMARY_BATCH_SIZE = 5  # Number of chunks to process together for summarization
MAX_WORDS_FOR_DIRECT_SUMMARY = 4000  # Maximum words for direct summarization

# Streamlit config
STREAMLIT_CONFIG = {
    "page_title": "PDF Chat & Summarizer",
    "page_icon": "📚",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}
