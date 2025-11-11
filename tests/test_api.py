"""
Quick test script to verify the RAG system is working
"""
import requests
import json

BACKEND_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        print(f"✅ Health: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_stats():
    """Test stats endpoint"""
    print("\nTesting stats endpoint...")
    try:
        response = requests.get(f"{BACKEND_URL}/stats", timeout=5)
        print(f"✅ Stats: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Stats check failed: {e}")
        return False

def test_query(question: str):
    """Test query endpoint"""
    print(f"\nTesting query: {question}")
    try:
        response = requests.post(
            f"{BACKEND_URL}/query",
            json={"query": question, "top_k": 3},
            timeout=30
        )
        result = response.json()
        
        print(f"✅ Query successful!")
        print(f"\nAnswer: {result['answer'][:200]}...")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Sources: {len(result['sources'])}")
        
        return True
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🎭 Testing The Shakespearean Scholar RAG System\n")
    print("=" * 60)
    
    # Test health
    if not test_health():
        print("\n❌ Backend is not available. Make sure Docker containers are running:")
        print("   docker-compose up -d")
        return
    
    # Test stats
    test_stats()
    
    # Test queries
    test_questions = [
        "What does the Soothsayer say to Caesar?",
        "What are Brutus's internal conflicts?",
        "Who is the noblest Roman of them all?"
    ]
    
    for question in test_questions:
        test_query(question)
        print("-" * 60)
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()
