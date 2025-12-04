#!/usr/bin/env python3
"""
Automated blog post generation script
Uses Google Custom Search API to search for images and generate blog posts.
"""

import os
import json
import re
import requests
from datetime import datetime, timedelta
from pathlib import Path
import yaml
import frontmatter

# Configuration
# Read API key from environment variable or use default
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyBUrWy_QcqzNFbRPik7Dm7MqXmIbqmG-Gw")
# Custom Search Engine ID must be created at Google Custom Search
# Available at https://programmablesearchengine.google.com/
# Your CSE ID: 8690747c4ec274a1e
CUSTOM_SEARCH_ENGINE_ID = os.getenv("GOOGLE_CSE_ID", "8690747c4ec274a1e")

POSTS_DIR = Path("_posts")
IMAGES_DIR = Path("images")

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


def create_post(place):
    """
    Generate a blog post based on place information.
    """
    # Create search query
    query = f"{place['name']} {place.get('location', '')} current state abandoned"
    
    print(f"Searching for images of '{place['name']}'...")
    images = search_images(query, num_results=5)
    
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
    
    # Post content
    location_text = f" ({place.get('location', '')})" if place.get('location') else ""
    content = f"""# The Current State of {place['name']}{location_text}

{place['description']}

## The Past

{place['name']} was once a place beloved by many. How has this place changed over time?

{image_markdown}

## Conclusion

We've explored the current state of {place['name']}, a place that was once popular and thriving. While places change with the passage of time, the memories and stories remain.

---

*This post was generated using Google Custom Search API, searching for images from within the last month.*
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


def main():
    """
    Main function: Randomly select a place and generate a post.
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
    
    # Randomly select a place
    place = random.choice(PLACES)
    
    print(f"\nSelected place: {place['name']}")
    if place.get('location'):
        print(f"Location: {place['location']}")
    print(f"Search query: {place['name']} current state\n")
    
    # Generate post
    post_path = create_post(place)
    
    if post_path:
        print(f"\n✅ Post generated successfully: {post_path}")
    else:
        print("\n❌ Failed to generate post.")


if __name__ == "__main__":
    main()

