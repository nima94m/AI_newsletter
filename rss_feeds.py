"""
RSS News Aggregator
Fetches daily news from multiple RSS feeds and categorizes them by topic.
"""

import feedparser
import pandas as pd
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from tabulate import tabulate
import re
from typing import Optional

# RSS FEED SOURCES - Curated list of reliable daily news feeds

RSS_FEEDS = {
    # General News / Top Stories
    "Reuters Top News": {
        "url": "https://feeds.reuters.com/reuters/topNews",
        "default_category": "general"
    },
    "BBC World": {
        "url": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "default_category": "general"
    },
    "NPR News": {
        "url": "https://feeds.npr.org/1001/rss.xml",
        "default_category": "general"
    },
    "Associated Press": {
        "url": "https://rsshub.app/apnews/topics/apf-topnews",
        "default_category": "general"
    },

    # Politics
    "Reuters Politics": {
        "url": "https://feeds.reuters.com/Reuters/PoliticsNews",
        "default_category": "politics"
    },
    "BBC Politics": {
        "url": "http://feeds.bbci.co.uk/news/politics/rss.xml",
        "default_category": "politics"
    },
    "Politico": {
        "url": "https://rss.politico.com/politics-news.xml",
        "default_category": "politics"
    },

    # Business / Economics
    "Reuters Business": {
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "default_category": "economics"
    },
    "BBC Business": {
        "url": "http://feeds.bbci.co.uk/news/business/rss.xml",
        "default_category": "economics"
    },
    "CNBC Top News": {
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
        "default_category": "economics"
    },

    # Technology
    "Reuters Technology": {
        "url": "https://feeds.reuters.com/reuters/technologyNews",
        "default_category": "technology"
    },
    "TechCrunch": {
        "url": "https://techcrunch.com/feed/",
        "default_category": "technology"
    },
    "Ars Technica": {
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "default_category": "technology"
    },

    # Sports
    "ESPN Top Headlines": {
        "url": "https://www.espn.com/espn/rss/news",
        "default_category": "sports"
    },
    "BBC Sport": {
        "url": "http://feeds.bbci.co.uk/sport/rss.xml",
        "default_category": "sports"
    },

    # Science & Health
    "Reuters Health": {
        "url": "https://feeds.reuters.com/reuters/healthNews",
        "default_category": "health"
    },
    "BBC Science": {
        "url": "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "default_category": "science"
    },
    "NPR Science": {
        "url": "https://feeds.npr.org/1007/rss.xml",
        "default_category": "science"
    },

    # Entertainment
    "Reuters Entertainment": {
        "url": "https://feeds.reuters.com/reuters/entertainment",
        "default_category": "entertainment"
    },
    "BBC Entertainment": {
        "url": "http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
        "default_category": "entertainment"
    },
}

# CATEGORY KEYWORDS

CATEGORY_KEYWORDS = {
    "politics": [
        "election", "president", "congress", "senate", "parliament", "minister",
        "government", "vote", "democrat", "republican", "policy", "legislation",
        "campaign", "political", "diplomat", "embassy", "treaty", "sanction"
    ],
    "economics": [
        "economy", "market", "stock", "trade", "inflation", "gdp", "bank",
        "finance", "investment", "recession", "unemployment", "interest rate",
        "federal reserve", "wall street", "currency", "bitcoin", "crypto"
    ],
    "sports": [
        "game", "match", "championship", "league", "score", "player", "team",
        "football", "soccer", "basketball", "baseball", "tennis", "golf",
        "olympics", "tournament", "coach", "athlete", "nfl", "nba", "mlb"
    ],
    "crime": [
        "crime", "murder", "arrest", "police", "court", "trial", "prison",
        "criminal", "robbery", "fraud", "shooting", "investigation", "suspect",
        "charged", "convicted", "sentence", "lawsuit", "attorney"
    ],
    "technology": [
        "tech", "software", "ai", "artificial intelligence", "startup", "app",
        "google", "apple", "microsoft", "amazon", "meta", "cybersecurity",
        "data", "algorithm", "machine learning", "robot", "innovation"
    ],
    "health": [
        "health", "medical", "hospital", "doctor", "disease", "vaccine",
        "treatment", "cancer", "virus", "pandemic", "drug", "fda", "clinical",
        "patient", "surgery", "mental health", "covid", "research"
    ],
    "science": [
        "science", "research", "study", "discovery", "space", "nasa", "climate",
        "environment", "physics", "biology", "chemistry", "experiment",
        "scientist", "laboratory", "planet", "species", "evolution"
    ],
    "entertainment": [
        "movie", "film", "music", "celebrity", "actor", "singer", "concert",
        "album", "box office", "streaming", "netflix", "hollywood", "award",
        "grammy", "oscar", "emmy", "show", "series", "tv"
    ]
}


def categorize_article(title: str, summary: str, default_category: str) -> str:
    text = f"{title} {summary}".lower()
    category_scores = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score > 0:
            category_scores[category] = score

    if category_scores:
        return max(category_scores, key=category_scores.get)

    return default_category


def parse_date(entry) -> Optional[datetime]:
    date_fields = ['published', 'updated', 'pubDate', 'date']

    for field in date_fields:
        if hasattr(entry, field):
            try:
                return date_parser.parse(getattr(entry, field))
            except (ValueError, TypeError):
                continue

    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:6])
        except (ValueError, TypeError):
            pass

    if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        try:
            return datetime(*entry.updated_parsed[:6])
        except (ValueError, TypeError):
            pass

    return None


def fetch_rss_feed(feed_name: str, feed_info: dict) -> list:
    articles = []
    url = feed_info["url"]
    default_category = feed_info["default_category"]

    try:
        feed = feedparser.parse(url)

        if feed.bozo and not feed.entries:
            print(f"Warning: Could not parse {feed_name}")
            return articles

        for entry in feed.entries:
            title = entry.get('title', 'No Title')
            link = entry.get('link', '')
            summary = entry.get('summary', entry.get('description', ''))

            summary = re.sub(r'<[^>]+>', '', summary)
            summary = summary[:200] + "..." if len(summary) > 200 else summary

            pub_date = parse_date(entry)
            category = categorize_article(title, summary, default_category)

            articles.append({
                'source': feed_name,
                'category': category,
                'title': title[:100] + "..." if len(title) > 100 else title,
                'link': link,
                'date': pub_date.strftime('%Y-%m-%d %H:%M') if pub_date else 'Unknown',
                'date_obj': pub_date
            })

    except Exception as e:
        print(f"Error fetching {feed_name}: {str(e)}")

    return articles


def fetch_all_feeds(feed_selection: list = None) -> pd.DataFrame:
    all_articles = []

    feeds_to_fetch = RSS_FEEDS
    if feed_selection:
        feeds_to_fetch = {k: v for k, v in RSS_FEEDS.items() if k in feed_selection}

    print("Fetching RSS feeds...")

    for feed_name, feed_info in feeds_to_fetch.items():
        articles = fetch_rss_feed(feed_name, feed_info)
        all_articles.extend(articles)

    df = pd.DataFrame(all_articles)

    if not df.empty:
        df = df.sort_values('date', ascending=False)
        df = df.drop(columns=['date_obj'], errors='ignore')

    return df


def filter_todays_news(df: pd.DataFrame) -> pd.DataFrame:
    today = datetime.now().strftime('%Y-%m-%d')
    return df[df['date'].str.startswith(today)]


def filter_by_category(df: pd.DataFrame, categories: list) -> pd.DataFrame:
    return df[df['category'].isin(categories)]


def display_news_table(df: pd.DataFrame, title: str = "NEWS ARTICLES"):
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)

    if df.empty:
        print("No articles found.")
        return

    display_df = df[['category', 'title', 'link', 'date', 'source']].copy()
    display_df['link'] = display_df['link'].apply(lambda x: x[:50] + "..." if len(str(x)) > 50 else x)

    print(tabulate(display_df, headers='keys', tablefmt='grid', showindex=False))
    print(f"\nTotal articles: {len(df)}")


def get_category_summary(df: pd.DataFrame) -> pd.DataFrame:
    return df['category'].value_counts().reset_index()


def save_to_csv(df: pd.DataFrame, filename: str = "news_articles.csv"):
    df.to_csv(filename, index=False)
    print(f"Saved {len(df)} articles to {filename}")


def save_to_excel(df: pd.DataFrame, filename: str = "news_articles.xlsx"):
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='All Articles', index=False)

        for category in df['category'].unique():
            category_df = df[df['category'] == category]
            sheet_name = category.title()[:31]
            category_df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"Saved to {filename} with separate sheets per category")


# MAIN EXECUTION

if __name__ == "__main__":
    news_df = fetch_all_feeds()

    if not news_df.empty:
        print("\nArticle Count by Category")
        print(tabulate(
            get_category_summary(news_df),
            headers=['Category', 'Count'],
            tablefmt='grid'
        ))

        display_news_table(news_df, "ALL NEWS ARTICLES")

        favorite_topics = ['politics', 'economics', 'technology']
        filtered_df = filter_by_category(news_df, favorite_topics)
        display_news_table(filtered_df, f"Selected Topics: {', '.join(favorite_topics).title()}")

        save_to_csv(news_df, "news_articles.csv")

        print("\nNews aggregation complete.")
    else:
        print("No articles were fetched. Check your internet connection.")
