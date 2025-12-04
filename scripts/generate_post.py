#!/usr/bin/env python3
"""
Automated blog post generation script
Uses Google Custom Search API to search for images and generate blog posts.
"""

import os
import json
import re
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
import yaml
import frontmatter

# Optional imports with fallback
try:
    from pytrends.request import TrendReq
    PTRENDS_AVAILABLE = True
except ImportError:
    PTRENDS_AVAILABLE = False
    print("Warning: pytrends not available. Trend-based selection disabled.")

try:
    import wikipedia
    wikipedia.set_lang("en")  # Set to English
    WIKIPEDIA_AVAILABLE = True
except ImportError:
    WIKIPEDIA_AVAILABLE = False
    print("Warning: wikipedia not available. Wikipedia integration disabled.")

# Configuration
# Read API key from environment variable or use default
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyBUrWy_QcqzNFbRPik7Dm7MqXmIbqmG-Gw")
# Custom Search Engine ID must be created at Google Custom Search
# Available at https://programmablesearchengine.google.com/
# Your CSE ID: 8690747c4ec274a1e
CUSTOM_SEARCH_ENGINE_ID = os.getenv("GOOGLE_CSE_ID", "8690747c4ec274a1e")

POSTS_DIR = Path("_posts")
IMAGES_DIR = Path("images")

# Initialize pytrends (if available)
if PTRENDS_AVAILABLE:
    pytrends = TrendReq(hl='en-US', tz=360)

# List of places that were once popular around the world
PLACES = [
    {"name": "Times Square", "location": "New York, USA", "description": "Times Square was once the vibrant heart of New York City, known for its dazzling lights and bustling crowds."},
    {"name": "Detroit", "location": "Michigan, USA", "description": "Detroit was once the Motor City, a thriving industrial hub and symbol of American manufacturing power."},
    {"name": "Pripyat", "location": "Ukraine", "description": "Pripyat was a modern Soviet city until the Chernobyl disaster, now a ghost town frozen in time."},
    {"name": "Hashima Island", "location": "Japan", "description": "Hashima Island, also known as Gunkanjima, was once the most densely populated place on Earth, now abandoned."},
    {"name": "Bodie", "location": "California, USA", "description": "Bodie was a booming gold-mining town in the 1800s, now preserved as a ghost town."},
    {"name": "Varosha", "location": "Cyprus", "description": "Varosha was a popular tourist destination until 1974, now an abandoned resort town."},
    {"name": "Centralia", "location": "Pennsylvania, USA", "description": "Centralia was a mining town until an underground fire forced its abandonment."},
    {"name": "Kolmanskop", "location": "Namibia", "description": "Kolmanskop was a wealthy diamond mining town, now being reclaimed by the desert."},
    {"name": "Craco", "location": "Italy", "description": "Craco was a medieval hilltop town abandoned due to natural disasters."},
    {"name": "Oradour-sur-Glane", "location": "France", "description": "Oradour-sur-Glane was preserved as a memorial after being destroyed in World War II."},
    {"name": "Humberstone", "location": "Chile", "description": "Humberstone was a thriving saltpeter mining town, now a UNESCO World Heritage Site."},
    {"name": "Kadykchan", "location": "Russia", "description": "Kadykchan was a Soviet mining town abandoned after the collapse of the USSR."},
]


def get_trend_score(place_name, location=""):
    """
    Get Google Trends score for a place.
    Returns a score from 0-100 based on recent search trends.
    """
    if not PTRENDS_AVAILABLE:
        return 50  # Default score if pytrends not available
    
    try:
        # Build search keyword
        keyword = place_name
        if location:
            keyword = f"{place_name} {location}"
        
        # Get interest over time for the last 30 days
        pytrends.build_payload([keyword], cat=0, timeframe='today 1-m', geo='', gprop='')
        df = pytrends.interest_over_time()
        
        if df.empty:
            return 50  # Default score if no data
        
        # Calculate average trend score
        avg_score = df[keyword].mean()
        return min(100, max(0, int(avg_score)))
    
    except Exception as e:
        # Rate limiting or other errors - return default score
        # Don't print error for rate limiting (429) to avoid spam
        if "429" not in str(e):
            print(f"Error getting trend score for {place_name}: {e}")
        return 50  # Default score on error


def get_wikipedia_info(place_name, location=""):
    """
    Get Wikipedia information for a place.
    Returns a dictionary with summary, keywords, and full text.
    """
    if not WIKIPEDIA_AVAILABLE:
        return {
            "summary": "",
            "keywords": [],
            "full_text": ""
        }
    
    try:
        # Try to find Wikipedia page
        search_query = place_name
        if location:
            # Try with location first
            search_query = f"{place_name}, {location}"
        
        try:
            page = wikipedia.page(search_query, auto_suggest=True)
        except wikipedia.exceptions.DisambiguationError as e:
            # If disambiguation, try first option
            page = wikipedia.page(e.options[0])
        except wikipedia.exceptions.PageError:
            # Try without location
            page = wikipedia.page(place_name, auto_suggest=True)
        
        return {
            "summary": page.summary,
            "keywords": extract_keywords(page.summary + " " + page.content[:2000]),
            "full_text": page.content[:5000],  # First 5000 chars
            "url": page.url,
            "title": page.title
        }
    
    except Exception as e:
        print(f"Error getting Wikipedia info for {place_name}: {e}")
        return {
            "summary": "",
            "keywords": [],
            "full_text": ""
        }


def extract_keywords(text):
    """
    Extract relevant keywords from text that describe the place's characteristics.
    """
    # Keywords that indicate abandoned/ruined places
    characteristic_keywords = [
        "abandoned", "ruins", "ruined", "ghost town", "deserted", "derelict",
        "decay", "decayed", "dilapidated", "crumbling", "collapsed",
        "mining", "mine", "industrial", "factory", "manufacturing",
        "disaster", "destroyed", "evacuated", "uninhabited",
        "preserved", "memorial", "historical", "heritage",
        "Soviet", "communist", "war", "bombing", "conflict"
    ]
    
    text_lower = text.lower()
    found_keywords = []
    
    for keyword in characteristic_keywords:
        if keyword in text_lower:
            found_keywords.append(keyword)
    
    # Also extract location-specific terms
    location_terms = ["city", "town", "village", "island", "resort", "hotel", "zoo"]
    for term in location_terms:
        if term in text_lower:
            found_keywords.append(term)
    
    # Remove duplicates and return top 5
    return list(set(found_keywords))[:5]


def search_images(query, num_results=10):
    """
    Search for images using Google Custom Search API.
    Filters results to within the last month.
    """
    url = "https://www.googleapis.com/customsearch/v1"
    
    # Calculate date one month ago
    one_month_ago = datetime.now() - timedelta(days=30)
    date_restrict = one_month_ago.strftime("%Y%m%d")
    
    params = {
        "key": GOOGLE_API_KEY,
        "cx": CUSTOM_SEARCH_ENGINE_ID,
        "q": query,
        "searchType": "image",
        "num": num_results,
        "safe": "active",
        "dateRestrict": f"d{30}",  # Last 30 days
        "imgSize": "large",
        "imgType": "photo"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Check for API errors
        if "error" in data:
            error_msg = data["error"].get("message", "Unknown error")
            print(f"Google API Error: {error_msg}")
            return []
        
        images = []
        if "items" in data:
            for item in data["items"]:
                images.append({
                    "url": item.get("link", ""),
                    "title": item.get("title", ""),
                    "thumbnail": item.get("image", {}).get("thumbnailLink", ""),
                    "context": item.get("image", {}).get("contextLink", "")
                })
        
        return images
    except requests.exceptions.Timeout:
        print(f"Image search timeout: {query}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error occurred during image search: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Response status code: {e.response.status_code}")
        return []


def search_images_by_features(place_name, location, keywords, num_results=10):
    """
    Search for images using place name and characteristic keywords.
    """
    # Build query with keywords
    if keywords:
        keyword_str = " ".join(keywords[:3])  # Use top 3 keywords
        query = f"{place_name} {location} {keyword_str} current state"
    else:
        query = f"{place_name} {location} abandoned current state"
    
    print(f"Searching images with query: {query}")
    return search_images(query, num_results)


def create_post(place, wiki_info=None):
    """
    Generate a blog post based on place information.
    """
    # Get Wikipedia info if not provided
    if wiki_info is None:
        print(f"Fetching Wikipedia information for '{place['name']}'...")
        wiki_info = get_wikipedia_info(place['name'], place.get('location', ''))
    
    # Extract keywords for image search
    keywords = wiki_info.get('keywords', [])
    if not keywords:
        keywords = extract_keywords(place.get('description', ''))
    
    # Search images using features
    print(f"Searching for images of '{place['name']}' using keywords: {keywords}")
    images = search_images_by_features(
        place['name'], 
        place.get('location', ''), 
        keywords,
        num_results=5
    )
    
    if not images:
        print(f"No images found for '{place['name']}'.")
        return None
    
    # Generate post content
    date = datetime.now()
    # Convert place name to URL-safe slug
    place_slug = re.sub(r'[^\w\s-]', '', place['name'])
    place_slug = re.sub(r'[-\s]+', '-', place_slug)
    filename = f"{date.strftime('%Y-%m-%d')}-{place_slug.lower()}.md"
    filepath = POSTS_DIR / filename
    
    # Check if post already exists (prevent duplicates)
    if filepath.exists():
        print(f"Warning: {filepath} already exists. Skipping.")
        return None
    
    # Generate image markdown
    image_markdown = "\n\n## Current State\n\n"
    for i, img in enumerate(images[:5], 1):
        image_markdown += f"![{place['name']} image {i}]({img['url']})\n\n"
        image_markdown += f"*{img['title']}*\n\n"
    
    # Use Wikipedia summary if available, otherwise use default description
    description = place.get('description', '')
    if wiki_info.get('summary'):
        # Use Wikipedia summary, but keep it concise (first 2-3 sentences)
        wiki_summary = wiki_info['summary']
        sentences = wiki_summary.split('. ')
        description = '. '.join(sentences[:3]) + '.' if len(sentences) > 3 else wiki_summary
    
    # Post content
    location_text = f" ({place.get('location', '')})" if place.get('location') else ""
    content = f"""# The Current State of {place['name']}{location_text}

{description}

## The Past

{place['name']} was once a place beloved by many. How has this place changed over time?

{image_markdown}

## Conclusion

We've explored the current state of {place['name']}, a place that was once popular and thriving. While places change with the passage of time, the memories and stories remain.

---

*This post was generated using Google Custom Search API, Wikipedia API, and Google Trends, searching for images from within the last month.*
"""
    
    # Generate front matter
    post = frontmatter.Post(content)
    tags = [place['name'], "abandoned places", "current state"]
    if place.get('location'):
        tags.append(place['location'])
    
    post.metadata = {
        "title": f"The Current State of {place['name']}",
        "date": date.strftime("%Y-%m-%d %H:%M:%S"),
        "categories": ["Place Exploration"],
        "tags": tags
    }
    
    # Save file
    POSTS_DIR.mkdir(exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))
    
    print(f"Post created successfully: {filepath}")
    return filepath


def select_place_by_trend():
    """
    Select a place based on Google Trends scores.
    Places with higher trends are more likely to be selected.
    Falls back to random selection if trends unavailable.
    """
    import random
    
    if not PTRENDS_AVAILABLE:
        # Fallback to random if pytrends not available
        print("pytrends not available, using random selection")
        return random.choice(PLACES)
    
    print("Checking Google Trends for all places...")
    place_scores = []
    successful_scores = 0
    
    for i, place in enumerate(PLACES):
        place_name = place['name']
        location = place.get('location', '')
        
        # Get trend score
        score = get_trend_score(place_name, location)
        place_scores.append((place, score))
        
        # Only count non-default scores as successful
        if score != 50:
            successful_scores += 1
        
        print(f"  {place_name}: Trend score = {score}")
        
        # Longer delay to avoid rate limiting (3 seconds between requests)
        if i < len(PLACES) - 1:  # Don't sleep after last item
            time.sleep(3)
    
    # If we got rate limited (all scores are 50), fall back to random
    if successful_scores == 0:
        print("\n⚠️  Google Trends rate limited. Falling back to random selection.")
        return random.choice(PLACES)
    
    # Sort by trend score (highest first)
    place_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Weighted random selection: higher trend = higher chance
    # Use top 5 places for weighted selection
    top_places = place_scores[:5]
    weights = [score for _, score in top_places]
    
    # Normalize weights
    total_weight = sum(weights)
    if total_weight > 0:
        weights = [w / total_weight for w in weights]
        selected_place = random.choices(
            [place for place, _ in top_places],
            weights=weights,
            k=1
        )[0]
    else:
        selected_place = top_places[0][0]
    
    return selected_place


def main():
    """
    Main function: Select a place based on trends and generate a post.
    """
    import random
    
    # Check API key and CSE ID
    if not CUSTOM_SEARCH_ENGINE_ID or CUSTOM_SEARCH_ENGINE_ID == "YOUR_CSE_ID_HERE":
        print("Warning: GOOGLE_CSE_ID environment variable is not set.")
        print("Please set GOOGLE_CSE_ID in GitHub Secrets or as an environment variable.")
        return
    
    if not GOOGLE_API_KEY:
        print("Warning: GOOGLE_API_KEY is not set.")
        return
    
    # Select place (random for now, can enable trends later)
    print("\n" + "="*50)
    print("Selecting place...")
    print("="*50)
    
    import random
    # For now, use random selection to avoid rate limiting
    # Can enable trends later: place = select_place_by_trend()
    place = random.choice(PLACES)
    
    print(f"\n✅ Selected place: {place['name']}")
    if place.get('location'):
        print(f"   Location: {place['location']}")
    
    # Get Wikipedia information
    print(f"\nFetching information about {place['name']}...")
    wiki_info = get_wikipedia_info(place['name'], place.get('location', ''))
    
    if wiki_info.get('summary'):
        print(f"   Found Wikipedia page: {wiki_info.get('title', 'N/A')}")
        print(f"   Extracted keywords: {', '.join(wiki_info.get('keywords', []))}")
    else:
        print("   Wikipedia information not available, using default description")
    
    print("\n" + "="*50)
    
    # Generate post with Wikipedia info
    post_path = create_post(place, wiki_info)
    
    if post_path:
        print(f"\n✅ Post generated successfully: {post_path}")
    else:
        print("\n❌ Failed to generate post.")


if __name__ == "__main__":
    main()

