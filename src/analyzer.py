import google.generativeai as genai
import os
import json
import logging

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
load_dotenv()

def analyze_bio_for_industries(bio_text):
    """
    Uses Gemini to extract industries from a professor's bio.
    Returns a list of industry strings.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logging.warning("GEMINI_API_KEY not found. Returning empty list.")
        return []

    genai.configure(api_key=api_key)
    # Use a currently supported model
    model = genai.GenerativeModel('gemini-flash-latest')

    prompt = f"""
    Analyze the following academic biography and identify:
    1. The key industries the person is involved in (high-level, e.g., "Technology", "Healthcare").
    2. The specific sectors or sub-industries (more granular, e.g., "SaaS", "Semiconductors", "Biotech").

    Return ONLY a JSON object with two keys: "industries" (list of strings) and "sectors" (list of strings).
    Example: {{"industries": ["Technology", "Finance"], "sectors": ["Fintech", "Blockchain", "SaaS"]}}
    If no specific industry/sector is mentioned, return empty lists.
    
    Biography:
    {bio_text[:4000]} 
    """
    # Truncate bio to avoid token limits if necessary

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Clean up potential markdown formatting
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
            text = text[3:-3]
            
        result = json.loads(text)
        
        # Ensure structure
        if not isinstance(result, dict):
             result = {"industries": ["General Management"], "sectors": []}
             
        if "industries" not in result or not result["industries"]:
             result["industries"] = ["General Management"]
             
        if "sectors" not in result:
             result["sectors"] = []
             
        return result
            
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        return {"industries": ["General Management"], "sectors": []}

if __name__ == "__main__":
    # Test
    sample_bio = "Professor Smith is an expert in blockchain and digital currencies. He has worked with major banks."
    print(analyze_bio_for_industries(sample_bio))
