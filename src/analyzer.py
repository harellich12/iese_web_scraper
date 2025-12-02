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
    3. Their primary areas of interest or research topics (e.g., "Artificial Intelligence", "Supply Chain Management", "Corporate Governance"). Limit to the top 3-5.

    INSTRUCTIONS:
    - Aim for a BALANCE between explicit mentions and reasonable inference.
    - If a sector/industry is strongly implied by their research topics or the companies they work with, include it.
    - Do not be overly restrictive, but avoid wild guesses.
    - Use specific terms where possible (e.g., "Fintech" is better than just "Finance"), but include the broader industry if it helps context.
    - "Areas of Interest" should capture their academic or professional focus.

    Return ONLY a JSON object with three keys: "industries" (list of strings), "sectors" (list of strings), and "areas_of_interest" (list of strings).
    Example: {{"industries": ["Technology", "Finance"], "sectors": ["Fintech", "Blockchain", "SaaS"], "areas_of_interest": ["Cryptocurrency", "Smart Contracts", "Digital Assets"]}}
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
                 result = {"industries": ["General Management"], "sectors": [], "areas_of_interest": []}
                 
            if "industries" not in result or not result["industries"]:
                 result["industries"] = ["General Management"]
                 
            if "sectors" not in result:
                 result["sectors"] = []

            if "areas_of_interest" not in result:
                 result["areas_of_interest"] = []
                 
            return result
            
        except Exception as e:
            if "404" in str(e) and "not found" in str(e):
                logging.error(f"Model not found (404): {e}. Stopping retries.")
                return {"industries": ["General Management"], "sectors": [], "areas_of_interest": []}
            
            wait_time = (2 ** attempt) * 15  # 15s, 30s, 60s
            if "429" in str(e):
                logging.warning(f"Rate limit hit (429). Waiting {wait_time}s...")
            else:
                logging.warning(f"Attempt {attempt+1} failed for LLM analysis: {e}. Waiting {wait_time}s...")
                
            if attempt < 2:
                import time
                time.sleep(wait_time)
            else:
                logging.error(f"All attempts failed for LLM analysis. Returning default.")
                return {"industries": ["General Management"], "sectors": [], "areas_of_interest": []}

if __name__ == "__main__":
    # Test
    sample_bio = "Professor Smith is an expert in blockchain and digital currencies. He has worked with major banks."
    print(analyze_bio_for_industries(sample_bio))
