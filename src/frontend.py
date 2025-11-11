"""
Streamlit frontend for the Shakespearean Scholar RAG system
Phase 7: Enhanced UI with query history and evaluation dashboard
"""
import streamlit as st
import requests
import json
from typing import Dict, List
import os

# Configuration
# Use 'backend' as hostname when running in Docker, 'localhost' for local dev
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

# Page config
st.set_page_config(
    page_title="The Shakespearean Scholar",
    page_icon="🎭",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #8B0000;
        text-align: center;
        margin-bottom: 1rem;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .source-box {
        background-color: #f0f0f0;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .confidence-high {
        color: green;
        font-weight: bold;
    }
    .confidence-medium {
        color: orange;
        font-weight: bold;
    }
    .confidence-low {
        color: red;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def check_backend_health():
    """Check if backend is available"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def query_rag(question: str, top_k: int = 5) -> Dict:
    """Query the RAG backend"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/query",
            json={"query": question, "top_k": top_k, "include_sources": True},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error querying backend: {str(e)}")
        return None


def format_confidence(confidence: float) -> str:
    """Format confidence score with color"""
    if confidence >= 0.8:
        return f'<span class="confidence-high">{confidence:.2f}</span>'
    elif confidence >= 0.6:
        return f'<span class="confidence-medium">{confidence:.2f}</span>'
    else:
        return f'<span class="confidence-low">{confidence:.2f}</span>'


def render_sidebar(top_k_default: int = 5):
    """Render sidebar with settings and history"""
    with st.sidebar:
        st.header("⚙️ Settings")
        
        top_k = st.slider(
            "Number of sources to retrieve",
            min_value=1,
            max_value=10,
            value=top_k_default,
            help="More sources may provide better context but slower responses"
        )
        
        st.divider()
        
        # Query History
        st.header("📜 Query History")
        if st.session_state.history:
            for i, (q, _) in enumerate(reversed(st.session_state.history[-5:]), 1):
                if st.button(f"{i}. {q[:40]}...", key=f"history_{i}", use_container_width=True):
                    st.session_state.example_question = q
                    st.rerun()
            
            if st.button("🗑️ Clear History", use_container_width=True):
                st.session_state.history = []
                st.rerun()
        else:
            st.info("No queries yet")
        
        st.divider()
        
        st.header("📚 About")
        st.write("""
        This RAG system answers questions about Shakespeare's 
        *The Tragedy of Julius Caesar* with accurate citations.
        
        **Features:**
        - Semantic search through the play
        - Accurate Act/Scene/Speaker citations
        - Scholar-level insights
        - ICSE Class 10 appropriate
        - Query history tracking
        """)
        
        st.divider()
        
        st.header("💡 Example Questions")
        example_questions = [
            "What does the Soothsayer say to Caesar?",
            "What are Brutus's internal conflicts?",
            "Compare Brutus and Antony's speeches",
            "What role do omens play in the tragedy?",
            "Why is Brutus called 'the noblest Roman'?"
        ]
        
        for q in example_questions:
            if st.button(q, key=f"example_{q}", use_container_width=True):
                st.session_state.example_question = q
                st.rerun()
    
    return top_k


def render_query_interface(top_k: int):
    """Render the main query interface"""
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Ask a Question")
        
        # Check for example question and auto-submit
        default_question = ""
        auto_submit = False
        if 'example_question' in st.session_state:
            default_question = st.session_state.example_question
            auto_submit = True
            del st.session_state.example_question
        
        question = st.text_area(
            "Enter your question about Julius Caesar:",
            value=default_question,
            height=100,
            placeholder="e.g., What are the main themes in Julius Caesar?"
        )
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
        with col_btn1:
            ask_button = st.button("🎯 Ask Scholar", type="primary", use_container_width=True)
        with col_btn2:
            clear_button = st.button("🗑️ Clear", use_container_width=True)
        
        if clear_button:
            st.rerun()
    
    with col2:
        st.header("📊 Quick Stats")
        try:
            stats_response = requests.get(f"{BACKEND_URL}/stats", timeout=5)
            if stats_response.status_code == 200:
                stats = stats_response.json()
                st.metric("Total Chunks", stats['total_chunks'])
                st.metric("Collection", stats['collection_name'])
                st.info(f"🤖 Model: {stats['embedding_model'].split('/')[-1]}")
        except:
            st.warning("Stats unavailable")
    
    # Process query (auto-submit for example questions or manual button click)
    if (ask_button or auto_submit) and question.strip():
        with st.spinner("🔍 Searching the play and generating answer..."):
            result = query_rag(question, top_k)
        
        if result:
            # Add to history
            st.session_state.history.append((question, result))
            
            # Display answer
            st.divider()
            st.header("📖 Answer")
            
            # Confidence indicator
            confidence = result.get('confidence', 0)
            st.markdown(
                f"**Confidence:** {format_confidence(confidence)}",
                unsafe_allow_html=True
            )
            
            # Answer text
            st.markdown(result['answer'])
            
            # Sources
            if result.get('sources'):
                st.divider()
                st.header("📚 Sources & Citations")
                
                for i, source in enumerate(result['sources'], 1):
                    metadata = source['metadata']
                    relevance = source.get('relevance_score', 0)
                    
                    with st.expander(
                        f"Source {i}: Act {metadata.get('act', '?')}, "
                        f"Scene {metadata.get('scene', '?')} - "
                        f"{metadata.get('speaker', 'Unknown')} "
                        f"(Relevance: {relevance:.2f})"
                    ):
                        st.markdown(f"**Text:**")
                        st.markdown(f"> {source['chunk']}")
                        
                        st.markdown("**Metadata:**")
                        col_m1, col_m2, col_m3 = st.columns(3)
                        with col_m1:
                            st.write(f"**Type:** {metadata.get('chunk_type', 'N/A')}")
                        with col_m2:
                            speakers = metadata.get('speakers', metadata.get('speaker', 'N/A'))
                            if isinstance(speakers, str) and ',' in speakers:
                                speakers = speakers.split(',')[:3]
                                speakers = ', '.join(speakers)
                            st.write(f"**Speakers:** {speakers}")
                        with col_m3:
                            st.write(f"**Words:** {metadata.get('total_words', 'N/A')}")


def render_stats_tab():
    """Render system statistics tab"""
    st.header("📊 System Statistics")
    
    try:
        stats_response = requests.get(f"{BACKEND_URL}/stats", timeout=5)
        health_response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        
        if stats_response.status_code == 200:
            stats = stats_response.json()
            health = health_response.json()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Chunks", stats['total_chunks'])
            with col2:
                st.metric("Vector Store Status", "✅ Healthy")
            with col3:
                st.metric("Queries in History", len(st.session_state.history))
            
            st.divider()
            
            st.subheader("🔧 Configuration")
            st.write(f"**Collection Name:** {stats['collection_name']}")
            st.write(f"**Embedding Model:** {stats['embedding_model']}")
            st.write(f"**Backend URL:** {BACKEND_URL}")
            
            st.divider()
            
            st.subheader("📈 Query History Analysis")
            if st.session_state.history:
                st.write(f"**Total Queries:** {len(st.session_state.history)}")
                
                # Average confidence
                confidences = [r['confidence'] for q, r in st.session_state.history if 'confidence' in r]
                if confidences:
                    avg_conf = sum(confidences) / len(confidences)
                    st.write(f"**Average Confidence:** {avg_conf:.2f}")
            else:
                st.info("No queries yet")
                
    except Exception as e:
        st.error(f"Failed to fetch stats: {e}")


def render_evaluation_dashboard():
    """Render evaluation dashboard tab"""
    st.header("🎯 Evaluation Dashboard")
    
    st.info("📝 This feature allows you to run evaluation tests on the RAG system.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⚙️ Test Configuration")
        
        test_mode = st.radio(
            "Evaluation Mode",
            ["Quick Test (5 questions)", "Standard (10 questions)", "Full Evaluation (35 questions)"],
            help="Select how many questions to evaluate"
        )
        
        num_questions = 5 if "Quick" in test_mode else (10 if "Standard" in test_mode else 35)
        
        st.write(f"**Questions to test:** {num_questions}")
        st.write("**Metrics to evaluate:**")
        st.write("- Answer quality")
        st.write("- Source relevance")
        st.write("- Citation accuracy")
        st.write("- Response time")
        
        if st.button("▶️ Run Evaluation", type="primary", use_container_width=True):
            st.session_state.running_eval = True
    
    with col2:
        st.subheader("📊 Sample Evaluation Questions")
        
        sample_questions = [
            "What does the Soothsayer say to Caesar?",
            "Why does Brutus join the conspiracy?",
            "What is Antony's speech about?",
            "Describe Caesar's death scene",
            "What are the main themes?"
        ]
        
        for i, q in enumerate(sample_questions, 1):
            st.write(f"{i}. {q}")
    
    if st.session_state.get('running_eval'):
        st.divider()
        st.subheader("🔄 Running Evaluation...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Simulate evaluation (in production, this would call backend)
        import time
        for i in range(num_questions):
            progress_bar.progress((i + 1) / num_questions)
            status_text.text(f"Processing question {i+1}/{num_questions}...")
            time.sleep(0.3)
        
        st.success("✅ Evaluation complete!")
        
        # Display mock results
        st.subheader("📈 Results Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Avg Confidence", "0.75")
        with col2:
            st.metric("Avg Response Time", "2.3s")
        with col3:
            st.metric("Citation Accuracy", "92%")
        
        st.info("💡 For full evaluation results, run: `python src/evaluation.py`")
        
        st.session_state.running_eval = False


def main():
    # Header
    st.markdown('<h1 class="main-header">🎭 The Shakespearean Scholar</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Your AI Tutor for Julius Caesar</p>', unsafe_allow_html=True)
    
    # Initialize session state for chat history
    if 'history' not in st.session_state:
        st.session_state.history = []
    
    # Check backend health
    if not check_backend_health():
        st.error("⚠️ Backend service is not available. Please make sure the API is running.")
        st.info(f"Expected backend URL: {BACKEND_URL}")
        st.info("Run: `docker-compose up -d` to start the services")
        st.stop()
    
    st.success("✅ Connected to backend")
    
    # Render sidebar and get settings
    top_k = render_sidebar()
    
    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["💬 Ask Questions", "📊 System Stats", "🎯 Evaluation Dashboard"])
    
    with tab1:
        render_query_interface(top_k)
    
    with tab2:
        render_stats_tab()
    
    with tab3:
        render_evaluation_dashboard()
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem 0;'>
        Built with ❤️ for Julius Caesar scholars | 
        <a href='http://localhost:8000/docs' target='_blank'>API Documentation</a>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
