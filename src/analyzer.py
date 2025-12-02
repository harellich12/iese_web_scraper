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
    model = genai.GenerativeModel('gemini-2.0-flash')

    prompt = f"""
    Analyze the following academic biography and identify:
    1. The key industries the person is involved in (high-level, e.g., "Technology", "Healthcare"). Limit to the top 1-3 most relevant.
    2. The specific sectors or sub-industries (more granular, e.g., "SaaS", "Semiconductors", "Biotech"). Limit to the top 3-5 most relevant.

    CRITICAL INSTRUCTIONS:
    - Be CONSERVATIVE. Only include industries/sectors that are EXPLICITLY mentioned or STRONGLY implied by their research/work.
    - Do NOT include broad terms if a specific one applies (e.g., use "Fintech" instead of just "Finance" if applicable, but don't list every possible sub-sector).
    - Do NOT infer sectors based on loose associations. If they just mention a company name once, that doesn't mean they specialize in that company's sector.
    - Focus on their AREA OF EXPERTISE, not just who they worked with.

    Return ONLY a JSON object with two keys: "industries" (list of strings) and "sectors" (list of strings).
    Example: {{"industries": ["Technology", "Finance"], "sectors": ["Fintech", "Blockchain", "SaaS"]}}
    If no specific industry/sector is mentioned, return empty lists.
    
    Biography:
    {bio_text[:4000]} 
    """
    # Truncate bio to avoid token limits if necessary

    for attempt in range(3):
        try:
            response = model.generate_content(prompt, request_options={'timeout': 30})
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
            if "404" in str(e) and "not found" in str(e):
                logging.error(f"Model not found (404): {e}. Stopping retries.")
                return {"industries": ["General Management"], "sectors": []}
                
            logging.warning(f"Attempt {attempt+1} failed for LLM analysis: {e}")
            if attempt < 2:
                import time
                time.sleep(2)
            else:
                logging.error(f"All attempts failed for LLM analysis. Returning default.")
                return {"industries": ["General Management"], "sectors": []}

if __name__ == "__main__":
    # Test
    sample_bio = "Professor Smith is an expert in blockchain and digital currencies. He has worked with major banks."
    print(analyze_bio_for_industries(sample_bio))
