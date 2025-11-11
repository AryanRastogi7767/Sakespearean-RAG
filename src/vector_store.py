"""
Vector database management using ChromaDB
"""
import json
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import logging

from .config import (
    CHROMA_COLLECTION_NAME,
    EMBEDDING_MODEL,
    CHUNK_FILE,
    CHROMA_HOST,
    CHROMA_PORT,
    USE_CHROMA_CLIENT
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorStore:
    """Manages the vector database for the RAG system"""
    
    def __init__(self, collection_name: str = None):
        """
        Initialize the vector store
        
        Args:
            collection_name: Name of the collection
        """
        self.collection_name = collection_name or CHROMA_COLLECTION_NAME
        
        # Initialize ChromaDB client (connecting to separate service)
        if USE_CHROMA_CLIENT:
            logger.info(f"Connecting to ChromaDB service at {CHROMA_HOST}:{CHROMA_PORT}")
            try:
                self.client = chromadb.HttpClient(
                    host=CHROMA_HOST,
                    port=CHROMA_PORT,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                # Test connection
                self.client.heartbeat()
                logger.info("Successfully connected to ChromaDB service")
            except Exception as e:
                logger.error(f"Failed to connect to ChromaDB service: {e}")
                logger.info("Falling back to persistent client")
                # Fallback to persistent client if service is not available
                persist_directory = "/app/chroma_db"
                self.client = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
        else:
            # Use persistent client
            persist_directory = "/app/chroma_db"
            logger.info(f"Using persistent ChromaDB at {persist_directory}")
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        
        # Get or create collection
        self.collection = None
        self._setup_collection()
    
    def _setup_collection(self):
        """Setup or retrieve the collection"""
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Retrieved existing collection: {self.collection_name}")
            logger.info(f"Collection has {self.collection.count()} documents")
        except Exception as e:
            logger.info(f"Creating new collection: {self.collection_name}")
            # Create collection without embedding function - we'll provide embeddings manually
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Julius Caesar play chunks with metadata"},
                embedding_function=None  # We'll compute embeddings ourselves
            )
    
    def load_chunks_from_file(self, file_path: str = None) -> List[Dict]:
        """
        Load chunks from JSONL file
        
        Args:
            file_path: Path to the chunks file
            
        Returns:
            List of chunk dictionaries
        """
        file_path = file_path or str(CHUNK_FILE)
        chunks = []
        
        logger.info(f"Loading chunks from: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    chunks.append(json.loads(line))
        
        logger.info(f"Loaded {len(chunks)} chunks")
        return chunks
    
    def index_chunks(self, chunks: List[Dict] = None):
        """
        Index chunks into the vector database
        
        Args:
            chunks: List of chunk dictionaries. If None, loads from file
        """
        if chunks is None:
            chunks = self.load_chunks_from_file()
        
        if len(chunks) == 0:
            logger.warning("No chunks to index")
            return
        
        # Check if already indexed
        if self.collection.count() >= len(chunks):
            logger.info("Collection already indexed. Skipping.")
            return
        
        logger.info(f"Indexing {len(chunks)} chunks...")
        
        # Prepare data
        documents = []
        metadatas = []
        ids = []
        
        for chunk in chunks:
            documents.append(chunk['text'])
            
            # Prepare metadata (ChromaDB requires strings, ints, or floats)
            # Handle both 'speaker' (single) and 'speakers' (list) fields
            speakers = chunk.get('speakers', [])
            speaker = chunk.get('speaker', speakers[0] if speakers else 'Unknown')
            speakers_str = ','.join(speakers) if speakers else speaker
            
            metadata = {
                'act': chunk.get('act', 0),
                'scene': chunk.get('scene', 0),
                'speaker': speaker,
                'speakers': speakers_str,
                'chunk_type': chunk.get('chunk_type', 'unknown'),
                'num_speeches': chunk.get('num_speeches', 0),
                'total_words': chunk.get('total_words', 0),
            }
            metadatas.append(metadata)
            ids.append(chunk['chunk_id'])
        
        # Compute embeddings using our model
        logger.info(f"Computing embeddings for {len(documents)} documents...")
        embeddings = self.embedding_model.encode(
            documents,
            show_progress_bar=True,
            convert_to_numpy=True
        ).tolist()
        logger.info("Embeddings computed successfully")
        
        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_end = min(i + batch_size, len(documents))
            self.collection.add(
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end],
                ids=ids[i:batch_end],
                embeddings=embeddings[i:batch_end]  # Provide pre-computed embeddings
            )
            logger.info(f"Indexed {batch_end}/{len(documents)} chunks")
        
        logger.info("Indexing complete!")
    
    def query(
        self,
        query_text: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Query the vector database
        
        Args:
            query_text: The query string
            top_k: Number of results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            Dictionary with results
        """
        logger.info(f"Querying: {query_text[:100]}...")
        
        # Compute query embedding using our model
        query_embedding = self.embedding_model.encode([query_text], convert_to_numpy=True).tolist()[0]
        
        # Query with pre-computed embedding
        results = self.collection.query(
            query_embeddings=[query_embedding],  # Use embeddings instead of text
            n_results=top_k,
            where=filter_metadata
        )
        
        # Format results
        formatted_results = {
            'documents': results['documents'][0] if results['documents'] else [],
            'metadatas': results['metadatas'][0] if results['metadatas'] else [],
            'distances': results['distances'][0] if results['distances'] else [],
            'ids': results['ids'][0] if results['ids'] else []
        }
        
        logger.info(f"Retrieved {len(formatted_results['documents'])} results")
        return formatted_results
    
    def reset_collection(self):
        """Reset the collection (useful for development)"""
        logger.warning("Resetting collection...")
        self.client.delete_collection(name=self.collection_name)
        self._setup_collection()
        logger.info("Collection reset complete")


def initialize_vector_store() -> VectorStore:
    """
    Initialize and populate the vector store
    
    Returns:
        Initialized VectorStore instance
    """
    vector_store = VectorStore()
    
    # Index chunks if not already done
    if vector_store.collection.count() == 0:
        logger.info("Vector store is empty. Indexing chunks...")
        vector_store.index_chunks()
    else:
        logger.info(f"Vector store already has {vector_store.collection.count()} documents")
    
    return vector_store


if __name__ == "__main__":
    # Test the vector store
    print("Initializing vector store...")
    vs = initialize_vector_store()
    
    print("\nTesting query...")
    results = vs.query("What does the Soothsayer say to Caesar?", top_k=3)
    
    print("\nResults:")
    for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])):
        print(f"\n[Result {i+1}]")
        print(f"Act {meta['act']}, Scene {meta['scene']} - {meta['speaker']}")
        print(f"Text: {doc[:200]}...")
