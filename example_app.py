# ==== Copyright 2008 - 2025 S. Volkan Kücükbudak ====
#
# A demonstration of the Anti-Dump Index (ADI) algorithm within a Flask application.
# This app shows how ADI can be used to intelligently route user inputs to different
# AI models based on the input's quality and content.
#
# NOTE: This code is for educational and demonstrative purposes only.
# Please refer to the LICENSE file before using this code. Respecting the work of
# developers ensures that free resources like this can continue to exist.
#
# =====================================================================================================
# HOW TO USE THIS EXAMPLE APPLICATION
#
# 1. Install dependencies:
#    pip install flask
#
# 2. Run the Flask app:
#    python example_app.py
#
# 3. Send a POST request to the /process endpoint with a JSON body:
#    curl -X POST http://localhost:5000/process \
#      -H "Content-Type: application/json" \
#      -d '{"input_text": "Help me fix this Python code: print(x)"}'
#
# Example JSON output:
# {
#    "api_used": "Claude (Programming)",
#    "adi_value": -0.75,
#    "adi_decision": "HIGH_PRIORITY",
#    "decision": "Accepted",
#    "quality_rating": "High-quality input: Contains programming context",
#    "response": "Claude processed: Solved programming tasks in 'Help me fix this Python code: print(x)'",
#    "recommendations": ["Add error messages for better debugging"]
# }
# =====================================================================================================

from flask import Flask, request, jsonify
from adi import DumpindexAnalyzer

app = Flask(__name__)
analyzer = DumpindexAnalyzer()

# Simulated AI APIs. In a production environment, these would be real API calls.
def gpt_processing(text: str) -> str:
    """Simulates processing by a logical analysis model."""
    return f"GPT processed: Focused on logical analysis of '{text}'"

def gemini_processing(text: str) -> str:
    """Simulates processing by a creative content model."""
    return f"Gemini processed: Generated creative content for '{text}'"

def claude_processing(text: str) -> str:
    """Simulates processing by a programming-focused model."""
    return f"Claude processed: Solved programming tasks in '{text}'"

def deepseek_processing(text: str) -> str:
    """Simulates processing by a deep analysis model."""
    return f"DeepSeek processed: Deep analysis of '{text}'"

def reject_processing(text: str) -> str:
    """Handles inputs that are rejected due to low quality."""
    return "Input rejected. Please provide more details and context."

@app.route('/process', methods=['POST'])
def process_input():
    """
    Main endpoint for processing user inputs.
    Routes to different AI models based on ADI score and content.
    """
    try:
        data = request.get_json()
        input_text = data.get('input_text', '')
        
        if not input_text:
            return jsonify({"error": "No input text provided"}), 400
        
        # Use the ADI algorithm to analyze the input text.
        result = analyzer.analyze_input(input_text)  # FIX: Correct method name
        adi_value = result['adi']
        adi_decision = result['decision']  # FIX: Use correct key
        
        # The core ADI routing logic.
        if adi_value > 1.0:
            # High dumpiness: The input is rejected. This saves processing resources.
            response_text = reject_processing(input_text)
            api_used = "Rejection"
            quality_rating = "Low-quality input: Too much noise, insufficient details"
            
        elif adi_value < 0:
            # High-quality input: Route to a premium, deep-analysis model.
            response_text = deepseek_processing(input_text)
            api_used = "DeepSeek (Deep Analysis)"
            quality_rating = "High-quality input: Well-structured with sufficient context"
            
        elif "program" in input_text.lower() or "code" in input_text.lower():
            # Medium-quality input, but content suggests a programming task.
            response_text = claude_processing(input_text)
            api_used = "Claude (Programming)"
            quality_rating = "Medium-quality input: Programming context detected"
            
        elif "creative" in input_text.lower() or "write" in input_text.lower():
            # Medium-quality input, but content suggests a creative task.
            response_text = gemini_processing(input_text)
            api_used = "Gemini (Creative)"
            quality_rating = "Medium-quality input: Creative task detected"
            
        else:
            # Standard input: Route to a general-purpose model.
            response_text = gpt_processing(input_text)
            api_used = "GPT (Logical Analysis)"
            quality_rating = "Medium-quality input: General purpose routing"
        
        # Assemble and return the final JSON response.
        response = {
            "api_used": api_used,
            "adi_value": round(adi_value, 3),
            "adi_decision": adi_decision,  # FIX: Correct key name
            "decision": "Rejected" if adi_value > 1.0 else "Accepted",
            "quality_rating": quality_rating,
            "response": response_text,
            "recommendations": result['recommendations'],  # FIX: Correct key name
            "metrics": result['metrics']  # Include full metrics for transparency
        }
        
        return jsonify(response)
    
    except Exception as e:
        # Error handling to prevent app crashes
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy", "service": "ADI Example App"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
