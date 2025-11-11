#!/bin/bash

# This script builds, starts, and validates the RAG system.

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print a formatted step
step() {
    echo -e "\n${YELLOW}➡️  $1...${NC}"
}

# Function to print a success message
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to print an error message
error() {
    echo -e "${RED}❌ $1${NC}"
}

# --- Main Script ---

echo -e "${GREEN}--- 🎭 Shakespearean Scholar RAG System Startup ---${NC}"

# 1. Check for prerequisites
step "Checking prerequisites"
if ! command -v docker &> /dev/null; then
    error "Docker is not installed. Please install it to continue."
    exit 1
fi
if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose is not installed. Please install it to continue."
    exit 1
fi
if [ ! -f .env ]; then
    error ".env file not found. Please copy .env.example to .env and add your API key."
    exit 1
fi
if grep -q "your_actual_api_key_here" .env; then
    error "Placeholder API key found in .env. Please add a real Google Gemini API key."
    exit 1
fi
success "All prerequisites met."

# 2. Build and start services
step "Building and starting Docker containers"
docker-compose up -d --build
if [ $? -ne 0 ]; then
    error "Docker Compose failed to start. Please check the logs above."
    exit 1
fi
success "All services started."

# 3. Wait for services to become ready
step "Waiting for services to become ready (up to 2 minutes)"
max_wait=120
waited=0
backend_ready=false
frontend_ready=false

while [ $waited -lt $max_wait ]; do
    # Check if backend is responding
    if [ "$backend_ready" = false ]; then
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            backend_ready=true
        fi
    fi
    
    # Check if frontend is responding
    if [ "$frontend_ready" = false ]; then
        if curl -s http://localhost:8501/_stcore/health > /dev/null 2>&1; then
            frontend_ready=true
        fi
    fi
    
    # Break if both are ready
    if [ "$backend_ready" = true ] && [ "$frontend_ready" = true ]; then
        break
    fi
    
    echo -n "."
    sleep 2
    waited=$((waited + 2))
done

echo "" # Newline after dots

if [ "$backend_ready" = false ] || [ "$frontend_ready" = false ]; then
    if [ "$backend_ready" = false ]; then
        error "Backend did not become ready in time. Please check logs:"
        echo "  docker-compose logs backend"
    fi
    if [ "$frontend_ready" = false ]; then
        error "Frontend did not become ready in time. Please check logs:"
        echo "  docker-compose logs frontend"
    fi
    exit 1
fi
success "Backend and Frontend are ready."

# 4. Run validation checks
step "Running validation checks"

# Check backend health endpoint
echo -n "   - Checking backend health... "
backend_response=$(curl -s http://localhost:8000/health)
if [[ $(echo "$backend_response" | jq -r '.status') == "healthy" ]]; then
    success "OK"
else
    error "FAIL"
    exit 1
fi

# Check vector store count
echo -n "   - Checking vector store... "
chunk_count=$(echo "$backend_response" | jq -r '.vector_store_count')
if [ "$chunk_count" -gt 0 ]; then
    success "$chunk_count chunks loaded."
else
    error "FAIL (0 chunks found)"
    exit 1
fi

# Check frontend accessibility
echo -n "   - Checking frontend UI... "
if curl -s http://localhost:8501 | grep -q "Streamlit"; then
    success "OK"
else
    error "FAIL"
    exit 1
fi

# 5. Final success message
echo -e "\n${GREEN}--- 🎉 System is LIVE! ---${NC}"
echo ""
echo "You can now access the application:"
echo -e "  - ${YELLOW}Frontend UI:${NC}      http://localhost:8501"
echo -e "  - ${YELLOW}Backend API Docs:${NC} http://localhost:8000/docs"
echo -e "  - ${YELLOW}ChromaDB UI:${NC}      http://localhost:8001"
echo ""
echo "To stop the application, run: ${YELLOW}docker-compose down${NC}"
echo ""
echo -e "${GREEN}---------------------------------${NC}"
