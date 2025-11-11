"""
FastAPI application for the Shakespearean Scholar RAG system
"""
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

from .rag_pipeline import create_rag_pipeline
from .vector_store import initialize_vector_store
from .config import EMBEDDING_MODEL, CHROMA_COLLECTION_NAME

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="The Shakespearean Scholar API",
    description="RAG system for answering questions about Julius Caesar",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global RAG pipeline
rag_pipeline = None


# Pydantic models
class QueryRequest(BaseModel):
    """Request model for query endpoint"""
    query: str = Field(..., description="The question to ask about Julius Caesar")
    top_k: Optional[int] = Field(5, description="Number of context chunks to retrieve", ge=1, le=20)
    include_sources: Optional[bool] = Field(True, description="Whether to include source citations")


class SourceInfo(BaseModel):
    """Model for source citation information"""
    chunk: str
    metadata: Dict
    relevance_score: float


class QueryResponse(BaseModel):
    """Response model for query endpoint"""
    answer: str
    sources: List[SourceInfo]
    confidence: float


class BatchQueryRequest(BaseModel):
    """Request model for batch query endpoint"""
    queries: List[str] = Field(..., description="List of questions to ask")
    top_k: Optional[int] = Field(5, description="Number of context chunks per query", ge=1, le=20)


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    message: str
    vector_store_count: int


class StatsResponse(BaseModel):
    """Response model for stats endpoint"""
    total_chunks: int
    collection_name: str
    embedding_model: str


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the RAG pipeline on startup"""
    global rag_pipeline
    try:
        logger.info("Initializing RAG pipeline...")
        vector_store = initialize_vector_store()
        rag_pipeline = create_rag_pipeline(vector_store)
        logger.info("RAG pipeline initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG pipeline: {e}")
        raise


# API Endpoints
@app.get("/", tags=["General"])
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to The Shakespearean Scholar API",
        "documentation": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """Health check endpoint"""
    if rag_pipeline is None:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    
    try:
        count = rag_pipeline.vector_store.collection.count()
        return HealthResponse(
            status="healthy",
            message="All systems operational",
            vector_store_count=count
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@app.get("/stats", response_model=StatsResponse, tags=["General"])
async def get_stats():
    """Get system statistics"""
    if rag_pipeline is None:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    
    try:
        return StatsResponse(
            total_chunks=rag_pipeline.vector_store.collection.count(),
            collection_name=CHROMA_COLLECTION_NAME,
            embedding_model=EMBEDDING_MODEL
        )
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.post("/query", response_model=QueryResponse, tags=["RAG"])
async def query_rag(request: QueryRequest):
    """
    Main query endpoint for the RAG system
    
    Ask questions about Julius Caesar and get answers with citations.
    """
    if rag_pipeline is None:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        logger.info(f"Processing query: {request.query[:100]}...")
        
        result = rag_pipeline.query(
            question=request.query,
            top_k=request.top_k,
            include_sources=request.include_sources
        )
        
        return QueryResponse(
            answer=result['answer'],
            sources=[SourceInfo(**source) for source in result['sources']],
            confidence=result['confidence']
        )
    
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.post("/batch_query", tags=["RAG"])
async def batch_query(request: BatchQueryRequest):
    """
    Batch query endpoint for processing multiple questions
    """
    if rag_pipeline is None:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    
    if not request.queries:
        raise HTTPException(status_code=400, detail="Queries list cannot be empty")
    
    if len(request.queries) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 queries allowed per batch")
    
    try:
        logger.info(f"Processing batch of {len(request.queries)} queries")
        
        results = rag_pipeline.batch_query(
            questions=request.queries,
            top_k=request.top_k
        )
        
        return {
            "results": results,
            "total": len(results)
        }
    
    except Exception as e:
        logger.error(f"Error processing batch query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing batch query: {str(e)}")


@app.get("/search", tags=["RAG"])
async def search_chunks(
    query: str,
    top_k: int = 10,
    act: Optional[int] = None,
    scene: Optional[int] = None,
    speaker: Optional[str] = None
):
    """
    Search for chunks with optional metadata filters
    """
    if rag_pipeline is None:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    
    try:
        # Build filter
        filter_metadata = {}
        if act is not None:
            filter_metadata['act'] = act
        if scene is not None:
            filter_metadata['scene'] = scene
        if speaker is not None:
            filter_metadata['speaker'] = speaker
        
        chunks = rag_pipeline.retrieve_context(
            query=query,
            top_k=top_k,
            filter_metadata=filter_metadata if filter_metadata else None
        )
        
        return {
            "query": query,
            "filters": filter_metadata,
            "results": chunks,
            "count": len(chunks)
        }
    
    except Exception as e:
        logger.error(f"Error searching chunks: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    from config import API_HOST, API_PORT
    
    uvicorn.run(
        "api:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )
