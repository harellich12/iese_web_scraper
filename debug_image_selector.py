import requests
from bs4 import BeautifulSoup
import re

url = "https://www.iese.edu/faculty-research/faculty/ricardo-calleja/"
try:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    print(f"Response length: {len(response.text)}")
    
    # Search for the name in the text to find potential image URLs
    matches = [m.start() for m in re.finditer(r"calleja", response.text, re.IGNORECASE)]
    print(f"Found 'calleja' at indices: {matches[:5]}...")
    
    for match in matches[:5]:
        start = max(0, match - 100)
        end = min(len(response.text), match + 100)
        print(f"\nContext around {match}:\n{response.text[start:end]}")

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Check jumbotron for background image
    jumbotron = soup.select_one(".jumbotron")
    if jumbotron:
        print(f"\nJumbotron found: {jumbotron.name}")
        print(f"Classes: {jumbotron.get('class')}")
        print(f"Style: {jumbotron.get('style')}")
        print(f"Data attributes: {[k for k in jumbotron.attrs.keys() if k.startswith('data-')]}")
        for k, v in jumbotron.attrs.items():
            if k.startswith('data-'):
                print(f"{k}: {v}")
    else:
        print("\nNo jumbotron found.")

except Exception as e:
    print(f"Error: {e}")
