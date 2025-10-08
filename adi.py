# =====================================================================================================
# Anti-Dump Algorithm (ADI)
# A mathematical framework for evaluating and filtering low-quality, unproductive text inputs.
#
# Copyright 2008 - 2025 S. Volkan Kücükbudak
# NOTE: This file contains the core logic for calculating the ADI. It is not an application itself.
# It serves as a library to be integrated into other tools.
#
# IF YOU USE THIS CODE, PLEASE READ THE LICENSE FILE.
# Do not steal free code. Respecting developers' credits ensures that projects like this remain open-source.
# =====================================================================================================

# =====================================================================================================
# QUICK USAGE EXAMPLE
# This section demonstrates how to initialize the analyzer and run it on sample texts.
# Uncomment the code below to see the ADI in action.
# =====================================================================================================
#
# analyzer = DumpindexAnalyzer()
#
# test_inputs = [
#     "Pls fix my code. Urgent!!!",
#     """I'm trying to implement a login function in Python. 
#     When calling auth.login(), I get a TypeError. 
#     Here's my code:
#     ```python
#     def login(username, password):
#         return auth.login(username)
#     ```
#     I'm using Python 3.8 and the auth library version 2.1."""
# ]
#
# for input_text in test_inputs:
#     result = analyzer.analyze_input(input_text)
#     print("-" * 50)
#     print(f"Analysis for: {input_text[:50]}...")
#     print(f"ADI: {result['adi']}")
#     print(f"Decision: {result['decision']}")
#     print("Recommendations:")
#     for rec in result['recommendations']:
#         print(f"- {rec}")
#     print("\nMetrics:", result['metrics'])
# print("-" * 50)
#
# =====================================================================================================
# END OF EXAMPLE
# =====================================================================================================

# Import necessary libraries for data structuring, text processing, and mathematical operations.
from dataclasses import dataclass
from typing import List, Dict, Tuple
import re
import numpy as np

# A dataclass to hold the results of the metric analysis.
# This provides a clean, structured way to pass metrics throughout the analyzer.
@dataclass
class InputMetrics:
    noise: float
    effort: float
    context: float
    details: float
    bonus_factors: float
    penalty_factors: float

# The main class for the Anti-Dump Algorithm.
# It handles the entire analysis workflow, from metric extraction to ADI calculation and recommendations.
class DumpindexAnalyzer:
    def __init__(self, weights: Dict[str, float] = None):
        # Default weights for each metric. These can be customized to suit specific use cases.
        # These can be customized to suit specific use cases (e.g., technical support, creative writing).
        self.weights = weights or {
            'noise': 1.0,
            'effort': 2.0,
            'context': 1.5,
            'details': 1.5,
            'bonus': 0.5,
            'penalty': 1.0
        }
        # =====================================================================================================
        # NOTE: Datasets for Metric Extraction
        # =====================================================================================================
        # The patterns below serve as simple, readable examples for a showcase.
        # For a production environment, you should replace these static patterns
        # with more dynamic and scalable solutions.

        # --- OPTION 1: Static Regular Expressions ---
        # These patterns are easy to understand but are limited to specific keywords and syntax.
        
        # Demo Example: 
        # Patterns for identifying "Noise" elements (e.g., urgency, informal language).
        
        self.noise_patterns = {
            'urgency': r'\b(urgent|asap|emergency|!!+|\?\?+)\b',
            'informal': r'\b(pls|plz|thx)\b',
            'vague': r'\b(something|somehow|maybe|probably)\b'
        }
        
        # Patterns for identifying technical details and context information.
        self.detail_patterns = {
            'code_elements': r'\b(function|class|method|variable|array|object)\b',
            'technical_terms': r'\b(error|exception|bug|issue|crash|fail)\b',
            'specifics': r'[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*'
        }
        
        # --- OPTION 2: Machine Learning Models (Alternative, commented out) ---
        # For a more robust approach, you could use pre-trained ML models to classify text.
        # This allows for more nuanced and context-aware metric extraction.
        # Example:
        # from your_ml_library import TextClassifier
        # self.noise_classifier = TextClassifier('noise_model.pkl')
        # self.detail_classifier = TextClassifier('detail_model.pkl')

        # --- OPTION 3: LLM Embeddings (Advanced, commented out) ---
        # For the most sophisticated approach, you can use LLM embeddings to measure
        # the semantic similarity of the input to a set of "noise" and "detail" vectors.
        # This is highly effective against subtle "dumpiness" or new forms of jargon.
        # Example:
        # from your_llm_library import get_embedding
        # self.noise_vector = get_embedding("urgent help pls asap")
        # self.detail_vector = get_embedding("error stack trace with code example")

 # end main class

    def calculate_noise(self, text: str) -> Tuple[float, Dict]:
        """
        Calculates the noise ratio in the input text by detecting irrelevant or informal words.
        Returns the ratio of noise words to total words, and a dictionary of all matched patterns.
        """
        noise_count = 0
        noise_details = {}
        
        for category, pattern in self.noise_patterns.items():
            matches = re.findall(pattern, text.lower())
            noise_count += len(matches)
            noise_details[category] = matches
        
        total_words = len(text.split())
        return (noise_count / max(total_words, 1), noise_details)

    def calculate_effort(self, text: str) -> float:
        """
        Assesses the effort invested in the input's structure, including sentence quality,
        formatting (e.g., code blocks), and punctuation. A higher score indicates better structure.
        """
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        if not sentences:
            return 0.0
        
        avg_sentence_length = np.mean([len(s.split()) for s in sentences])
        has_formatting = bool(re.search(r'```|\*\*|\n\s*\n', text))
        has_punctuation = bool(re.search(r'[.,;:]', text))
        
        effort_score = min(5.0, (
            (20 <= avg_sentence_length <= 50) * 2.0 +
            has_formatting * 1.5 +
            has_punctuation * 1.5
        ))
        
        return effort_score

    def calculate_context(self, text: str) -> float:
        """
        Measures the presence of background information. It identifies key phrases
        that signal the user is providing a use case, environment details, or goals.
        """
        context_indicators = { # simple basics to understand indicators
            'background': r'\b(because|since|as|when|while)\b',
            'environment': r'\b(using|version|environment|platform|system)\b',
            'goal': r'\b(trying to|want to|need to|goal is|attempting to)\b'
        }
        
        context_score = 0.0
        for category, pattern in context_indicators.items():
            if re.search(pattern, text.lower()):
                context_score += 1.0
                
        return min(5.0, context_score)

    def calculate_details(self, text: str) -> Tuple[float, Dict]:
        """
        Quantifies the level of technical depth. This function looks for specific
        technical keywords, code snippets, and structured data that adds value.
        """
        detail_score = 0.0
        detail_findings = {}
        
        for category, pattern in self.detail_patterns.items():
            matches = re.findall(pattern, text)
            score = len(matches) * 0.5
            detail_findings[category] = matches
            detail_score += score
            
        return (min(5.0, detail_score), detail_findings)

    def calculate_bonus_factors(self, text: str) -> float:
        """
        Identifies and rewards positive formatting elements like code blocks,
        links, or bulleted lists, which significantly improve clarity.
        """
        bonus_score = 0.0
        
        if re.search(r'```[\s\S]*?```', text):
            bonus_score += 1.0
        if re.search(r'\[.*?\]\(.*?\)', text):
            bonus_score += 0.5
        if re.search(r'\n\s*[-*+]\s', text):
            bonus_score += 0.5
        
        return bonus_score

    def calculate_penalty_factors(self, text: str) -> Tuple[float, Dict]:
        """
        Deducts points for negative characteristics, such as excessive capitalization,
        redundant punctuation (e.g., "!!!"), or inputs that are too short to be useful.
        """
        penalties = {}
        
        caps_ratio = len(re.findall(r'[A-Z]', text)) / max(len(re.findall(r'[a-zA-Z]', text)), 1)
        if caps_ratio > 0.7:
            penalties['excessive_caps'] = caps_ratio
        
        excessive_punctuation = len(re.findall(r'[!?]{2,}', text))
        if excessive_punctuation:
            penalties['excessive_punctuation'] = excessive_punctuation
        
        if len(text.split()) < 10:
            penalties['too_short'] = True
        
        penalty_score = min(5.0, sum(penalties.values()) if penalties else 0)
        return (penalty_score, penalties)

    def calculate_adi(self, metrics: InputMetrics) -> float:
        """
        Calculates the final Anti-Dump Index (ADI) score using the weighted formula.
        The denominator is protected against division by zero to ensure stability.
        """
        try:
            numerator = (
                self.weights['noise'] * metrics.noise -
                (self.weights['effort'] * metrics.effort +
                 self.weights['bonus'] * metrics.bonus_factors)
            )
            denominator = (
                self.weights['context'] * metrics.context +
                self.weights['details'] * metrics.details +
                self.weights['penalty'] * metrics.penalty_factors
            )
            return numerator / max(denominator, 0.1)
        except Exception as e:
            print(f"Error calculating ADI: {e}")
            return float('inf')

    def analyze_input(self, text: str) -> Dict:
        """
        This is the main entry point for the analysis. It orchestrates the entire process:
        1. Calls all individual metric calculation functions.
        2. Consolidates the results into an InputMetrics object.
        3. Calculates the final ADI score.
        4. Generates a human-readable decision and specific recommendations for the user.
        """
        noise_value, noise_details = self.calculate_noise(text)
        effort_value = self.calculate_effort(text)
        context_value = self.calculate_context(text)
        details_value, detail_findings = self.calculate_details(text)
        bonus_value = self.calculate_bonus_factors(text)
        penalty_value, penalty_details = self.calculate_penalty_factors(text)
        
        metrics = InputMetrics(
            noise=noise_value,
            effort=effort_value,
            context=context_value,
            details=details_value,
            bonus_factors=bonus_value,
            penalty_factors=penalty_value
        )
        
        adi = self.calculate_adi(metrics)
        
        decision = self._make_decision(adi)
        recommendations = self._generate_recommendations(metrics, noise_details, detail_findings, penalty_details)
        
        return {
            'adi': round(adi, 3),
            'metrics': {
                'noise': round(noise_value, 3),
                'effort': round(effort_value, 3),
                'context': round(context_value, 3),
                'details': round(details_value, 3),
                'bonus_factors': round(bonus_value, 3),
                'penalty_factors': round(penalty_value, 3)
            },
            'decision': decision,
            'recommendations': recommendations,
            'details': {
                'noise_findings': noise_details,
                'technical_details': detail_findings,
                'penalties': penalty_details
            }
        }

    def _make_decision(self, adi: float) -> str:
        """
        Translates the numerical ADI score into a categorical decision: REJECT,
        MEDIUM_PRIORITY, or HIGH_PRIORITY.
        """
        if adi > 1:
            return "REJECT"
        elif 0 <= adi <= 1:
            return "MEDIUM_PRIORITY"
        else:
            return "HIGH_PRIORITY"

    def _generate_recommendations(self, metrics: InputMetrics,
                                 noise_details: Dict,
                                 detail_findings: Dict,
                                 penalty_details: Dict) -> List[str]:
        """
        Generates actionable suggestions to help the user improve their input.
        The recommendations are based on which metrics scored low.
        """
        recommendations = []
        
        if metrics.noise > 0.3:
            recommendations.append("Reduce informal or urgent expressions.")
            
        if metrics.context < 1.0:
            recommendations.append("Provide more context (environment, background, goal).")
            
        if metrics.details < 1.0:
            recommendations.append("Include specific technical details.")
            
        if metrics.effort < 2.0:
            recommendations.append("Improve the structure of your input.")
            
        if metrics.penalty_factors > 0:
            if 'excessive_caps' in penalty_details:
                recommendations.append("Avoid excessive capitalization.")
            if 'excessive_punctuation' in penalty_details:
                recommendations.append("Reduce excessive punctuation marks.")
            if 'too_short' in penalty_details:
                recommendations.append("Provide a more detailed description.")
                    
        return recommendations
