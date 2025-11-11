"""
RAG pipeline implementation
"""
import logging
import re
from typing import Dict, List, Optional
from google import genai

from .config import (
    GOOGLE_API_KEY,
    LLM_MODEL,
    TOP_K_RESULTS
)
from .prompts import create_rag_prompt, create_context_from_chunks
from .vector_store import VectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_act_scene(query: str) -> Optional[Dict]:
    """
    Extract Act and Scene numbers from a query
    
    Args:
        query: User's question
        
    Returns:
        Dictionary with 'act' and optionally 'scene' keys, or None
    """
    # Patterns to match: "Act 3 Scene 1", "act 3, scene 1", "Act III Scene I", etc.
    patterns = [
        r'act\s+(\d+)\s+scene\s+(\d+)',  # Act 3 Scene 1
        r'act\s+(\d+),?\s+scene\s+(\d+)',  # Act 3, Scene 1
        r'act\s+([IVX]+)\s+scene\s+([IVX]+)',  # Act III Scene I (Roman numerals)
        r'act\s+(\d+)',  # Just Act 3
    ]
    
    query_lower = query.lower()
    
    for pattern in patterns:
        match = re.search(pattern, query_lower)
        if match:
            groups = match.groups()
            result = {}
            
            # Convert Act number (handle Roman numerals)
            act_str = groups[0]
            if act_str.isdigit():
                result['act'] = int(act_str)
            else:
                # Roman numeral conversion
                roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5}
                result['act'] = roman_map.get(act_str.upper(), None)
            
            # Convert Scene number if present
            if len(groups) > 1:
                scene_str = groups[1]
                if scene_str.isdigit():
                    result['scene'] = int(scene_str)
                else:
                    roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5}
                    result['scene'] = roman_map.get(scene_str.upper(), None)
            
            if result.get('act'):
                logger.info(f"Detected Act/Scene reference in query: {result}")
                return result
    
    return None


class RAGPipeline:
    """Main RAG pipeline for question answering"""
    
    def __init__(self, vector_store: VectorStore):
        """
        Initialize the RAG pipeline
        
        Args:
            vector_store: Initialized VectorStore instance
        """
        self.vector_store = vector_store
        self.client = self._initialize_gemini()
        logger.info("RAG Pipeline initialized")
    
    def _initialize_gemini(self):
        """Initialize the Gemini API client"""
        logger.info(f"Using Google Gemini model: {LLM_MODEL}")
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not set in environment variables")
        return genai.Client(api_key=GOOGLE_API_KEY)
    
    def retrieve_context(
        self,
        query: str,
        top_k: int = None,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Retrieve relevant context from vector store with smart filtering
        
        Args:
            query: User's question
            top_k: Number of results to retrieve
            filter_metadata: Optional metadata filters
            
        Returns:
            List of retrieved chunks with metadata
        """
        top_k = top_k or TOP_K_RESULTS
        
        # Auto-detect Act/Scene references if no explicit filter provided
        if not filter_metadata:
            act_scene = extract_act_scene(query)
            if act_scene:
                # Build ChromaDB filter
                if 'scene' in act_scene:
                    filter_metadata = {
                        '$and': [
                            {'act': act_scene['act']},
                            {'scene': act_scene['scene']}
                        ]
                    }
                    logger.info(f"Filtering by Act {act_scene['act']}, Scene {act_scene['scene']}")
                else:
                    filter_metadata = {'act': act_scene['act']}
                    logger.info(f"Filtering by Act {act_scene['act']}")
        
        # Query vector store
        results = self.vector_store.query(
            query_text=query,
            top_k=top_k,
            filter_metadata=filter_metadata
        )
        
        # Format results
        chunks = []
        for doc, meta, distance, chunk_id in zip(
            results['documents'],
            results['metadatas'],
            results['distances'],
            results['ids']
        ):
            chunks.append({
                'text': doc,
                'metadata': meta,
                'distance': distance,
                'chunk_id': chunk_id
            })
        
        return chunks
    
    def generate_answer(self, prompt: str) -> str:
        """
        Generate answer using Gemini API
        
        Args:
            prompt: Complete prompt with context and question
            
        Returns:
            Generated answer
        """
        try:
            response = self.client.models.generate_content(
                model=LLM_MODEL,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return f"I apologize, but I encountered an error generating the answer: {str(e)}"
    
    def query(
        self,
        question: str,
        top_k: int = None,
        include_sources: bool = True
    ) -> Dict:
        """
        Complete RAG query pipeline
        
        Args:
            question: User's question
            top_k: Number of context chunks to retrieve
            include_sources: Whether to include source citations
            
        Returns:
            Dictionary with answer and sources
        """
        logger.info(f"Processing query: {question[:100]}...")
        
        # Step 1: Retrieve relevant context
        chunks = self.retrieve_context(question, top_k)
        
        if not chunks:
            return {
                'answer': "I apologize, but I couldn't find relevant information in the play to answer your question.",
                'sources': [],
                'confidence': 0.0
            }
        
        # Step 2: Build context
        context = create_context_from_chunks(chunks)
        
        # Step 3: Create prompt
        prompt = create_rag_prompt(context, question)
        
        # Step 4: Generate answer
        answer = self.generate_answer(prompt)
        
        # Step 5: Format response
        response = {
            'answer': answer,
            'sources': [],
            'confidence': self._calculate_confidence(chunks)
        }
        
        if include_sources:
            response['sources'] = [
                {
                    'chunk': chunk['text'],
                    'metadata': chunk['metadata'],
                    'relevance_score': 1.0 - chunk['distance']
                }
                for chunk in chunks
            ]
        
        logger.info("Query processed successfully")
        return response
    
    def _calculate_confidence(self, chunks: List[Dict]) -> float:
        """
        Calculate confidence score based on retrieval quality
        
        Args:
            chunks: Retrieved chunks
            
        Returns:
            Confidence score between 0 and 1
        """
        if not chunks:
            return 0.0
        
        # Use average relevance (inverse of distance)
        avg_relevance = sum(1.0 - chunk['distance'] for chunk in chunks) / len(chunks)
        return min(max(avg_relevance, 0.0), 1.0)
    
    def batch_query(self, questions: List[str], top_k: int = None) -> List[Dict]:
        """
        Process multiple questions
        
        Args:
            questions: List of questions
            top_k: Number of context chunks per question
            
        Returns:
            List of response dictionaries
        """
        logger.info(f"Processing batch of {len(questions)} questions")
        responses = []
        
        for i, question in enumerate(questions, 1):
            logger.info(f"Processing question {i}/{len(questions)}")
            response = self.query(question, top_k)
            response['question'] = question
            responses.append(response)
        
        return responses


def create_rag_pipeline(vector_store: VectorStore = None) -> RAGPipeline:
    """
    Factory function to create a RAG pipeline
    
    Args:
        vector_store: Optional VectorStore instance
        
    Returns:
        Initialized RAGPipeline
    """
    if vector_store is None:
        from vector_store import initialize_vector_store
        vector_store = initialize_vector_store()
    
    return RAGPipeline(vector_store)


if __name__ == "__main__":
    # Test the RAG pipeline
    print("Initializing RAG pipeline...")
    
    from vector_store import initialize_vector_store
    vs = initialize_vector_store()
    pipeline = create_rag_pipeline(vs)
    
    # Test query
    print("\nTesting query...")
    test_question = "What does the Soothsayer say to Caesar?"
    result = pipeline.query(test_question)
    
    print(f"\nQuestion: {test_question}")
    print(f"\nAnswer: {result['answer']}")
    print(f"\nConfidence: {result['confidence']:.2f}")
    print(f"\nNumber of sources: {len(result['sources'])}")
