import requests
from bs4 import BeautifulSoup
import time
import logging
import sys
import os
from PIL import Image
from io import BytesIO
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_URL = "https://www.iese.edu/search/professors/"

def get_soup(url):
    """Helper to fetch URL and return BeautifulSoup object."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
        return None

def process_image(image_url, professor_name):
    """Downloads, crops, and saves the image locally."""
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        img = Image.open(BytesIO(response.content))
        
        # Crop: 400x300 starting at x=800
        # Box is (left, upper, right, lower)
        # x=800 to x=1200 (width 400)
        # y=0 to y=300 (height 300)
        crop_box = (800, 0, 1200, 300)
        
        # Ensure image is large enough, otherwise resize or pad?
        # For now, we'll just try to crop. If image is smaller, PIL might complain or return smaller.
        # Let's just crop.
        cropped_img = img.crop(crop_box)
        
        # Create directory
        save_dir = "data/images"
        os.makedirs(save_dir, exist_ok=True)
        
        # Safe filename
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', professor_name)
        filename = f"{safe_name}.jpg"
        file_path = os.path.join(save_dir, filename).replace("\\", "/")
        
        # Convert to RGB if necessary (e.g. if PNG with alpha)
        if cropped_img.mode in ("RGBA", "P"):
            cropped_img = cropped_img.convert("RGB")
            
        cropped_img.save(file_path, "JPEG", quality=85)
        
        return file_path
        
    except Exception as e:
        logging.error(f"Error processing image for {professor_name}: {e}")
        return None

def get_all_professor_urls(limit=None):
    """Iterates through pagination to get all professor profile URLs."""
    professor_urls = []
    page = 1
    
    while True:
        # Check if we have enough URLs
        if limit and len(professor_urls) >= limit:
            logging.info(f"Reached limit of {limit} URLs during discovery.")
            break

        url = f"{BASE_URL}{page}/" if page > 1 else BASE_URL
        logging.info(f"Scraping list page: {url}")
        
        soup = get_soup(url)
        if not soup:
            break
            
        # Check for redirects (if we asked for page X but got page 1)
        # Note: requests follows redirects by default, so we check the soup or response history if we had it.
        # Since we only have soup here, we can check canonical link or just rely on content.
        # A better check is if the "Next" button logic works.
        
        # Find professor links
        links = soup.select("a.employee-card-link") 
        
        if not links:
            logging.info("No more professors found (no links).")
            break
            
        logging.info(f"Found {len(links)} profiles on page {page}")
        
        new_links_count = 0
        for link in links:
            href = link.get('href')
            if href and href not in professor_urls:
                professor_urls.append(href)
                new_links_count += 1
                if limit and len(professor_urls) >= limit:
                    break
        
        if limit and len(professor_urls) >= limit:
            break
        
        if new_links_count == 0:
            logging.info("No new professors found on this page (all duplicates). Stopping.")
            break
            
        # Check for "Next" button
        next_button = soup.select_one("a.next.page-numbers")
        if not next_button:
            logging.info("Reached last page (no next button).")
            break
            
        page += 1
        if page > 50: # Safety break
            logging.info("Hit safety limit of 50 pages.")
            break
            
        time.sleep(1) 

    return list(set(professor_urls))

def scrape_professor_details(url):
    """Scrapes details from a single professor's profile page."""
    logging.info(f"Scraping profile: {url}")
    soup = get_soup(url)
    if not soup:
        return None

    data = {
        "url": url,
        "name": "Unknown",
        "title": "",
        "department": "",
        "bio": "",
        "image_url": ""
    }

    try:
        # Name - Try multiple strategies
        name_tag = soup.select_one("h1.entry-title")
        if name_tag:
            # Get text, but be careful of spans. 
            # Often the name is split across text nodes and spans.
            # "Mario" <span>Capizzani</span>
            data["name"] = name_tag.get_text(" ", strip=True)
        
        if data["name"] == "Unknown" and soup.title:
             data["name"] = soup.title.get_text(strip=True).split("|")[0].strip()

        # Title & Department
        # The structure is often: <div class="faculty-data"> <h1>...</h1> TEXT <ul>...</ul> </div>
        # We need the TEXT between h1 and ul.
        faculty_data = soup.select_one(".faculty-data")
        if faculty_data:
            # Get all text from faculty_data
            full_text = faculty_data.get_text(" ", strip=True)
            # Remove the name (from h1) from this text to isolate title
            if data["name"] in full_text:
                remaining_text = full_text.replace(data["name"], "").strip()
                # The remaining text might include the UL content (email, phone), so we need to be careful.
                # Better approach: Iterate children
                title_parts = []
                for child in faculty_data.children:
                    if child.name == 'h1': continue
                    if child.name == 'ul': break # Stop at contact info
                    if child.string and child.string.strip():
                        title_parts.append(child.string.strip())
                
                if title_parts:
                    data["title"] = " ".join(title_parts)

            # Heuristic for Department
            if " of " in data["title"]:
                data["department"] = data["title"].split(" of ")[-1]
            elif " in " in data["title"]:
                data["department"] = data["title"].split(" in ")[-1]

        # Bio
        # Try multiple selectors for bio
        content_div = soup.select_one(".entry-content")
        if content_div:
            data["bio"] = content_div.get_text("\n", strip=True)
        
        # Fallback 1: Generic article content
        if not data["bio"]:
            bio_div = soup.select_one("#main article")
            if bio_div:
                 data["bio"] = bio_div.get_text("\n", strip=True)
        
        # Fallback 2: Look for specific text blocks if main containers fail
        if not data["bio"]:
            # Sometimes it's just in a div with class 'row' or similar generic
            # Let's try to grab all paragraphs in the main area
            main_area = soup.select_one("main") or soup.select_one("#main")
            if main_area:
                paras = main_area.find_all('p')
                data["bio"] = "\n".join([p.get_text(strip=True) for p in paras])

        # Image
        # Strategy 1: Check for jumbotron background image (lazy loaded)
        jumbotron = soup.select_one(".jumbotron")
        if jumbotron and jumbotron.get('data-bg-image'):
            bg_image = jumbotron.get('data-bg-image')
            # Format is usually: url(https://...)
            if "url(" in bg_image:
                data["image_url"] = bg_image.split("url(")[1].split(")")[0]
            else:
                data["image_url"] = bg_image

        # Strategy 2: Fallback to standard image tag
        if not data["image_url"]:
            img_tag = soup.select_one(".post-thumbnail img")
            if img_tag:
                data["image_url"] = img_tag.get('src')
        
        # Process Image (Download & Crop)
        if data["image_url"]:
            local_path = process_image(data["image_url"], data["name"])
            if local_path:
                data["image_url"] = local_path
            
        logging.info(f"Extracted: Name={data['name']}, Title={data['title']}, Dept={data['department']}, BioLen={len(data['bio'])}, ImageURL={data['image_url']}")

    except Exception as e:
        logging.error(f"Error parsing profile {url}: {e}")

    return data

from database import init_db, Professor, Industry, Sector
from analyzer import analyze_bio_for_industries

# Initialize DB Session
Session = init_db()
session = Session()

def save_professor(data):
    """Saves professor data and industries to the database."""
    try:
        # Check if exists
        existing = session.query(Professor).filter_by(url=data['url']).first()
        if existing:
            # Update image if we have a new one and (it's missing OR it's a remote URL and we have a local one)
            # Actually, just update if we have a valid new image.
            if data['image_url'] and existing.image_url != data['image_url']:
                existing.image_url = data['image_url']
                session.commit()
                logging.info(f"Updated image for: {data['name']}")
            else:
                logging.info(f"Professor already exists: {data['name']}")
            return

        prof = Professor(
            name=data['name'],
            url=data['url'],
            title=data['title'],
            department=data['department'],
            bio=data['bio'],
            image_url=data['image_url']
        )
        
        # Analyze Industries & Sectors
        if data['bio']:
            analysis_result = analyze_bio_for_industries(data['bio'])
            
            industry_names = analysis_result.get("industries", [])
            sector_names = analysis_result.get("sectors", [])
            
            logging.info(f"Inferred Industries: {industry_names}, Sectors: {sector_names}")
            
            # Save Industries
            for ind_name in industry_names:
                industry = session.query(Industry).filter_by(name=ind_name).first()
                if not industry:
                    industry = Industry(name=ind_name)
                    session.add(industry)
                prof.industries.append(industry)
                
            # Save Sectors
            for sec_name in sector_names:
                sector = session.query(Sector).filter_by(name=sec_name).first()
                if not sector:
                    sector = Sector(name=sec_name)
                    session.add(sector)
                prof.sectors.append(sector)
        
        session.add(prof)
        session.commit()
        logging.info(f"Saved: {prof.name}")
        
    except Exception as e:
        logging.error(f"Error saving {data['name']}: {e}")
        session.rollback()

if __name__ == "__main__":
    # Allow passing a limit argument: python scraper.py 5
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    
    print("Starting scrape...", flush=True)
    # Pass limit to discovery to avoid fetching all pages if we only need a few
    urls = get_all_professor_urls(limit=limit)
    print(f"Total unique professors found: {len(urls)}", flush=True)
    
    if limit:
        # Slice again just in case, though the function should handle it
        urls = urls[:limit]
        print(f"Limiting to first {limit} profiles for processing.", flush=True)

    for i, url in enumerate(urls):
        logging.info(f"Processing {i+1}/{len(urls)}: {url}")
        details = scrape_professor_details(url)
        if details:
            save_professor(details)
        time.sleep(0.1) # Small delay to prevent tight loop race conditions
            
    print("Scraping complete.", flush=True)
    time.sleep(2) # Ensure the process doesn't exit before the agent captures the output
    sys.exit(0)
