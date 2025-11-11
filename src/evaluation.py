"""
Evaluation script for the RAG system
"""
import json
import logging
from typing import List, Dict
from pathlib import Path
import pandas as pd
from datetime import datetime

from .config import EVALUATION_FILE
from .rag_pipeline import create_rag_pipeline
from .vector_store import initialize_vector_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGEvaluator:
    """Evaluator for the RAG system"""
    
    def __init__(self, rag_pipeline, evaluation_file: str = None):
        """
        Initialize the evaluator
        
        Args:
            rag_pipeline: Initialized RAG pipeline
            evaluation_file: Path to evaluation questions file
        """
        self.rag_pipeline = rag_pipeline
        self.evaluation_file = evaluation_file or str(EVALUATION_FILE)
        self.results = []
    
    def load_evaluation_questions(self) -> List[Dict]:
        """Load evaluation questions from file"""
        logger.info(f"Loading evaluation questions from {self.evaluation_file}")
        with open(self.evaluation_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        logger.info(f"Loaded {len(questions)} questions")
        return questions
    
    def evaluate_single_question(self, question_obj: Dict) -> Dict:
        """
        Evaluate a single question
        
        Args:
            question_obj: Question dictionary from evaluation file
            
        Returns:
            Evaluation result dictionary
        """
        question = question_obj['question']
        logger.info(f"Evaluating: {question[:100]}...")
        
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
                'sources': response['sources']
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating question: {e}")
            return {
                'id': question_obj.get('id'),
                'category': question_obj.get('category', 'unknown'),
                'question': question,
                'error': str(e)
            }
    
    def evaluate_all(self) -> List[Dict]:
        """
        Evaluate all questions in the testbed
        
        Returns:
            List of evaluation results
        """
        questions = self.load_evaluation_questions()
        self.results = []
        
        logger.info(f"Starting evaluation of {len(questions)} questions...")
        
        for i, question_obj in enumerate(questions, 1):
            logger.info(f"Progress: {i}/{len(questions)}")
            result = self.evaluate_single_question(question_obj)
            self.results.append(result)
        
        logger.info("Evaluation complete!")
        return self.results
    
    def calculate_metrics(self) -> Dict:
        """
        Calculate evaluation metrics
        
        Returns:
            Dictionary of metrics
        """
        if not self.results:
            logger.warning("No results to calculate metrics from")
            return {}
        
        # Basic statistics
        total_questions = len(self.results)
        successful = sum(1 for r in self.results if 'error' not in r)
        failed = total_questions - successful
        
        # Confidence statistics
        confidences = [r['confidence'] for r in self.results if 'confidence' in r]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Category breakdown
        categories = {}
        for result in self.results:
            cat = result.get('category', 'unknown')
            if cat not in categories:
                categories[cat] = {'total': 0, 'avg_confidence': []}
            categories[cat]['total'] += 1
            if 'confidence' in result:
                categories[cat]['avg_confidence'].append(result['confidence'])
        
        # Calculate average confidence per category
        for cat in categories:
            conf_list = categories[cat]['avg_confidence']
            categories[cat]['avg_confidence'] = sum(conf_list) / len(conf_list) if conf_list else 0
        
        metrics = {
            'total_questions': total_questions,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / total_questions if total_questions > 0 else 0,
            'average_confidence': avg_confidence,
            'min_confidence': min(confidences) if confidences else 0,
            'max_confidence': max(confidences) if confidences else 0,
            'categories': categories
        }
        
        return metrics
    
    def generate_report(self, output_file: str = None) -> str:
        """
        Generate a markdown evaluation report
        
        Args:
            output_file: Optional file to write report to
            
        Returns:
            Report as markdown string
        """
        metrics = self.calculate_metrics()
        
        report_lines = [
            "# RAG System Evaluation Report",
            f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## 1. Executive Summary\n",
            f"- **Total Questions:** {metrics['total_questions']}",
            f"- **Successful:** {metrics['successful']}",
            f"- **Failed:** {metrics['failed']}",
            f"- **Success Rate:** {metrics['success_rate']:.2%}",
            f"- **Average Confidence:** {metrics['average_confidence']:.3f}",
            "\n## 2. Performance by Category\n",
        ]
        
        # Category table
        report_lines.append("| Category | Total Questions | Avg Confidence |")
        report_lines.append("|----------|----------------|----------------|")
        for cat, data in metrics['categories'].items():
            report_lines.append(
                f"| {cat.capitalize()} | {data['total']} | {data['avg_confidence']:.3f} |"
            )
        
        # Sample responses
        report_lines.append("\n## 3. Sample Responses\n")
        
        # Best performing (highest confidence)
        sorted_results = sorted(
            [r for r in self.results if 'confidence' in r],
            key=lambda x: x['confidence'],
            reverse=True
        )
        
        if sorted_results:
            report_lines.append("### 3.1 High Confidence Response\n")
            best = sorted_results[0]
            report_lines.extend([
                f"**Question:** {best['question']}",
                f"\n**System Answer:**",
                f"\n{best['system_answer']}",
                f"\n**Confidence:** {best['confidence']:.3f}",
                "\n---\n"
            ])
        
        # Lowest performing
        if len(sorted_results) > 1:
            report_lines.append("### 3.2 Low Confidence Response\n")
            worst = sorted_results[-1]
            report_lines.extend([
                f"**Question:** {worst['question']}",
                f"\n**System Answer:**",
                f"\n{worst['system_answer']}",
                f"\n**Confidence:** {worst['confidence']:.3f}",
                "\n---\n"
            ])
        
        # Detailed results
        report_lines.append("\n## 4. Detailed Results\n")
        for result in self.results:
            if 'error' in result:
                report_lines.append(f"\n### Question {result['id']}: ❌ ERROR\n")
                report_lines.append(f"**Question:** {result['question']}")
                report_lines.append(f"\n**Error:** {result['error']}\n")
            else:
                report_lines.append(f"\n### Question {result['id']}: {result['question']}\n")
                report_lines.append(f"**Category:** {result['category']} | **Difficulty:** {result['difficulty']}")
                report_lines.append(f"\n**System Answer:**")
                report_lines.append(f"\n{result['system_answer']}")
                report_lines.append(f"\n**Confidence:** {result['confidence']:.3f}")
                report_lines.append(f"\n**Sources Used:** {result['num_sources']}")
                report_lines.append("\n---\n")
        
        report = "\n".join(report_lines)
        
        # Write to file if specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"Report written to {output_file}")
        
        return report
    
    def save_results(self, output_file: str):
        """Save results as JSON"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to {output_file}")


def run_evaluation():
    """Main evaluation function"""
    logger.info("Starting RAG system evaluation...")
    
    # Initialize pipeline
    logger.info("Initializing RAG pipeline...")
    vector_store = initialize_vector_store()
    rag_pipeline = create_rag_pipeline(vector_store)
    
    # Create evaluator
    evaluator = RAGEvaluator(rag_pipeline)
    
    # Run evaluation
    logger.info("Running evaluation...")
    results = evaluator.evaluate_all()
    
    # Calculate metrics
    metrics = evaluator.calculate_metrics()
    logger.info(f"\nEvaluation Metrics:")
    logger.info(f"  Success Rate: {metrics['success_rate']:.2%}")
    logger.info(f"  Avg Confidence: {metrics['average_confidence']:.3f}")
    
    # Generate report
    report_file = Path(__file__).parent.parent / "EVALUATION.md"
    evaluator.generate_report(output_file=str(report_file))
    
    # Save detailed results
    results_file = Path(__file__).parent.parent / "evaluation_results.json"
    evaluator.save_results(str(results_file))
    
    logger.info(f"\nEvaluation complete!")
    logger.info(f"  Report: {report_file}")
    logger.info(f"  Results: {results_file}")


if __name__ == "__main__":
    run_evaluation()
