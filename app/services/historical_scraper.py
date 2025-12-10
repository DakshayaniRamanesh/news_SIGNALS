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
    
    Args:
        start_date (str): YYYY-MM-DD
        end_date (str): YYYY-MM-DD
        query (str): Search query
        
    Returns:
        list: Processed news items as a list of dictionaries.
    """
    # Construct Google News RSS URL
    # Format: https://news.google.com/rss/search?q={query}+after:{start}+before:{end}&hl=en-LK&gl=LK&ceid=LK:en
    base_url = "https://news.google.com/rss/search"
    search_query = f"{query} after:{start_date} before:{end_date}"
    
    params = {
        "q": search_query,
        "hl": "en-LK",
        "gl": "LK",
        "ceid": "LK:en"
    }
    
    logger.info(f"Scraping historical data for query: {search_query}")
    
    try:
        # distinct User-Agent to avoid blocking
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(base_url, params=params, headers=headers)
        response.raise_for_status()
        
        feed = feedparser.parse(io.BytesIO(response.content))
        
        if not feed.entries:
            logger.info("No entries found in Google News RSS for this period.")
            return []
            
        rows = []
        for e in feed.entries:
            # Google News items often don't have a simple summary, sometimes it's in description
            summary = e.get("description", "")
            # Clean up Google's specific html in description if needed, or leave for data_processor
            
            rows.append({
                "Source": e.get("source", {}).get("title", "Google News"),
                "Title": e.get("title", ""),
                "Link": e.get("link", ""),
                "Summary": summary,
                "Published": e.get("published", ""),
                "SEO_Score": 5.0 # Default score for external fetched
            })
            
        if not rows:
            return []
            
        # Convert to DataFrame
        df = pd.DataFrame(rows)
        
        # Process using the existing robust pipeline
        processed_df = process_articles(df)
        
        # Save to history so we don't need to scrape again
        save_to_history(processed_df, "data")
        
        # Return as list of dicts for the API
        return processed_df.to_dict(orient="records")
        
    except Exception as e:
        logger.error(f"Error during historical scraping: {e}")
        return []
