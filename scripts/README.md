# Script Usage

## generate_post.py

Automated blog post generation script with smart place selection and content enrichment.

### Features

- **Google Trends Integration**: Selects places based on current search trends
- **Wikipedia API**: Automatically fetches place information and extracts characteristic keywords
- **Smart Image Search**: Uses extracted keywords to find more relevant images
- **Automatic Content Generation**: Creates rich blog posts with Wikipedia summaries

### Usage

```bash
# Set environment variables
export GOOGLE_API_KEY="your-api-key"
export GOOGLE_CSE_ID="your-cse-id"

# Install dependencies (including pytrends and wikipedia)
pip install -r requirements.txt

# Run script
python scripts/generate_post.py
```

### Running on Windows PowerShell

```powershell
$env:GOOGLE_API_KEY="your-api-key"
$env:GOOGLE_CSE_ID="your-cse-id"
python scripts/generate_post.py
```

### How It Works

1. **Trend-Based Selection**: Checks Google Trends for all places and selects one with high search interest
2. **Wikipedia Research**: Fetches Wikipedia page for the selected place
3. **Keyword Extraction**: Extracts characteristic keywords (e.g., "abandoned", "ruins", "mining")
4. **Smart Image Search**: Searches for images using place name + keywords
5. **Post Generation**: Creates blog post with Wikipedia summary and relevant images

### Output

Generated posts are saved in the `_posts/` directory.

Filename format: `YYYY-MM-DD-place-name.md`

### Dependencies

- `pytrends`: Google Trends data
- `wikipedia`: Wikipedia API access
- `requests`: HTTP requests
- `python-frontmatter`: Markdown front matter handling
