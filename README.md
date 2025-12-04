# Abandoned Places Blog - Automated Posting System

An automated blog posting system using GitHub Pages. Automatically generates blog posts about the current state of places that were once popular around the world, using Google Custom Search API.

## Key Features

- 🤖 **Automated Posting**: Daily automatic post generation via GitHub Actions
- 🔍 **Image Search**: Google Custom Search API for searching images from within the last month
- 💰 **Monetization**: Google AdSense integration for ad revenue
- 📱 **Responsive Design**: Mobile-friendly Jekyll-based blog

## Project Structure

```
goto_hannam/
├── _config.yml              # Jekyll configuration file
├── _layouts/                # Layout templates
│   ├── default.html
│   └── post.html
├── _posts/                  # Auto-generated post files
├── _includes/               # Include files
│   ├── google-adsense.html
│   └── social.html
├── assets/                  # CSS and other assets
├── scripts/                 # Automation scripts
│   ├── generate_post.py     # Post generation script
│   └── config.example.yaml  # Configuration file example
├── .github/
│   └── workflows/
│       ├── auto-post.yml     # GitHub Actions workflow for auto-posting
│       └── jekyll.yml        # GitHub Actions workflow for Jekyll build
├── Gemfile                  # Ruby dependencies
├── requirements.txt         # Python dependencies
└── README.md
```

## Setup Instructions

### 1. Google Custom Search Engine Setup

1. Visit [Google Custom Search Engine](https://programmablesearchengine.google.com/)
2. Create a new search engine
3. Select "Search the entire web" option
4. Copy the generated **Search Engine ID (CSE ID)**

### 2. GitHub Secrets Configuration

Add the following secrets in your GitHub repository:
Settings > Secrets and variables > Actions:

- `GOOGLE_API_KEY`: Your Google API key (`AIzaSyBUrWy_QcqzNFbRPik7Dm7MqXmIbqmG-Gw`)
- `GOOGLE_CSE_ID`: Your Custom Search Engine ID (`8690747c4ec274a1e`)

### 3. Google AdSense Setup

1. Sign up for [Google AdSense](https://www.google.com/adsense/)
2. After site approval, enter your Publisher ID in `_config.yml` under `google_adsense`
3. Enter your ad slot ID in `_includes/google-adsense.html` replacing `YOUR_AD_SLOT_ID`

### 4. Local Testing

```bash
# Install Python dependencies
pip install -r requirements.txt

# Set environment variables (Windows PowerShell)
$env:GOOGLE_API_KEY="AIzaSyBUrWy_QcqzNFbRPik7Dm7MqXmIbqmG-Gw"
$env:GOOGLE_CSE_ID="8690747c4ec274a1e"

# Test post generation
python scripts/generate_post.py
```

### 5. Run Jekyll Local Server

```bash
# Install Ruby dependencies
bundle install

# Run local server
bundle exec jekyll serve
```

Visit `http://localhost:4000` in your browser to preview.

## GitHub Pages Deployment

1. Go to your repository Settings > Pages
2. Select "GitHub Actions" as the source
3. GitHub Actions will automatically build and deploy your site

## Auto-Posting Schedule

The GitHub Actions workflow runs automatically every day to generate new posts:
- Execution time: Daily at 9:00 AM (UTC) = 6:00 PM KST
- Manual execution: You can manually run the "자동 포스팅 생성" workflow from the GitHub Actions tab

## Adding Post Topics

You can add new places to the `PLACES` list in `scripts/generate_post.py`:

```python
PLACES = [
    {"name": "Times Square", "location": "New York, USA", "description": "..."},
    {"name": "Detroit", "location": "Michigan, USA", "description": "..."},
    # Add new places
    {"name": "New Place", "location": "Location", "description": "Description"},
]
```

## Important Notes

1. **API Quota**: Google Custom Search API has limited free quota (100 requests per day). Consider a paid plan if needed.

2. **Image Copyright**: Verify copyright of searched images and obtain permission from image owners if necessary.

3. **Content Quality**: Regularly review and improve the quality of auto-generated posts.

4. **AdSense Policy**: Comply with Google AdSense policies to avoid account suspension.

## License

This project is licensed under the MIT License.

## Contributing

Please file issues for bug reports or feature suggestions.
