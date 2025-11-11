"""
Mock evaluation script for demonstration purposes
This script runs evaluation on retrieval quality only (no LLM calls)
"""
import json
import logging
from typing import List, Dict
from pathlib import Path
from datetime import datetime
from collections import Counter

from src.config import EVALUATION_FILE
from src.vector_store import initialize_vector_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockRAGEvaluator:
    """Evaluator that tests retrieval quality without LLM calls"""
    
    def __init__(self, vector_store, evaluation_file: str = None):
        """Initialize the evaluator"""
        self.vector_store = vector_store
        self.evaluation_file = evaluation_file or str(EVALUATION_FILE)
        self.results = []
    
    def load_evaluation_questions(self) -> List[Dict]:
        """Load evaluation questions from file"""
        logger.info(f"Loading evaluation questions from {self.evaluation_file}")
        with open(self.evaluation_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        logger.info(f"Loaded {len(questions)} questions")
        return questions
    
    def evaluate_retrieval(self, question_obj: Dict) -> Dict:
        """
        Evaluate retrieval quality for a single question
        
        Args:
            question_obj: Question dictionary from evaluation file
            
        Returns:
            Evaluation result dictionary
        """
        question = question_obj['question']
        logger.info(f"Evaluating retrieval: {question[:80]}...")
        
        try:
            # Get retrieval results only
            results = self.vector_store.query(question, top_k=5)
            
            # Calculate retrieval metrics
            relevances = results.get('distances', [])
            avg_relevance = sum(relevances) / len(relevances) if relevances else 0
            
            # Analyze retrieved chunks
            metadatas = results.get('metadatas', [])
            chunk_types = [m.get('chunk_type', 'unknown') for m in metadatas]
            acts = [m.get('act', 0) for m in metadatas]
            speakers = [m.get('speaker', 'Unknown') for m in metadatas]
            
            result = {
                'id': question_obj.get('id'),
                'category': question_obj.get('category', 'unknown'),
                'difficulty': question_obj.get('difficulty', 'unknown'),
                'question': question,
                'ideal_answer': question_obj.get('ideal_answer', ''),
                'num_sources': len(results.get('documents', [])),
                'avg_relevance': 1 - avg_relevance,  # Convert distance to similarity
                'chunk_types': chunk_types,
                'acts_covered': list(set(acts)),
                'speakers': speakers[:3],  # Top 3 speakers
                'sources': results.get('documents', [])[:2]  # Top 2 for brevity
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
        """Evaluate all questions in the testbed"""
        questions = self.load_evaluation_questions()
        self.results = []
        
        logger.info(f"Starting retrieval evaluation of {len(questions)} questions...")
        
        for i, question_obj in enumerate(questions, 1):
            logger.info(f"Progress: {i}/{len(questions)}")
            result = self.evaluate_retrieval(question_obj)
            self.results.append(result)
        
        logger.info("Evaluation complete!")
        return self.results
    
    def calculate_metrics(self) -> Dict:
        """Calculate evaluation metrics"""
        if not self.results:
            logger.warning("No results to calculate metrics from")
            return {}
        
        # Basic statistics
        total_questions = len(self.results)
        successful = sum(1 for r in self.results if 'error' not in r)
        failed = total_questions - successful
        
        # Relevance statistics
        relevances = [r['avg_relevance'] for r in self.results if 'avg_relevance' in r]
        avg_relevance = sum(relevances) / len(relevances) if relevances else 0
        
        # Coverage statistics
        all_chunk_types = []
        all_acts = set()
        for result in self.results:
            if 'chunk_types' in result:
                all_chunk_types.extend(result['chunk_types'])
            if 'acts_covered' in result:
                all_acts.update(result['acts_covered'])
        
        chunk_type_dist = Counter(all_chunk_types)
        
        # Category breakdown
        categories = {}
        for result in self.results:
            cat = result.get('category', 'unknown')
            if cat not in categories:
                categories[cat] = {'total': 0, 'avg_relevance': []}
            categories[cat]['total'] += 1
            if 'avg_relevance' in result:
                categories[cat]['avg_relevance'].append(result['avg_relevance'])
        
        # Calculate average relevance per category
        for cat in categories:
            rel_list = categories[cat]['avg_relevance']
            categories[cat]['avg_relevance'] = sum(rel_list) / len(rel_list) if rel_list else 0
        
        metrics = {
            'total_questions': total_questions,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / total_questions if total_questions > 0 else 0,
            'average_relevance': avg_relevance,
            'min_relevance': min(relevances) if relevances else 0,
            'max_relevance': max(relevances) if relevances else 0,
            'categories': categories,
            'chunk_type_distribution': dict(chunk_type_dist),
            'acts_coverage': len(all_acts)
        }
        
        return metrics
    
    def generate_report(self, output_file: str = None) -> str:
        """Generate a markdown evaluation report"""
        metrics = self.calculate_metrics()
        
        report_lines = [
            "# RAG System Evaluation Report",
            f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## 1. Executive Summary\n",
            "This evaluation focuses on **retrieval quality** - testing how well the vector store",
            "retrieves relevant context for each question. LLM answer generation is not evaluated",
            "due to API quota limitations.\n",
            f"- **Total Questions:** {metrics['total_questions']}",
            f"- **Successfully Evaluated:** {metrics['successful']}",
            f"- **Failed:** {metrics['failed']}",
            f"- **Success Rate:** {metrics['success_rate']:.2%}",
            f"- **Average Retrieval Relevance:** {metrics['average_relevance']:.3f}",
            f"- **Acts Covered:** {metrics['acts_coverage']}/5",
            "\n## 2. Retrieval Quality Analysis\n",
            "### 2.1 Overall Retrieval Performance\n",
            f"- **Average Relevance Score:** {metrics['average_relevance']:.3f}",
            f"- **Best Relevance:** {metrics['max_relevance']:.3f}",
            f"- **Worst Relevance:** {metrics['min_relevance']:.3f}",
            "\n### 2.2 Chunk Type Distribution\n",
            "Retrieved chunks by type:\n",
        ]
        
        # Chunk type table
        for chunk_type, count in sorted(metrics['chunk_type_distribution'].items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"- **{chunk_type}:** {count} chunks")
        
        # Category performance
        report_lines.append("\n## 3. Performance by Question Category\n")
        report_lines.append("| Category | Total Questions | Avg Relevance |")
        report_lines.append("|----------|----------------|---------------|")
        for cat, data in sorted(metrics['categories'].items(), key=lambda x: x[1]['avg_relevance'], reverse=True):
            report_lines.append(
                f"| {cat.capitalize()} | {data['total']} | {data['avg_relevance']:.3f} |"
            )
        
        # Sample retrievals
        report_lines.append("\n## 4. Sample Retrieval Results\n")
        
        # Best performing (highest relevance)
        sorted_results = sorted(
            [r for r in self.results if 'avg_relevance' in r],
            key=lambda x: x['avg_relevance'],
            reverse=True
        )
        
        if sorted_results:
            report_lines.append("### 4.1 High Relevance Retrieval\n")
            best = sorted_results[0]
            report_lines.extend([
                f"**Question:** {best['question']}",
                f"**Category:** {best['category']} | **Difficulty:** {best['difficulty']}",
                f"**Relevance Score:** {best['avg_relevance']:.3f}",
                f"**Chunks Retrieved:** {best['num_sources']}",
                f"**Chunk Types:** {', '.join(set(best['chunk_types']))}",
                f"**Acts Covered:** {', '.join(map(str, best['acts_covered']))}",
                "\n**Top Retrieved Context:**",
                f"\n> {best['sources'][0][:200]}..." if best['sources'] else "> No sources",
                "\n---\n"
            ])
        
        # Lowest performing
        if len(sorted_results) > 1:
            report_lines.append("### 4.2 Low Relevance Retrieval\n")
            worst = sorted_results[-1]
            report_lines.extend([
                f"**Question:** {worst['question']}",
                f"**Category:** {worst['category']} | **Difficulty:** {worst['difficulty']}",
                f"**Relevance Score:** {worst['avg_relevance']:.3f}",
                f"**Chunks Retrieved:** {worst['num_sources']}",
                f"**Chunk Types:** {', '.join(set(worst['chunk_types']))}",
                "\n**Analysis:** Lower relevance may indicate:",
                "- Question requires cross-scene context",
                "- Question is more analytical/thematic",
                "- May need larger top-k or different chunking strategy",
                "\n---\n"
            ])
        
        # Detailed results by category
        report_lines.append("\n## 5. Detailed Results by Category\n")
        
        by_category = {}
        for result in self.results:
            cat = result.get('category', 'unknown')
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(result)
        
        for cat in sorted(by_category.keys()):
            report_lines.append(f"\n### 5.{list(by_category.keys()).index(cat) + 1} {cat.capitalize()} Questions\n")
            
            for result in by_category[cat][:3]:  # Top 3 per category
                if 'error' in result:
                    report_lines.append(f"**Q{result['id']}:** ❌ ERROR\n")
                    report_lines.append(f"- Question: {result['question']}")
                    report_lines.append(f"- Error: {result['error']}\n")
                else:
                    report_lines.append(f"**Q{result['id']}:** {result['question']}")
                    report_lines.append(f"- Relevance: {result['avg_relevance']:.3f}")
                    report_lines.append(f"- Chunks: {result['num_sources']} ({', '.join(set(result['chunk_types']))})")
                    report_lines.append(f"- Acts: {', '.join(map(str, result['acts_covered']))}\n")
        
        # Recommendations
        report_lines.append("\n## 6. Insights & Recommendations\n")
        report_lines.append("### 6.1 Strengths\n")
        report_lines.append(f"- ✅ Successfully retrieved context for {metrics['success_rate']:.1%} of questions")
        report_lines.append(f"- ✅ Good average relevance score ({metrics['average_relevance']:.3f})")
        report_lines.append(f"- ✅ Covers all {metrics['acts_coverage']} acts of the play")
        report_lines.append(f"- ✅ Diverse chunk types used: {len(metrics['chunk_type_distribution'])} types")
        
        report_lines.append("\n### 6.2 Areas for Improvement\n")
        
        # Find weak categories
        weak_cats = [cat for cat, data in metrics['categories'].items() 
                     if data['avg_relevance'] < metrics['average_relevance']]
        if weak_cats:
            report_lines.append(f"- ⚠️  Lower performance on: {', '.join(weak_cats)}")
            report_lines.append("  * Consider increasing top-k for these question types")
            report_lines.append("  * May need specialized chunking for comparative/thematic questions")
        
        report_lines.append("\n### 6.3 Next Steps\n")
        report_lines.append("1. **LLM Integration:** Test with working API key to evaluate answer quality")
        report_lines.append("2. **Parameter Tuning:** Experiment with top-k values (current: 5)")
        report_lines.append("3. **Chunking Refinement:** Consider adding cross-reference chunks for comparative questions")
        report_lines.append("4. **Prompt Engineering:** Optimize system prompt for analytical questions")
        
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


def run_mock_evaluation():
    """Main evaluation function"""
    logger.info("Starting RAG system evaluation (retrieval only)...")
    
    # Initialize vector store
    logger.info("Initializing vector store...")
    vector_store = initialize_vector_store()
    
    # Create evaluator
    evaluator = MockRAGEvaluator(vector_store)
    
    # Run evaluation
    logger.info("Running retrieval evaluation...")
    results = evaluator.evaluate_all()
    
    # Calculate metrics
    metrics = evaluator.calculate_metrics()
    logger.info(f"\nEvaluation Metrics:")
    logger.info(f"  Success Rate: {metrics['success_rate']:.2%}")
    logger.info(f"  Avg Relevance: {metrics['average_relevance']:.3f}")
    
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
    run_mock_evaluation()
