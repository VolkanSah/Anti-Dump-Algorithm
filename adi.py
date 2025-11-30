# =====================================================================================================
# Anti-Dump Algorithm (ADI) - FIXED VERSION
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

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import re
import numpy as np
import json
from pathlib import Path

@dataclass
class InputMetrics:
    noise: float
    effort: float
    context: float
    details: float
    bonus_factors: float
    penalty_factors: float
    repetition_penalty: float = 0.0

class DumpindexAnalyzer:
    def __init__(self, weights: Dict[str, float] = None, enable_logging: bool = False):
        """
        Initialize the ADI Analyzer.
        
        Args:
            weights: Custom weight configuration for your use case
            enable_logging: If True, logs all analyses to adi_logs.jsonl for later optimization
        """
        self.weights = weights or {
            'noise': 1.0,
            'effort': 2.0,
            'context': 1.5,
            'details': 1.5,
            'bonus': 0.5,
            'penalty': 1.0
        }
        
        self.enable_logging = enable_logging
        self.log_file = Path('adi_logs.jsonl')
        
        # Pattern definitions for metric extraction
        self.noise_patterns = {
            'urgency': r'\b(urgent|asap|emergency|!!+|\?\?+)\b',
            'informal': r'\b(pls|plz|thx|omg|wtf)\b',
            'vague': r'\b(something|somehow|maybe|probably)\b'
        }
        
        self.detail_patterns = {
            'code_elements': r'\b(function|class|method|variable|array|object|def|return)\b',
            'technical_terms': r'\b(error|exception|bug|issue|crash|fail|traceback|stack)\b',
            'specifics': r'[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*'
        }
        
        self.context_indicators = {
            'background': r'\b(because|since|as|when|while)\b',
            'environment': r'\b(using|version|environment|platform|system)\b',
            'goal': r'\b(trying to|want to|need to|goal is|attempting to)\b'
        }

    def _has_negation_before(self, text: str, match_pos: int, window_size: int = 50) -> bool:
        """
        Check if a negation word appears within a specified window before the match position.
        This prevents false positives like 'I have no idea when this started' counting as context.
        
        Args:
            text: The full input text
            match_pos: Position of the matched pattern
            window_size: Number of characters to look back (default: 50)
        
        Returns:
            True if negation found, False otherwise
        """
        window_start = max(0, match_pos - window_size)
        window = text[window_start:match_pos].lower()
        return bool(re.search(r'\b(no|not|never|without|dont|don\'t|doesnt|doesn\'t)\b', window))

    def calculate_repetition_penalty(self, text: str) -> float:
        """
        Calculate penalty for keyword stuffing and repetitive patterns.
        This prevents gaming the system by repeating technical terms.
        
        Returns:
            Penalty score (0 to 3, where higher means more repetition)
        """
        words = text.lower().split()
        if len(words) == 0:
            return 0.0
        
        # Calculate unique word ratio
        unique_ratio = len(set(words)) / len(words)
        
        # Detect excessive repetition of the same word
        word_counts = {}
        for word in words:
            if len(word) > 3:  # Ignore short words like 'the', 'and'
                word_counts[word] = word_counts.get(word, 0) + 1
        
        max_repetition = max(word_counts.values()) if word_counts else 1
        repetition_factor = min(max_repetition / len(words), 0.5)
        
        # Combined penalty
        penalty = (1 - unique_ratio) * 2 + repetition_factor * 2
        return min(penalty, 3.0)

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
        Assesses the effort invested in the input's structure.
        FIXED: Now handles edge cases like very short sentences properly.
        """
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        if not sentences:
            return 0.0
        
        avg_sentence_length = np.mean([len(s.split()) for s in sentences])
        has_formatting = bool(re.search(r'```|\*\*|\n\s*\n', text))
        has_punctuation = bool(re.search(r'[.,;:]', text))
        
        # FIX: Weight sentence count AND length, not just length range
        sentence_quality = (
            (len(sentences) >= 3) * 1.0 +  # Bonus for multiple sentences
            (20 <= avg_sentence_length <= 50) * 2.0 +  # Ideal length range
            (avg_sentence_length >= 5) * 0.5  # Minimum meaningful length
        )
        
        effort_score = min(5.0, (
            sentence_quality +
            has_formatting * 1.5 +
            has_punctuation * 1.5
        ))
        
        return effort_score

    def calculate_context(self, text: str) -> float:
        """
        Measures the presence of background information.
        FIXED: Now checks for negations to avoid false positives.
        """
        context_score = 0.0
        
        for category, pattern in self.context_indicators.items():
            for match in re.finditer(pattern, text.lower()):
                # Only count if NOT preceded by negation
                if not self._has_negation_before(text, match.start()):
                    context_score += 1.0
                    break  # Only count once per category
        
        return min(5.0, context_score)

    def calculate_details(self, text: str) -> Tuple[float, Dict]:
        """
        Quantifies the level of technical depth. This function looks for specific
        technical keywords, code snippets, and structured data that adds value.
        """
        detail_score = 0.0
        detail_findings = {}
        
        for category, pattern in self.detail_patterns.items():
            matches = re.findall(pattern, text.lower())
            score = len(matches) * 0.5
            detail_findings[category] = matches
            detail_score += score
        
        # Cap the score to prevent keyword stuffing from dominating
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
        redundant punctuation, or inputs that are too short to be useful.
        """
        penalties = {}
        
        # Excessive capitalization
        alpha_chars = re.findall(r'[a-zA-Z]', text)
        if alpha_chars:
            caps_ratio = len(re.findall(r'[A-Z]', text)) / len(alpha_chars)
            if caps_ratio > 0.7:
                penalties['excessive_caps'] = caps_ratio
        
        # Excessive punctuation
        excessive_punctuation = len(re.findall(r'[!?]{2,}', text))
        if excessive_punctuation:
            penalties['excessive_punctuation'] = excessive_punctuation
        
        # Too short
        if len(text.split()) < 10:
            penalties['too_short'] = 1.0
        
        penalty_score = sum(penalties.values()) if penalties else 0
        return (min(5.0, penalty_score), penalties)

    def calculate_adi(self, metrics: InputMetrics) -> float:
        """
        Calculates the final Anti-Dump Index (ADI) score using the weighted formula.
        FIXED: Now includes repetition penalty in the denominator to dampen gaming attempts.
        """
        try:
            numerator = (
                self.weights['noise'] * metrics.noise -
                (self.weights['effort'] * metrics.effort +
                 self.weights['bonus'] * metrics.bonus_factors)
            )
            
            # FIX: Add repetition penalty to denominator to reduce impact of keyword stuffing
            denominator = (
                self.weights['context'] * metrics.context +
                self.weights['details'] * metrics.details +
                self.weights['penalty'] * metrics.penalty_factors +
                metrics.repetition_penalty
            )
            
            # Ensure we never divide by zero
            return numerator / max(denominator, 0.1)
            
        except Exception as e:
            print(f"Error calculating ADI: {e}")
            return float('inf')

    def analyze_input(self, text: str, user_context: Optional[Dict] = None) -> Dict:
        """
        Main entry point for the analysis. Orchestrates the entire workflow.
        
        Args:
            text: The input text to analyze
            user_context: Optional dict with 'tier', 'history_avg' for context-aware routing
        
        Returns:
            Dictionary with ADI score, metrics, decision, and recommendations
        """
        # Calculate all metrics
        noise_value, noise_details = self.calculate_noise(text)
        effort_value = self.calculate_effort(text)
        context_value = self.calculate_context(text)
        details_value, detail_findings = self.calculate_details(text)
        bonus_value = self.calculate_bonus_factors(text)
        penalty_value, penalty_details = self.calculate_penalty_factors(text)
        repetition_value = self.calculate_repetition_penalty(text)
        
        metrics = InputMetrics(
            noise=noise_value,
            effort=effort_value,
            context=context_value,
            details=details_value,
            bonus_factors=bonus_value,
            penalty_factors=penalty_value,
            repetition_penalty=repetition_value
        )
        
        adi = self.calculate_adi(metrics)
        
        # Context-aware adjustment (if user tier provided)
        adi_adjusted = adi
        if user_context:
            if user_context.get('tier') == 'enterprise':
                adi_adjusted *= 0.8  # More lenient for paying customers
            if user_context.get('history_avg', 0) < 0:
                adi_adjusted *= 0.9  # Boost for users with good track record
        
        decision = self._make_decision(adi_adjusted)
        recommendations = self._generate_recommendations(
            metrics, noise_details, detail_findings, penalty_details
        )
        
        result = {
            'adi': round(adi, 3),
            'adi_adjusted': round(adi_adjusted, 3) if user_context else None,
            'metrics': {
                'noise': round(noise_value, 3),
                'effort': round(effort_value, 3),
                'context': round(context_value, 3),
                'details': round(details_value, 3),
                'bonus_factors': round(bonus_value, 3),
                'penalty_factors': round(penalty_value, 3),
                'repetition_penalty': round(repetition_value, 3)
            },
            'decision': decision,
            'recommendations': recommendations,
            'details': {
                'noise_findings': noise_details,
                'technical_details': detail_findings,
                'penalties': penalty_details
            }
        }
        
        # Optional logging for later weight optimization
        if self.enable_logging:
            self._log_analysis(text, adi, metrics)
        
        return result

    def _make_decision(self, adi: float) -> str:
        """
        Translates the numerical ADI score into a categorical decision.
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
        """
        recommendations = []
        
        if metrics.noise > 0.3:
            recommendations.append("Reduce informal or urgent expressions.")
            
        if metrics.context < 1.0:
            recommendations.append("Provide more context (environment, background, goal).")
            
        if metrics.details < 1.0:
            recommendations.append("Include specific technical details or error messages.")
            
        if metrics.effort < 2.0:
            recommendations.append("Improve the structure of your input with proper sentences.")
        
        if metrics.repetition_penalty > 1.0:
            recommendations.append("Avoid repeating the same keywords excessively.")
            
        if metrics.penalty_factors > 0:
            if 'excessive_caps' in penalty_details:
                recommendations.append("Avoid excessive capitalization.")
            if 'excessive_punctuation' in penalty_details:
                recommendations.append("Reduce excessive punctuation marks.")
            if 'too_short' in penalty_details:
                recommendations.append("Provide a more detailed description (minimum 10 words).")
        
        if not recommendations:
            recommendations.append("Your input quality is excellent. No improvements needed.")
                    
        return recommendations

    def _log_analysis(self, text: str, adi: float, metrics: InputMetrics):
        """
        Log analysis results to file for later weight optimization.
        Format: One JSON object per line (JSONL).
        """
        log_entry = {
            'text_hash': hash(text),
            'text_length': len(text),
            'adi': round(adi, 3),
            'metrics': {
                'noise': round(metrics.noise, 3),
                'effort': round(metrics.effort, 3),
                'context': round(metrics.context, 3),
                'details': round(metrics.details, 3),
                'bonus_factors': round(metrics.bonus_factors, 3),
                'penalty_factors': round(metrics.penalty_factors, 3),
                'repetition_penalty': round(metrics.repetition_penalty, 3)
            }
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

    def validate_weights(self, test_cases: List[Tuple[str, str]]) -> float:
        """
        Validate current weights against manually labeled test cases.
        
        Args:
            test_cases: List of (input_text, expected_decision) tuples
                       Example: [("Help pls!", "REJECT"), ("Python KeyError...", "HIGH_PRIORITY")]
        
        Returns:
            Accuracy score (0.0 to 1.0)
        """
        if not test_cases:
            raise ValueError("test_cases cannot be empty")
        
        correct = 0
        for text, expected in test_cases:
            result = self.analyze_input(text)
            if result['decision'] == expected:
                correct += 1
        
        accuracy = correct / len(test_cases)
        print(f"Weight Validation: {correct}/{len(test_cases)} correct ({accuracy:.1%})")
        return accuracy


# =====================================================================================================
# USAGE EXAMPLE
# =====================================================================================================
if __name__ == "__main__":
    analyzer = DumpindexAnalyzer(enable_logging=False)
    
    test_inputs = [
        "Pls fix my code. Urgent!!!",
        """I'm trying to implement a login function in Python. 
        When calling auth.login(), I get a TypeError. 
        Here's my code:
        ```python
        def login(username, password):
            return auth.login(username)
        ```
        I'm using Python 3.8 and the auth library version 2.1.""",
        "error error error bug bug crash crash function method class object variable",  # Keyword stuffing test
    ]
    
    for input_text in test_inputs:
        result = analyzer.analyze_input(input_text)
        print("-" * 70)
        print(f"Input: {input_text[:60]}...")
        print(f"ADI: {result['adi']}")
        print(f"Decision: {result['decision']}")
        print("Recommendations:")
        for rec in result['recommendations']:
            print(f"  - {rec}")
        print(f"Metrics: {result['metrics']}")
    print("-" * 70)
