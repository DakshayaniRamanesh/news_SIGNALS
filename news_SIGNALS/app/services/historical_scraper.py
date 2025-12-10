import feedparser
import pandas as pd
import requests
import io
import logging
from app.services.data_processor import process_articles, save_to_history

logger = logging.getLogger(__name__)

def scrape_historical_data(start_date, end_date, query="Sri Lanka"):
    """
    Scrapes historical news from Google News RSS for the given date range.
    Now supports scraping multiple topics if query is 'ALL' or a list.
    """
    import time
    import random
    
    # If query is special flag "ALL", use a broad list of keywords to maximize data
    queries = []
    if query == "ALL":
        queries = [
            "Sri Lanka", 
            "Colombo", 
            "Sri Lanka Economy", 
            "Sri Lanka Politics", 
            "Sri Lanka Crime",
            "Sri Lanka Weather",
            "Sri Lanka Sports",
            "Sri Lanka Tourism"
        ]
    elif isinstance(query, list):
        queries = query
    else:
        queries = [query]
        
    all_rows = []
    base_url = "https://news.google.com/rss/search"
    
    # distinct User-Agent to avoid blocking
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
    ]

    for q in queries:
        search_query = f"{q} after:{start_date} before:{end_date}"
        
        params = {
            "q": search_query,
            "hl": "en-LK",
            "gl": "LK",
            "ceid": "LK:en"
        }
        
        logger.info(f"Scraping historical data for query: {search_query}")
        
        try:
            # Random delay between queries
            time.sleep(random.uniform(2.0, 5.0))
            
            headers = {"User-Agent": random.choice(user_agents)}
            
            response = requests.get(base_url, params=params, headers=headers, timeout=20)
            response.raise_for_status()
            
            feed = feedparser.parse(io.BytesIO(response.content))
            
            if not feed.entries:
                logger.info(f"No entries found for {q}")
                continue
                
            logger.info(f"Found {len(feed.entries)} entries for {q}")
            
            for e in feed.entries:
                summary = e.get("description", "")
                all_rows.append({
                    "Source": e.get("source", {}).get("title", "Google News"),
                    "Title": e.get("title", ""),
                    "Link": e.get("link", ""),
                    "Summary": summary,
                    "Published": e.get("published", ""),
                    "SEO_Score": 5.0
                })
                
        except Exception as e:
            logger.error(f"Error scraping query {q}: {e}")
            continue

    if not all_rows:
        return []
        
    # Remove duplicates based on Link
    unique_rows = {v['Link']: v for v in all_rows}.values()
    
    # Convert to DataFrame
    df = pd.DataFrame(unique_rows)
    
    # Process using the existing robust pipeline
    processed_df = process_articles(df)
    
    # Save to history
    save_to_history(processed_df, "data")
    
    # Return as list of dicts
    return processed_df.to_dict(orient="records")
