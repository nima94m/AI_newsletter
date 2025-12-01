# AI News Digest Generator

This project automates the process of collecting news from major RSS feeds, using Google Gemini AI to select and summarize top stories, generating a clean daily newsletter (HTML + text), and sending it to your email inbox.

## Features

- **Multi-source news aggregation**: Fetches news from trusted sources (Reuters, BBC, NPR, AP, TechCrunch, ESPN, and more)
- **Smart categorization**: Automatically categorizes articles using keyword scoring
- **AI-powered selection**: Uses Gemini AI to select the top 2 articles per category
- **Intelligent summarization**: Uses Gemini AI to summarize each article in exactly 3 lines
- **Multiple output formats**: Generates both HTML and plain text newsletters
- **Email delivery**: Automatically sends the newsletter via Gmail SMTP
- **Google ADK integration**: Built with Google's Agent Development Kit (ADK) for robust AI agent orchestration

## Installation

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a `.env` file

Create a `.env` file in the project root with the following variables:

```env
GOOGLE_API_KEY=your_google_api_key
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_gmail_app_password
```

**Important**: Use a Gmail App Password, not your normal Gmail password. To generate an App Password:
1. Enable 2-Step Verification on your Google Account
2. Go to Google Account settings → Security → App passwords
3. Generate a new app password for "Mail"
4. Use that password in your `.env` file

## Usage

### Step 1 — Fetch and categorize news

```bash
python rss_feeds.py
```

This creates:
- `news_articles.csv` - Contains all fetched articles organized by category

### Step 2 — Generate the newsletter

```bash
python newsletter_generator.py
```

This produces:
- `newsletter.txt` - Plain text version of the newsletter
- `newsletter.html` - HTML version ready for email

### Step 3 — Send the newsletter by email

```bash
python send_newsletter.py
```

The newsletter will be sent to the recipient specified in `send_newsletter.py` (default: `nima.mashayekhi@gmail.com`).

## Architecture

This project uses Google ADK's `SequentialAgent` pattern:

- **Root Agent** (`NewsletterAgent`): A `SequentialAgent` that orchestrates the workflow
- **Sub-agent 1** (`ArticleSelectorAgent`): Selects the top 2 most newsworthy articles per category
- **Sub-agent 2** (`ArticleSummarizerAgent`): Generates 3-line summaries for each selected article

All agents use:
- **Model**: `gemini-2.5-flash-lite`
- **Retry configuration**: Automatic retry on rate limits (429, 500, 503, 504 errors)
- **Logging**: `LoggingPlugin()` for observability and debugging


## Project Structure

```
.
├── rss_feeds.py              # RSS feed fetching and categorization
├── newsletter_generator.py   # AI-powered newsletter generation
├── send_newsletter.py        # Email sending functionality
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (create this)
├── news_articles.csv         # Generated: Categorized articles
├── newsletter.txt            # Generated: Plain text newsletter
└── newsletter.html           # Generated: HTML newsletter
```


## Dependencies

Key dependencies include:
- `google-adk` - Google Agent Development Kit
- `google-genai` - Google Gemini API client
- `pandas` - Data manipulation
- `feedparser` - RSS feed parsing
- `beautifulsoup4` - HTML parsing for article content
- `python-dotenv` - Environment variable management
- `smtplib` - Email sending (built-in)

See `requirements.txt` for the complete list.

## License

This project is for educational purposes.

## Contributing

Feel free to submit issues or pull requests to improve this project!
