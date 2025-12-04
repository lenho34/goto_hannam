# Script Usage

## generate_post.py

Automated blog post generation script.

### Usage

```bash
# Set environment variables
export GOOGLE_API_KEY="your-api-key"
export GOOGLE_CSE_ID="your-cse-id"

# Run script
python scripts/generate_post.py
```

### Running on Windows PowerShell

```powershell
$env:GOOGLE_API_KEY="your-api-key"
$env:GOOGLE_CSE_ID="your-cse-id"
python scripts/generate_post.py
```

### Features

- Image search using Google Custom Search API
- Search images from within the last month only
- Automatic generation of Jekyll-formatted markdown files
- Automatic front matter generation

### Output

Generated posts are saved in the `_posts/` directory.

Filename format: `YYYY-MM-DD-place-name.md`
