"""
AI Newsletter Generator using Google ADK
Reads news articles, selects top stories per category using AI agents,
summarizes articles, and generates a newsletter ready for email.
"""

import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.genai import types
from datetime import datetime
import asyncio
import uuid
from typing import List

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.plugins.logging_plugin import LoggingPlugin

# Load environment variables
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_ID = "gemini-2.5-flash-lite"

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file!")

# Retry configuration
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)


def read_news_csv(filepath: str = "news_articles.csv") -> pd.DataFrame:
    """Read the news articles CSV file."""
    try:
        return pd.read_csv(filepath)
    except FileNotFoundError:
        raise FileNotFoundError(f"{filepath} not found. Please run rss_feeds.py first.")


def get_articles_by_category(df: pd.DataFrame) -> dict:
    """Group articles by category."""
    categories = {}
    for category in df['category'].unique():
        categories[category] = df[df['category'] == category].to_dict('records')
    return categories


def fetch_article_content(url: str) -> str:
    """Fetch and extract text content from an article URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        paragraphs = soup.find_all('p')
        text = ' '.join(p.get_text().strip() for p in paragraphs)

        return text[:5000] if len(text) > 5000 else text

    except Exception:
        return ""


# Agent Instructions
ARTICLE_SELECTOR_INSTRUCTION = """
You are an expert news editor. Analyze news article titles and select the TWO most important and newsworthy articles.

Return exactly two titles formatted as:
SELECTED:
1. [title]
2. [title]
"""

ARTICLE_SUMMARIZER_INSTRUCTION = """
You are a skilled journalist. Summarize the article in exactly three lines:
1. Main event
2. Key context or details
3. Why it matters
"""


# Agents
article_selector_agent = LlmAgent(
    name="ArticleSelectorAgent",
    model=Gemini(model=MODEL_ID, retry_options=retry_config),
    description="Selects the two most newsworthy articles",
    instruction=ARTICLE_SELECTOR_INSTRUCTION,
)

article_summarizer_agent = LlmAgent(
    name="ArticleSummarizerAgent",
    model=Gemini(model=MODEL_ID, retry_options=retry_config),
    description="Summarizes news articles in exactly three lines",
    instruction=ARTICLE_SUMMARIZER_INSTRUCTION,
)

root_agent = SequentialAgent(
    name="NewsletterAgent",
    sub_agents=[article_selector_agent, article_summarizer_agent],
    description="Agent chain that selects and summarizes articles",
)

root_runner = InMemoryRunner(agent=root_agent, plugins=[LoggingPlugin()])
selector_runner = InMemoryRunner(agent=article_selector_agent, plugins=[LoggingPlugin()])
summarizer_runner = InMemoryRunner(agent=article_summarizer_agent, plugins=[LoggingPlugin()])


async def select_top_articles(category: str, articles: list) -> list:
    """Use ArticleSelectorAgent to select the top 2 articles."""
    if len(articles) <= 2:
        return articles

    titles_text = "\n".join(f"- {article['title']}" for article in articles[:20])
    prompt = (
        f"Category: {category.upper()}\n\nHere are the article titles:\n"
        f"{titles_text}\n\nSelect the two strongest choices."
    )

    response_text = ""
    session_id = str(uuid.uuid4())

    async for event in selector_runner.run_async(
        user_id="user", session_id=session_id, new_message=prompt
    ):
        if hasattr(event, "content") and hasattr(event.content, "parts"):
            for part in event.content.parts:
                if hasattr(part, "text"):
                    response_text += part.text

    if not response_text:
        return articles[:2]

    selected = []
    for article in articles:
        title = article["title"].lower()
        lines = [line.lower() for line in response_text.split("\n") if len(line) > 5]

        if any(title in line or line in title for line in lines):
            selected.append(article)
            if len(selected) == 2:
                break

    return selected if len(selected) == 2 else articles[:2]


async def summarize_article(title: str, url: str, content: str = None) -> str:
    """Use ArticleSummarizerAgent to summarize an article."""
    if not content:
        content = fetch_article_content(url)

    if content:
        prompt = (
            f"Article Title: {title}\nArticle URL: {url}\n\n"
            f"Article Content:\n{content[:3000]}\n\n"
            "Provide a 3-line summary."
        )
    else:
        prompt = (
            f"Article Title: {title}\nArticle URL: {url}\n\n"
            "Provide a likely 3-line summary based on the title."
        )

    summary_text = ""
    session_id = str(uuid.uuid4())

    async for event in summarizer_runner.run_async(
        user_id="user", session_id=session_id, new_message=prompt
    ):
        if hasattr(event, "content") and hasattr(event.content, "parts"):
            for part in event.content.parts:
                if hasattr(part, "text"):
                    summary_text += part.text

    return summary_text.strip() if summary_text else "Summary unavailable."


async def process_category(category: str, articles: list) -> list:
    """Select and summarize articles."""
    selected = await select_top_articles(category, articles)

    processed = []
    for article in selected:
        summary = await summarize_article(article["title"], article["link"])
        item = article.copy()
        item["summary"] = summary
        processed.append(item)

    return processed


def generate_newsletter(selected_articles: dict) -> str:
    """Generate plain-text newsletter without separator lines."""
    today = datetime.now().strftime("%B %d, %Y")

    newsletter = f"""
Daily News Digest
{today}

A curated selection of noteworthy news from around the world.

"""

    category_titles = {
        "politics": "POLITICS",
        "economics": "ECONOMICS & BUSINESS",
        "technology": "TECHNOLOGY",
        "science": "SCIENCE",
        "health": "HEALTH",
        "sports": "SPORTS",
        "entertainment": "ENTERTAINMENT",
        "crime": "CRIME & JUSTICE",
        "general": "GENERAL NEWS",
    }

    for category, articles in selected_articles.items():
        if not articles:
            continue

        heading = category_titles.get(category, category.upper())

        newsletter += f"\n{heading}\n\n"

        for article in articles:
            newsletter += (
                f"{article['title']}\n"
                f"Source: {article.get('source', 'Unknown')}\n\n"
                f"{article.get('summary', 'Summary unavailable.')}\n\n"
                f"Read more: {article['link']}\n\n"
            )

    newsletter += (
        "\nThank you for reading the Daily News Digest.\n"
        'To unsubscribe, reply with "UNSUBSCRIBE".\n'
    )

    return newsletter


def generate_html_newsletter(selected_articles: dict) -> str:
    """Generate HTML newsletter (already had no ASCII separators)."""
    today = datetime.now().strftime("%B %d, %Y")

    category_titles = {
        "politics": "POLITICS",
        "economics": "ECONOMICS & BUSINESS",
        "technology": "TECHNOLOGY",
        "science": "SCIENCE",
        "health": "HEALTH",
        "sports": "SPORTS",
        "entertainment": "ENTERTAINMENT",
        "crime": "CRIME & JUSTICE",
        "general": "GENERAL NEWS",
    }

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Daily News Digest - {today}</title>
    <style>
        body {{
            font-family: Georgia, serif;
            line-height: 1.6;
            color: #333;
            margin: 0 auto;
            max-width: 700px;
            padding: 20px;
        }}
        .header {{
            background: #2b6cb0;
            color: white;
            padding: 25px;
            text-align: center;
            border-radius: 8px;
            margin-bottom: 25px;
        }}
        .category {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 25px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .article-title {{
            font-weight: bold;
            font-size: 18px;
            margin-bottom: 6px;
        }}
        .read-more {{
            font-weight: bold;
            color: #2b6cb0;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Daily News Digest</h1>
        <div>{today}</div>
    </div>
"""

    for category, articles in selected_articles.items():
        if not articles:
            continue

        heading = category_titles.get(category, category.upper())

        html += f"""
    <div class="category">
        <h2>{heading}</h2>
"""

        for article in articles:
            summary_html = article.get("summary", "").replace("\n", "<br>")
            html += f"""
        <div class="article">
            <div class="article-title">{article['title']}</div>
            <div>{summary_html}</div>
            <a class="read-more" href="{article['link']}">Read full article</a>
        </div>
"""

        html += "    </div>\n"

    html += """
</body>
</html>
"""

    return html


async def main():
    """Main execution function."""
    print("Generating newsletter...")

    df = read_news_csv("news_articles.csv")
    if df.empty:
        print("No articles were found. Exiting.")
        return

    articles_by_category = get_articles_by_category(df)

    selected_articles = {}
    for category, articles in articles_by_category.items():
        print(f"Processing category: {category}")
        selected_articles[category] = await process_category(category, articles)

    newsletter_text = generate_newsletter(selected_articles)
    newsletter_html = generate_html_newsletter(selected_articles)

    with open("newsletter.txt", "w", encoding="utf-8") as f:
        f.write(newsletter_text)

    with open("newsletter.html", "w", encoding="utf-8") as f:
        f.write(newsletter_html)

    print("Newsletter generation complete.")
    print("Files saved: newsletter.txt, newsletter.html")

    return newsletter_text, newsletter_html


if __name__ == "__main__":
    asyncio.run(main())
