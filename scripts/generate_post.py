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
    
    except KeyboardInterrupt:
        # User interrupted - re-raise
        raise
    except Exception as e:
        # Rate limiting or other errors - return default score
        # Don't print error for rate limiting (429) or network errors to avoid spam
        error_str = str(e).lower()
        if "429" not in error_str and "timeout" not in error_str and "interrupt" not in error_str:
            print(f"  ⚠️  Error getting trend score for {place_name}: {type(e).__name__}")
        return 50  # Default score on error


def get_wikipedia_info(place_name, location=""):
    """
    Get Wikipedia information for a place.
    Returns a dictionary with summary, keywords, full text, and historical events.
    """
    if not WIKIPEDIA_AVAILABLE:
        return {
            "summary": "",
            "keywords": [],
            "full_text": "",
            "historical_events": []
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
        
        # Extract historical events from full content
        full_content = page.content[:10000]  # First 10000 chars for better historical context
        historical_events = extract_historical_events(full_content, place_name)
        
        return {
            "summary": page.summary,
            "keywords": extract_keywords(page.summary + " " + full_content[:2000]),
            "full_text": full_content,
            "url": page.url,
            "title": page.title,
            "historical_events": historical_events
        }
    
    except Exception as e:
        print(f"Error getting Wikipedia info for {place_name}: {e}")
        return {
            "summary": "",
            "keywords": [],
            "full_text": "",
            "historical_events": []
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


def extract_historical_events(wiki_text, place_name):
    """
    Extract historical events from Wikipedia text.
    Returns a list of historical event descriptions.
    """
    if not wiki_text:
        return []
    
    # Keywords that indicate historical events
    historical_keywords = [
        "war", "battle", "disaster", "crisis", "revolution", "invasion",
        "earthquake", "fire", "evacuation", "abandonment", "decline",
        "collapse", "destruction", "attack", "bombing", "conflict",
        "epidemic", "pandemic", "strike", "riot", "uprising",
        "established", "founded", "built", "destroyed", "evacuated",
        "closed", "abandoned", "declared", "announced"
    ]
    
    # Split text into sentences
    sentences = re.split(r'[.!?]+', wiki_text)
    historical_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 30:  # Skip very short sentences
            continue
        
        sentence_lower = sentence.lower()
        # Check if sentence contains historical keywords
        for keyword in historical_keywords:
            if keyword in sentence_lower:
                # Check if sentence mentions the place name
                if place_name.lower() in sentence_lower:
                    historical_sentences.append(sentence)
                    break
        
        # Limit to top 5 historical events
        if len(historical_sentences) >= 5:
            break
    
    return historical_sentences[:5]


def search_images(query, num_results=10, date_restrict=None):
    """
    Search for images using Google Custom Search API.
    If date_restrict is None, searches all time (most relevant).
    """
    url = "https://www.googleapis.com/customsearch/v1"
    
    params = {
        "key": GOOGLE_API_KEY,
        "cx": CUSTOM_SEARCH_ENGINE_ID,
        "q": query,
        "searchType": "image",
        "num": num_results,
        "safe": "active",
        "imgSize": "large",
        "imgType": "photo"
    }
    
    # Only add dateRestrict if specified
    if date_restrict:
        params["dateRestrict"] = date_restrict
    
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
    return search_images(query, num_results, date_restrict=None)


def search_image_for_event(place_name, location, event_text, num_results=1):
    """
    Search for an image related to a specific historical event.
    Returns the most relevant image.
    """
    # Extract key terms from event text
    event_lower = event_text.lower()
    key_terms = []
    
    # Extract important keywords from the event
    important_words = ["war", "battle", "disaster", "fire", "earthquake", 
                      "evacuation", "bombing", "attack", "surrender", 
                      "victory", "hiatus", "restriction", "announced",
                      "world war", "wwii", "ww2", "wwi", "ww1"]
    
    # Check for multi-word phrases first
    if "world war ii" in event_lower or "wwii" in event_lower or "ww2" in event_lower:
        key_terms.append("World War II")
    elif "world war i" in event_lower or "wwi" in event_lower or "ww1" in event_lower:
        key_terms.append("World War I")
    
    # Then check for single words
    for word in important_words:
        if word in event_lower and word not in ["world war", "wwii", "ww2", "wwi", "ww1"]:
            key_terms.append(word)
    
    # Build query: place name + location + key event terms
    if key_terms:
        # Use place name + key terms for better relevance
        query = f"{place_name} {location} {' '.join(key_terms[:2])}"
    else:
        # Fallback: use place name and extract year if present
        year_match = re.search(r'\b(19|20)\d{2}\b', event_text)
        if year_match:
            query = f"{place_name} {location} {year_match.group()}"
        else:
            # Use first few meaningful words
            event_words = [w for w in event_text.split() if len(w) > 3][:4]
            query = f"{place_name} {location} {' '.join(event_words)}"
    
    print(f"  Searching image for event: {event_text[:60]}...")
    images = search_images(query, num_results, date_restrict=None)
    
    if images:
        return images[0]
    return None


def generate_event_description(event_text, place_name, max_length=200):
    """
    Generate a concise description of a historical event (max 200 characters).
    """
    # Clean up the event text
    event = event_text.strip()
    
    # Remove extra spaces
    event = re.sub(r'\s+', ' ', event)
    
    # If already short enough, return as is
    if len(event) <= max_length:
        return event
    
    # Try to truncate at sentence boundary (look for periods, exclamation, question marks)
    for delimiter in ['. ', '! ', '? ', ', ']:
        if delimiter in event:
            parts = event.split(delimiter)
            result = ""
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                # Check if adding this part would exceed limit
                if result:
                    test_result = result + delimiter + part
                else:
                    test_result = part
                
                if len(test_result) <= max_length:
                    result = test_result
                else:
                    break
            
            if result and len(result) <= max_length:
                return result
    
    # If no sentence boundary works, truncate at word boundary
    words = event.split()
    result = ""
    for word in words:
        if result:
            test_result = result + ' ' + word
        else:
            test_result = word
        
        if len(test_result) <= max_length - 3:
            result = test_result
        else:
            break
    
    # Return truncated result with ellipsis
    if result:
        return result + '...'
    else:
        # Fallback: just truncate at character limit
        return event[:max_length - 3] + '...'


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
    
    # Search images for current state section
    print(f"Searching for current state images of '{place['name']}' using keywords: {keywords}")
    images = search_images_by_features(
        place['name'], 
        place.get('location', ''), 
        keywords,
        num_results=5
    )
    
    if not images:
        print(f"Warning: No current state images found for '{place['name']}'.")
        images = []
    
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
    
    # Generate current state image markdown
    image_markdown = ""
    if images:
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
    
    # Generate historical events section with images and descriptions
    historical_events_text = ""
    if wiki_info.get('historical_events'):
        historical_events_text = "\n## Historical Events\n\n"
        
        for i, event in enumerate(wiki_info['historical_events'], 1):
            # Search for image related to this event
            event_image = search_image_for_event(
                place['name'], 
                place.get('location', ''), 
                event
            )
            
            # Generate concise description (200 characters max)
            event_description = generate_event_description(event, place['name'])
            
            # Add event with image and description
            historical_events_text += f"### {i}. {event_description}\n\n"
            
            if event_image:
                historical_events_text += f"![{place['name']} historical event {i}]({event_image['url']})\n\n"
                historical_events_text += f"*{event_image['title']}*\n\n"
            else:
                historical_events_text += f"*이미지를 찾을 수 없습니다.*\n\n"
            
            # Add delay between image searches to avoid rate limiting
            if i < len(wiki_info['historical_events']):
                time.sleep(1)
    else:
        # Fallback if no historical events found
        historical_events_text = "\n## Historical Background\n\n"
        historical_events_text += f"{place['name']} has a rich history marked by significant events that shaped its current state. "
        historical_events_text += f"From its founding to its decline, this place has witnessed many historical moments that reflect the changes of time.\n\n"
    
    # Post content
    location_text = f" ({place.get('location', '')})" if place.get('location') else ""
    content = f"""# The Current State of {place['name']}{location_text}

{description}

{historical_events_text}

{image_markdown}

## Conclusion

We've explored the current state of {place['name']}, a place that was once popular and thriving. While places change with the passage of time, the memories and stories remain.

---

*This post was generated using Google Custom Search API, Wikipedia API, and Google Trends.*
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
    Select a place with the highest Google Trends score.
    Returns the place with the highest trend score (non-random).
    Falls back to first place if trends unavailable.
    """
    import random
    
    if not PTRENDS_AVAILABLE:
        # Fallback to first place if pytrends not available
        print("⚠️  pytrends not available, selecting first place from list")
        return PLACES[0]
    
    print("Checking Google Trends for all places...")
    place_scores = []
    successful_scores = 0
    
    for i, place in enumerate(PLACES):
        place_name = place['name']
        location = place.get('location', '')
        
        try:
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
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user. Using scores collected so far...")
            break
        except Exception as e:
            print(f"  ⚠️  Skipping {place_name} due to error: {type(e).__name__}")
            place_scores.append((place, 50))  # Default score
            if i < len(PLACES) - 1:
                time.sleep(1)  # Shorter delay on error
    
    # If we got rate limited (all scores are 50), use first place
    if successful_scores == 0:
        print("\n⚠️  Google Trends rate limited. Selecting first place from list.")
        return PLACES[0]
    
    # Sort by trend score (highest first)
    place_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Select the place with the highest trend score (non-random)
    selected_place, highest_score = place_scores[0]
    print(f"\n✅ Selected place with highest trend score: {selected_place['name']} (score: {highest_score})")
    
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
    
    # Select place based on Google Trends score
    print("\n" + "="*50)
    print("Selecting place based on Google Trends...")
    print("="*50)
    
    place = select_place_by_trend()
    
    print(f"\n✅ Selected place: {place['name']}")
    if place.get('location'):
        print(f"   Location: {place['location']}")
    
    # Get Wikipedia information
    print(f"\nFetching information about {place['name']}...")
    wiki_info = get_wikipedia_info(place['name'], place.get('location', ''))
    
    if wiki_info.get('summary'):
        print(f"   Found Wikipedia page: {wiki_info.get('title', 'N/A')}")
        print(f"   Extracted keywords: {', '.join(wiki_info.get('keywords', []))}")
        if wiki_info.get('historical_events'):
            print(f"   Found {len(wiki_info['historical_events'])} historical events")
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

