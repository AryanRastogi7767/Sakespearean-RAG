"""
Evaluation script with rate limiting and retry logic for API calls
"""
import json
import logging
import time
from typing import List, Dict
from pathlib import Path
from datetime import datetime

from src.config import EVALUATION_FILE
from src.rag_pipeline import create_rag_pipeline
from src.vector_store import initialize_vector_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGEvaluatorWithRetry:
    """Evaluator for the RAG system with rate limiting"""
    
    def __init__(self, rag_pipeline, evaluation_file: str = None, delay_between_calls: float = 2.0):
        """
        Initialize the evaluator
        
        Args:
            rag_pipeline: Initialized RAG pipeline
            evaluation_file: Path to evaluation questions file
            delay_between_calls: Seconds to wait between API calls
        """
        self.rag_pipeline = rag_pipeline
        self.evaluation_file = evaluation_file or str(EVALUATION_FILE)
        self.delay = delay_between_calls
        self.results = []
    
    def load_evaluation_questions(self) -> List[Dict]:
        """Load evaluation questions from file"""
        logger.info(f"Loading evaluation questions from {self.evaluation_file}")
        with open(self.evaluation_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        logger.info(f"Loaded {len(questions)} questions")
        return questions
    
    def evaluate_single_question(self, question_obj: Dict, retry_count: int = 3) -> Dict:
        """
        Evaluate a single question with retry logic
        
        Args:
            question_obj: Question dictionary from evaluation file
            retry_count: Number of retries on failure
            
        Returns:
            Evaluation result dictionary
        """
        question = question_obj['question']
        logger.info(f"Evaluating: {question[:80]}...")
        
        for attempt in range(retry_count):
            try:
                # Get system response
                response = self.rag_pipeline.query(question, top_k=5)
                
                result = {
                    'id': question_obj.get('id'),
                    'category': question_obj.get('category', 'unknown'),
                    'difficulty': question_obj.get('difficulty', 'unknown'),
                    'question': question,
                    'ideal_answer': question_obj.get('ideal_answer', ''),
                    'system_answer': response['answer'],
                    'confidence': response['confidence'],
                    'num_sources': len(response['sources']),
                    'sources': response['sources'],
                    'success': True
                }
                
                # Add delay between successful calls to avoid rate limits
                time.sleep(self.delay)
                return result
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Attempt {attempt + 1}/{retry_count} failed: {error_msg}")
                
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    # Rate limit hit, wait longer
                    wait_time = (attempt + 1) * 5  # Exponential backoff
                    logger.info(f"Rate limit hit, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                elif attempt < retry_count - 1:
                    time.sleep(2)
                else:
                    # Final failure
                    logger.error(f"Failed after {retry_count} attempts: {e}")
                    return {
                        'id': question_obj.get('id'),
                        'category': question_obj.get('category', 'unknown'),
                        'difficulty': question_obj.get('difficulty', 'unknown'),
                        'question': question,
                        'ideal_answer': question_obj.get('ideal_answer', ''),
                        'system_answer': 'ERROR: ' + error_msg,
                        'confidence': 0.0,
                        'num_sources': 0,
                        'sources': [],
                        'success': False,
                        'error': error_msg
                    }
        
        return None
    
    def evaluate_all(self, max_questions: int = None) -> List[Dict]:
        """
        Evaluate all questions in the testbed
        
        Args:
            max_questions: Optional limit on number of questions to evaluate
            
        Returns:
            List of evaluation results
        """
        questions = self.load_evaluation_questions()
        if max_questions:
            questions = questions[:max_questions]
            logger.info(f"Limiting evaluation to first {max_questions} questions")
        
        self.results = []
        
        logger.info(f"Starting evaluation of {len(questions)} questions...")
        logger.info(f"Using {self.delay}s delay between calls to avoid rate limits")
        
        for i, question_obj in enumerate(questions, 1):
            logger.info(f"Progress: {i}/{len(questions)}")
            result = self.evaluate_single_question(question_obj)
            if result:
                self.results.append(result)
        
        logger.info("Evaluation complete!")
        return self.results
    
    def save_results(self, output_file: str):
        """Save results as JSON"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to {output_file}")


def run_evaluation_with_retry(max_questions: int = 10, delay: float = 3.0):
    """
    Run evaluation with rate limiting
    
    Args:
        max_questions: Maximum number of questions to evaluate (None for all)
        delay: Delay between API calls in seconds
    """
    logger.info("Starting RAG system evaluation with rate limiting...")
    
    # Initialize pipeline
    logger.info("Initializing RAG pipeline...")
    vector_store = initialize_vector_store()
    rag_pipeline = create_rag_pipeline(vector_store)
    
    # Create evaluator
    evaluator = RAGEvaluatorWithRetry(rag_pipeline, delay_between_calls=delay)
    
    # Run evaluation
    logger.info("Running evaluation...")
    results = evaluator.evaluate_all(max_questions=max_questions)
    
    # Calculate metrics
    total = len(results)
    successful = sum(1 for r in results if r.get('success', False))
    avg_confidence = sum(r.get('confidence', 0) for r in results if r.get('success', False)) / max(successful, 1)
    
    logger.info(f"\nEvaluation Metrics:")
    logger.info(f"  Total Questions: {total}")
    logger.info(f"  Successful: {successful}")
    logger.info(f"  Failed: {total - successful}")
    logger.info(f"  Success Rate: {successful/total*100:.1f}%")
    logger.info(f"  Avg Confidence: {avg_confidence:.3f}")
    
    # Save detailed results
    results_file = Path(__file__).parent.parent / "reports" / "evaluation_results_llm.json"
    results_file.parent.mkdir(exist_ok=True)
    evaluator.save_results(str(results_file))
    
    logger.info(f"\nEvaluation complete!")
    logger.info(f"  Results: {results_file}")
    
    return results


if __name__ == "__main__":
    # Run on ALL 35 questions with 3 second delay
    results = run_evaluation_with_retry(max_questions=None, delay=3.0)
