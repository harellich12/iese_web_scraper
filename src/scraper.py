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
            data["name"] = name_tag.get_text(" ", strip=True)
        
        # Fallback Name: Breadcrumb
        if data["name"] == "Unknown":
            breadcrumb = soup.select_one(".breadcrumb__item.item-current")
            if breadcrumb:
                data["name"] = breadcrumb.get_text(strip=True)

        # Fallback Name: Meta Title
        if data["name"] == "Unknown":
            meta_title = soup.select_one('meta[property="og:title"]')
            if meta_title:
                data["name"] = meta_title.get("content", "Unknown")

        if data["name"] == "Unknown" and soup.title:
             data["name"] = soup.title.get_text(strip=True).split("|")[0].strip()

        # Title & Department
        # Strategy 1: Look for "Professor ... in the X Department" in the bio/intro text
        # Selector: .content.description-subHeader p
        intro_div = soup.select_one(".content.description-subHeader p")
        intro_text = ""
        if intro_div:
            intro_text = intro_div.get_text(" ", strip=True)
        
        # Also check the first paragraph of the bio if intro_div is empty
        if not intro_text:
            content_div = soup.select_one(".entry-content")
            if content_div:
                first_p = content_div.find('p')
                if first_p:
                    intro_text = first_p.get_text(" ", strip=True)

        if intro_text:
            # Regex for department
            # Pattern 1: "Professor ... in the X Department"
            dept_match = re.search(r"Professor .*? in the (.+?) Department", intro_text, re.IGNORECASE)
            if dept_match:
                data["department"] = dept_match.group(1).strip()
            
            # Pattern 2: "Department of X"
            if not data["department"]:
                dept_match = re.search(r"Department of (.+?)(?:\.|,|$)", intro_text, re.IGNORECASE)
                if dept_match:
                    data["department"] = dept_match.group(1).strip()

        # Strategy 2: Meta Description
        if not data["department"]:
            meta_desc = soup.select_one('meta[name="description"]')
            if meta_desc:
                desc_text = meta_desc.get("content", "")
                # Pattern 1
                dept_match = re.search(r"Professor .*? in the (.+?) Department", desc_text, re.IGNORECASE)
                if dept_match:
                    data["department"] = dept_match.group(1).strip()
                # Pattern 2
                if not data["department"]:
                    dept_match = re.search(r"Department of (.+?)(?:\.|,|$)", desc_text, re.IGNORECASE)
                    if dept_match:
                        data["department"] = dept_match.group(1).strip()

        # Strategy 3: Old Heuristic (Fallback)
        if not data["department"]:
            faculty_data = soup.select_one(".faculty-data")
            if faculty_data:
                full_text = faculty_data.get_text(" ", strip=True)
                if data["name"] in full_text:
                    remaining_text = full_text.replace(data["name"], "").strip()
                    title_parts = []
                    for child in faculty_data.children:
                        if child.name == 'h1': continue
                        if child.name == 'ul': break 
                        if child.string and child.string.strip():
                            title_parts.append(child.string.strip())
                    
                    if title_parts:
                        data["title"] = " ".join(title_parts)

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

from database import init_db, Professor, Industry, Sector, AreaOfInterest
from analyzer import analyze_bio_for_industries

# Initialize DB Session
Session = init_db()
session = Session()

def save_professor(data):
    """Saves professor data and industries to the database."""
    try:
        # Check if exists
        prof = session.query(Professor).filter_by(url=data['url']).first()
        
        if not prof:
            prof = Professor(url=data['url'])
            session.add(prof)
            logging.info(f"Creating new professor: {data['name']}")
        else:
            logging.info(f"Updating existing professor: {data['name']}")

        # Update fields
        prof.name = data['name']
        prof.title = data['title']
        prof.department = data['department']
        prof.bio = data['bio']
        prof.image_url = data['image_url']
        
        # Analyze Industries & Sectors
        if data['bio']:
            analysis_result = analyze_bio_for_industries(data['bio'])
            
            industry_names = analysis_result.get("industries", [])
            sector_names = analysis_result.get("sectors", [])
            area_names = analysis_result.get("areas_of_interest", [])
            
            logging.info(f"Inferred Industries: {industry_names}, Sectors: {sector_names}, Areas: {area_names}")
            
            # Clear existing associations to avoid duplicates/stale data
            prof.industries = []
            prof.sectors = []
            prof.areas_of_interest = []
            
            # Save Industries
            for ind_name in industry_names:
                industry = session.query(Industry).filter_by(name=ind_name).first()
                if not industry:
                    industry = Industry(name=ind_name)
                    session.add(industry)
                if industry not in prof.industries:
                    prof.industries.append(industry)
                
            # Save Sectors
            for sec_name in sector_names:
                sector = session.query(Sector).filter_by(name=sec_name).first()
                if not sector:
                    sector = Sector(name=sec_name)
                    session.add(sector)
                if sector not in prof.sectors:
                    prof.sectors.append(sector)

            # Save Areas of Interest
            for area_name in area_names:
                area = session.query(AreaOfInterest).filter_by(name=area_name).first()
                if not area:
                    area = AreaOfInterest(name=area_name)
                    session.add(area)
                if area not in prof.areas_of_interest:
                    prof.areas_of_interest.append(area)
        
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
