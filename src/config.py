"""
Configuration settings for the RAG system
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Model Configuration
# Model Settings
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")  # Much smaller and faster!
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")  # Stable version with working quota

# RAG settings
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "5"))
CHUNK_FILE = DATA_DIR / "processed" / "chunks.jsonl"
EVALUATION_FILE = DATA_DIR / "evaluation.json"

# API settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# ChromaDB settings (using separate service)
CHROMA_COLLECTION_NAME = "julius_caesar"
CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
USE_CHROMA_CLIENT = os.getenv("USE_CHROMA_CLIENT", "true").lower() == "true"

# Create necessary directories
DATA_DIR.mkdir(exist_ok=True)
