# The Shakespearean Scholar - RAG System

> A containerized Retrieval-Augmented Generation (RAG) system that functions as an expert AI tutor on William Shakespeare's "The Tragedy of Julius Caesar."

**Course**: Advanced Natural Language Processing  
**Assignment**: A2 - RAG System Implementation  
**Deadline**: November 15, 2025  

**Members:**
- MT2024026 - Aryan Rastogi
- MT2024066 - Harshal Gujarathi
- MT2024091 - Mohit Sharma

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [API Documentation](#-api-documentation)
- [Evaluation](#-evaluation)
- [Development](#-development)
- [Troubleshooting](#-troubleshooting)

---

## 🎯 Overview

This project implements a complete RAG (Retrieval-Augmented Generation) system designed to answer questions about Shakespeare's "Julius Caesar" with the persona of an expert Shakespearean scholar suitable for ICSE Class 10 students.

### Key Features

-  **Semantic Search**: ChromaDB vector database with 150 hybrid-chunked segments
-  **LLM Generation**: Google Gemini 2.0 Flash for natural, contextual responses
-  **Enhanced Filtering**: Smart Act/Scene detection with regex-based metadata filtering
-  **Source Citations**: Every answer includes Act, Scene, and Speaker attribution
-  **RESTful API**: FastAPI backend with 5 comprehensive endpoints + health checks
-  **Interactive UI**: Streamlit frontend with 3-tab interface (Questions, Stats, Evaluation)
-  **Containerized**: Complete Docker Compose setup for one-command deployment
-  **Full Evaluation**: 35 questions evaluated with 100% success rate (563-line comprehensive report)

---

##  Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network (rag_network)            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │  Streamlit   │  HTTP   │   FastAPI    │                  │
│  │  Frontend    │────────►│   Backend    │                  │
│  │  Port 8501   │         │  Port 8000   │                  │
│  └──────────────┘         └──────┬───────┘                  │
│                                   │                         │
│                                   │ Vector Search           │
│                                   ▼                         │
│                          ┌──────────────┐                   │
│                          │  ChromaDB    │                   │
│                          │  Vector DB   │                   │
│                          │  Port 8001   │                   │
│                          └──────────────┘                   │
│                                                             │
│  Backend calls external Gemini API for generation           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Query** → Frontend/API receives user question
2. **Embed** → Query converted to vector embedding (all-MiniLM-L6-v2)
3. **Retrieve** → ChromaDB searches for top-k most relevant chunks
4. **Context** → Retrieved chunks formatted with metadata
5. **Generate** → Gemini LLM generates answer with citations
6. **Response** → Structured answer with sources returned to user

---

##  Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Vector DB** | ChromaDB | Vector storage and similarity search |
| **Embeddings** | all-MiniLM-L6-v2 | Text → Vector conversion (384 dims) |
| **LLM** | Google Gemini 2.0 Flash | Answer generation with context |
| **Backend** | FastAPI | REST API server (5 endpoints + health checks) |
| **Frontend** | Streamlit | Interactive web UI with 3-tab interface |
| **Containers** | Docker + Docker Compose | Service orchestration (3 services) |
| **ETL Pipeline** | Custom Python (parser.py) | Hybrid chunking (150 chunks, 5 types) |

---

##  Prerequisites

Before starting, ensure you have:

1. **Docker** (version 20.10+) and **Docker Compose** (version 2.0+)
   - [Install Docker Desktop](https://www.docker.com/products/docker-desktop/)
   
2. **Google Gemini API Key**
   - Get your key at [Google AI Studio](https://makersuite.google.com/app/apikey)

3. **Basic Requirements**
   - 4GB+ RAM available for containers
   - 2GB+ disk space for images and data
   - Internet connection for model downloads

---

##  Quick Start

### Method 1: Automated Setup (Recommended)

```bash
# 1. Clone the repository
git clone <repository-url>
cd A2

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env and add your API key
nano .env  # or use any text editor

# 4. Run the automated setup script
chmod +x startup.sh
./startup.sh
```

The script will:
- Build all Docker images
- Start all services (ChromaDB, Backend, Frontend)
- Wait for health checks to pass
- Validate the system is working
- Display access URLs

### Method 2: Manual Setup

```bash
# 1. Create and configure .env file
cp .env.example .env
echo "GOOGLE_API_KEY=your_actual_key_here" >> .env

# 2. Build and start services
docker-compose up -d

# 3. Wait for services to be ready (takes ~2-3 minutes)
docker-compose ps

# 4. Check health
curl http://localhost:8000/health
```

### Accessing the Application

After successful startup:

- **Frontend UI**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **ChromaDB**: http://localhost:8001

---

##  Project Structure

```
A2/
├── 📄 Documentation
│   ├── README.md                  # Main documentation (this file)
│   ├── PROJECT_STATUS.md          # Current project status
│   ├── PROJECT_PLAN.md            # Development plan reference
│   ├── FINAL_VERIFICATION.md      # Complete verification checklist
│   └── reports/
│       ├── EVALUATION.md          # Full LLM evaluation report (563 lines)
│       └── evaluation_results_llm.json # Detailed evaluation data (35 questions)
│
├── 🐳 Docker & Deployment
│   ├── docker-compose.yml         # Service orchestration (3 services)
│   ├── Dockerfile                 # Backend container definition
│   ├── Dockerfile.streamlit       # Frontend container definition
│   └── startup.sh                 # Automated setup script
│
├── ⚙️ Configuration
│   ├── .env.example               # Environment template
│   ├── .env                       # Your config (git-ignored, ESSENTIAL)
│   ├── .gitignore                 # Git ignore patterns
│   ├── requirements.txt           # Backend dependencies (35 packages)
│   └── requirements_frontend.txt  # Frontend dependencies (5 packages)
│
├── 📊 Data Pipeline
│   ├── raw/
│   │   └── julius-caesar.json     # Source text from Folger Shakespeare
│   ├── processed/
│   │   ├── julius_caesar_clean.json       # Cleaned text
│   │   ├── julius_caesar_structured.jsonl # Structured scenes
│   │   └── chunks.jsonl                   # 150 hybrid chunks (FINAL)
│   └── evaluation.json            # 35 test questions (6 categories)
│
├── 💻 Source Code
│   ├── __init__.py                # Package initialization
│   ├── config.py                  # Centralized configuration (loads .env)
│   ├── vector_store.py            # ChromaDB management (pre-computed embeddings)
│   ├── prompts.py                 # LLM prompt templates (scholar persona)
│   ├── rag_pipeline.py            # Core RAG orchestration + Act/Scene filtering
│   ├── api.py                     # FastAPI backend (5 endpoints)
│   ├── frontend.py                # Streamlit UI (3-tab interface)
│   ├── evaluation.py              # Full evaluation script
│   ├── evaluation_with_retry.py   # Rate-limited evaluation (used for final run)
│   ├── generate_eval_report.py    # Evaluation report generator
│   └── etl/                       # ETL pipeline modules
│       ├── parser.py              # Main ETL parser (353 lines)
│       └── utils.py               # Utility functions
│
├── 📓 Notebooks
│   └── inference_demo.ipynb       # Live demo notebook
│
└── 🧪 Tests
    └── test_api.py                # API integration tests
```

---

##  API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints

#### 1. Health Check
```http
GET /health
```
Returns service health status and vector store connection.

**Response:**
```json
{
  "status": "healthy",
  "message": "All systems operational",
  "vector_store_count": 150
}
```

#### 2. Vector Store Statistics
```http
GET /stats
```
Returns statistics about the vector database.

**Response:**
```json
{
  "total_chunks": 150,
  "collection_name": "julius_caesar",
  "embedding_model": "all-MiniLM-L6-v2"
}
```

#### 3. Query (Main Endpoint)
```http
POST /query
Content-Type: application/json

{
  "query": "What does the Soothsayer say to Caesar?",
  "top_k": 5
}
```

**Response:**
```json
{
  "answer": "The Soothsayer warns Caesar to 'Beware the Ides of March'. This famous warning occurs in Act 1, Scene 2...",
  "confidence": 0.286,
  "sources": [
    {
      "chunk": "CAESAR: Who is it in the press that calls on me?...",
      "metadata": {
        "act": 1,
        "scene": 2,
        "speaker": "CAESAR",
        "chunk_type": "dialogue_exchange"
      },
      "relevance_score": 0.403
    }
  ],
  "query": "What does the Soothsayer say to Caesar?",
  "num_sources": 5
}
```

#### 4. Batch Query
```http
POST /batch_query
Content-Type: application/json

{
  "queries": [
    "What does Caesar say about Cassius?",
    "How does Brutus justify the assassination?"
  ],
  "top_k": 5
}
```

#### 5. Raw Search
```http
GET /search?query=Brutus&top_k=3
```
Performs vector search without LLM generation.

### Interactive API Documentation

Visit http://localhost:8000/docs for full Swagger UI documentation with:
- Request/response schemas
- Try-it-out functionality
- Model definitions

---

##  Evaluation

### Test Dataset

The system has been evaluated on 35 questions in `data/evaluation.json`:

**Question Distribution:**
- **25 Factual (71%)**: Basic plot, character, and event questions
- **4 Analytical (11%)**: Character analysis and interpretation
- **3 Thematic (9%)**: Abstract themes (fate vs. free will, power, loyalty)
- **1 Character (3%)**: Character motivation/development
- **1 Comparative (3%)**: Compare elements within play
- **1 Rhetorical (3%)**: Analyze rhetorical devices

**Difficulty Levels:**
- **20 Easy**: Direct textual evidence
- **10 Medium**: Requires some inference
- **5 Hard**: Complex synthesis across acts

### Evaluation Results

**Full evaluation completed on November 11, 2025:**

```
Total Questions:        35
Success Rate:           100% (35/35)
Average Confidence:     0.227
Evaluation Time:        ~2 minutes with rate limiting
Report:                 reports/EVALUATION.md (563 lines)
```

**Key Findings:**
-  100% success rate with robust retry logic
-  Strong performance on factual questions (avg confidence: 0.237)
-  Enhanced Act/Scene filtering working perfectly
-  Scholar persona provides proper citations
-  Thematic questions show lower confidence (0.040 avg) - expected for retrieval-based systems

### Running Evaluation

The evaluation has been completed, but you can re-run it:

```bash
# Full evaluation with rate limiting (recommended)
docker-compose exec backend python src/evaluation_with_retry.py

# Standard evaluation
docker-compose exec backend python src/evaluation.py
```

### Metrics

The evaluation report (`reports/EVALUATION.md`) includes:

**Quantitative Metrics:**
- Overall performance (success rate, confidence scores)
- Performance by category (6 categories)
- Performance by difficulty (easy/medium/hard)
- Retrieval metrics (175 total chunks retrieved)

**RAGAs-Style Qualitative Metrics:**
- **Faithfulness**: 4/5 - Answers grounded in context
- **Answer Relevancy**: 4/5 - Addresses questions directly
- **Context Recall**: 4/5 - Good retrieval of relevant chunks
- **Context Precision**: 3.5/5 - Retrieved chunks mostly relevant

**Sample Q&A Pairs:**
- 4 diverse examples with full analysis
- High, moderate, analytical, and thematic question responses
- Each includes confidence scores and quality assessment

**Qualitative Analysis:**
- Answer quality assessment (4 strengths, 4 weaknesses)
- Retrieval quality assessment
- Error analysis and mitigation strategies
- Comparison with ideal answers (51% exact match)

**Recommendations:**
- Short-term improvements (4 items)
- Medium-term improvements (4 items)
- Long-term improvements (5 items)

See `reports/EVALUATION.md` for the complete 563-line report with all sections.

---

##  Development

### Local Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GOOGLE_API_KEY="your-key-here"
export CHROMA_HOST="localhost"
export CHROMA_PORT="8001"

# Start ChromaDB separately
docker-compose up chromadb -d

# Run backend
python -m uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

# Run frontend (in another terminal)
streamlit run src/frontend.py
```

### Running Tests

```bash
# Run unit tests
python -m pytest tests/

# Run specific test
python tests/test_api.py
```

### Environment Variables

Create `.env` file with:

```bash
# Required
GOOGLE_API_KEY=your_gemini_api_key_here

# Embedding Model (default shown)
EMBEDDING_MODEL=all-MiniLM-L6-v2

# LLM Configuration
LLM_MODEL=gemini-2.0-flash
USE_OLLAMA=false

# RAG Settings
TOP_K_RESULTS=5

# ChromaDB Settings
CHROMA_HOST=chromadb
CHROMA_PORT=8000

# API Settings (defaults shown)
API_HOST=0.0.0.0
API_PORT=8000

# Backend URL for Frontend (Docker)
BACKEND_URL=http://backend:8000
```

---

##  Troubleshooting

### Services Won't Start

**Problem**: `docker-compose up` fails

**Solutions**:
```bash
# Check Docker is running
docker ps

# Rebuild images
docker-compose build --no-cache

# Check logs
docker-compose logs backend
docker-compose logs chromadb
```

### Port Already in Use

**Problem**: "Port 8000/8001/8501 is already allocated"

**Solution**:
```bash
# Find process using port
lsof -i :8000

# Kill process or change ports in docker-compose.yml
```

### Backend Startup Takes Long

**Problem**: Backend health check fails or takes 2-3 minutes

**Reason**: Embedding model download on first run (~80MB for all-MiniLM-L6-v2)

**Solution**: Wait for model download to complete. Check logs:
```bash
docker-compose logs -f backend
```

**Note**: After first run, model is cached and startup is fast (~10 seconds).

### API Key Issues

**Problem**: Gemini API errors

**Solutions**:
```bash
# Verify API key is set
docker-compose exec backend env | grep GOOGLE_API_KEY

# Test API key
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

### ChromaDB Connection Failed

**Problem**: "Failed to connect to ChromaDB service"

**Solution**:
```bash
# Restart ChromaDB
docker-compose restart chromadb

# Check ChromaDB is healthy
curl http://localhost:8001/api/v1/heartbeat
```

### No Vector Data

**Problem**: "Collection is empty" or vector store errors

**Solution**:
```bash
# Check chunks file exists
ls -lh data/processed/chunks.jsonl

# Should show: 150 chunks
wc -l data/processed/chunks.jsonl

# Restart backend to re-index
docker-compose restart backend

# Verify vector store has data
curl http://localhost:8000/stats
# Should return: {"total_chunks": 150, ...}
```

---

## 📚 Additional Resources

- **Verification Report**: See `FINAL_VERIFICATION.md` for complete project verification
- **Evaluation Report**: See `reports/EVALUATION.md` for comprehensive evaluation (563 lines)
- **Project Status**: See `PROJECT_STATUS.md` for detailed implementation status
- **Project Plan**: See `PROJECT_PLAN.md` for detailed implementation guidance
- **API Documentation**: http://localhost:8000/docs (when running)
- **ChromaDB Docs**: https://docs.trychroma.com/
- **Gemini API**: https://ai.google.dev/docs

---

##  Implementation Notes

### Chunking Strategy

The system uses **hybrid chunking** with 5 types:

**Chunk Distribution (150 total):**
- **127 dialogue_exchange (85%)**: Multi-turn character conversations
- **16 scene_summary (11%)**: Opening context for each scene
- **4 famous_quote (3%)**: Memorable standalone lines
- **2 major_speech (1%)**: Extended monologues/speeches
- **1 soliloquy (1%)**: Character introspection

**Metadata per chunk:**
- Act number (1-5)
- Scene number (1-N)
- Speaker(s) array
- Chunk type
- Chunk ID
- Text content

This enables precise Act/Scene filtering for structural queries.

### Enhanced Act/Scene Filtering

**Smart Detection:**
- Regex patterns detect: "Act 3 Scene 1", "act 3, scene 1", "Act III Scene I"
- Auto-applies metadata filter: `{'$and': [{'act': 3}, {'scene': 1}]}`
- Handles various query formats automatically

**Example:**
```
Query: "What happens in Act 3 Scene 1?"
→ Detected: Act=3, Scene=1
→ Filter applied to ChromaDB query
→ Result: All 5 sources from Act 3 Scene 1 (100% accuracy)
```

### Prompt Engineering

System prompt designed to:
- Maintain expert Shakespearean scholar persona
- Target ICSE Class 10 comprehension level
- Enforce citation requirements (Act/Scene/Speaker)
- Prevent hallucination by grounding in context
- Explain archaic language when needed

### Model Selection

- **Embedding Model**: `all-MiniLM-L6-v2` (384 dimensions)
  - Fast download (~80MB) and inference
  - Good quality for English text
  - Lower memory footprint than larger models
  - Pre-computed embeddings avoid ONNX download issues
  
- **LLM**: Google Gemini 2.0 Flash
  - Fast response times (~2-3 seconds)
  - Good instruction following
  - Strong citation capabilities
  - Handles rate limiting with retry logic (3 attempts, exponential backoff)

---

##  Project Completion Status

###  System Statistics

- **150 Chunks**: 5 types across all 5 acts
- **35 Questions Evaluated**: 100% success rate
- **5 API Endpoints**: All operational with health checks
- **3 Docker Services**: backend (healthy), chromadb, frontend
- **3,030 Lines of Documentation**: README, PROJECT_STATUS, PROJECT_PLAN, EVALUATION

###  Key Achievements

-  Enhanced Act/Scene filtering with regex detection
-  Pre-computed embeddings avoid ONNX download issues
-  Robust retry logic handles API rate limiting
-  100% evaluation success rate on 35 diverse questions
-  Comprehensive 563-line evaluation report
-  Scholar persona with proper citations verified

---

##  Contributing

This is an academic project. For questions or issues:
1. Check troubleshooting section
2. Review logs: `docker-compose logs`
3. Contact course TAs

---

## 📋 Quick Reference

### System URLs (when running)
- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ChromaDB**: http://localhost:8001

### Key Files
- **Setup**: `startup.sh` - One-command deployment
- **Configuration**: `.env` - API keys and settings
- **Evaluation**: `reports/EVALUATION.md` - 563-line report
- **Verification**: `FINAL_VERIFICATION.md` - Complete checklist
- **Status**: `PROJECT_STATUS.md` - Implementation details

### Quick Commands
```bash
# Start system
./startup.sh

# Check health
curl http://localhost:8000/health

# View logs
docker-compose logs -f backend

# Stop system
docker-compose down
```
