import pandas as pd
import os
import numpy as np
from datetime import datetime, timedelta
import re
import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

# Map user sectors to tags in our data
SECTOR_MAP = {
    "energy": ["energy", "fuel", "power", "electricity", "utility", "solar", "renewable"],
    "transport": ["transport", "logistics", "shipping", "aviation", "vehicle", "traffic", "highway"],
    "health": ["health", "medical", "pharmaceutical", "hospital", "medicine", "drug"],
    "economic": ["economic", "finance", "bank", "investment", "tax", "inflation", "market", "cbsl"],
    "technology": ["technology", "digital", "it", "cyber", "software", "telecom", "AI", "startup"],
    "construction": ["construction", "housing", "infrastructure", "real estate", "cement", "development"],
    "tourism": ["tourism", "hotel", "travel", "hospitality", "tourist", "airport"],
    "agriculture": ["agriculture", "food", "farming", "crop", "plantation", "fertilizer"],
    "retail": ["retail", "consumer", "shopping", "price", "goods", "market", "trade"],
    "manufacturing": ["manufacturing", "factory", "industrial", "production", "export"],
    "education": ["education", "school", "university", "student", "campus", "training"]
}

# Location keywords to filter news if a specific location is selected
LOCATION_MAP = {
    "colombo": ["colombo", "western province"],
    "gampaha": ["gampaha", "western province", "negombo", "katunayake"],
    "kandy": ["kandy", "central province", "peradeniya"],
    "galle": ["galle", "southern province", "hikkaduwa"],
    "jaffna": ["jaffna", "northern province"],
    "matara": ["matara", "southern province"],
    "kurunegala": ["kurunegala", "north western"],
    "trincomalee": ["trincomalee", "eastern province"],
    "batticaloa": ["batticaloa", "eastern province"],
    "nuwara_eliya": ["nuwara eliya", "hatton"],
    "hambantota": ["hambantota", "southern province", "mattala"]
}

# Knowledge base for generating suggestions based on various factors
SUGGESTION_KB = {
    "high_risk": {
        "energy": "Grid instability detected. Include budget for industrial-grade backup power (solar/diesel).",
        "transport": "Supply chain disruption probable. Diversify logistics partners.",
        "economic": "High market volatility. Minimize USD exposure and seek fixed-rate financing.",
        "construction": "Material cost fluctuation is high. Use cost-plus contracts where possible.",
        "general": "Environment is volatile. Adopt a lean operational model to minimize burn rate."
    },
    "inflation": "Rising operational costs detected. Implement dynamic pricing and secure long-term supplier contracts.",
    "tax": "New tax regulations likely. Consult with tax advisors on VAT/SSCL compliance.",
    "labor": "Labor unrest detected. Focus on employee retention and contingency staffing.",
    "import": "Import restrictions possible. Source raw materials locally where possible.",
    "export_market": "Exchange rate volatility is a key factor. Consider hedging instruments for currency risk.",
    "high_investment": "Large capital exposure in current climate requires stepped investment approach. Release funds based on milestones.",
    "domestic_market_low": "Domestic demand may be suppressed. Consider value-segments or essential goods focus.",
    "tourism_rebound": "Tourism rebound detected. Focus marketing on high-yield international segments."
}

def parse_date(date_str):
    try:
        return pd.to_datetime(date_str, infer_datetime_format=True)
    except:
        return datetime.now()

def get_weighted_sentiment(df):
    if df.empty: return 0
    total_score = 0
    total_weight = 0
    for _, row in df.iterrows():
        score = row.get('sentiment_score', 0)
        impact = abs(row.get('impact_score', 0))
        weight = 1 + (impact * 0.1) 
        total_score += score * weight
        total_weight += weight
    return total_score / total_weight if total_weight > 0 else 0

def generate_suggestions(sector, risk_level, threats_df, opportunities_df, context):
    suggestions = []
    
    # 1. Sector & Risk Advice
    if risk_level == "High":
        suggestions.append(SUGGESTION_KB["high_risk"].get(sector, SUGGESTION_KB["high_risk"]["general"]))
    
    # 2. Investment Level Advice
    if context.get('investment') in ['high', 'very_high'] and risk_level != "Low":
        suggestions.append(SUGGESTION_KB["high_investment"])
        
    # 3. Market Focus Advice
    if context.get('target_market') in ['export', 'mixed']:
        suggestions.append(SUGGESTION_KB["export_market"])
    elif context.get('target_market') == 'domestic' and risk_level == "High":
        suggestions.append(SUGGESTION_KB["domestic_market_low"])
        
    # 4. Keyword based advice from threats
    combined_text = " ".join(threats_df['Title'].astype(str).tolist()).lower()
    
    if "inflation" in combined_text or "price" in combined_text:
        suggestions.append(SUGGESTION_KB["inflation"])
    if "tax" in combined_text or "vat" in combined_text:
        suggestions.append(SUGGESTION_KB["tax"])
    if "strike" in combined_text or "protest" in combined_text:
        suggestions.append(SUGGESTION_KB["labor"])
    if "import" in combined_text or "customs" in combined_text:
        suggestions.append(SUGGESTION_KB["import"])
        
    if not suggestions:
        suggestions.append("Monitor competitor pricing and maintain flexible operational plans.")
        
    return list(set(suggestions))

from urllib.parse import urljoin

# --- Gazette Scraper ---
def scrape_recent_gazettes():
    """Scrapes specified gazette sites for recent PDF links."""
    
    urls = [
        "https://www.gazette.lk/government-gazette",
        "http://documents.gov.lk/en/gazette_extra.php" 
    ]
    
    gazettes = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    for url in urls:
        try:
            logger.info(f"Scraping gazettes from: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                links = soup.find_all('a', href=True)
                
                count = 0
                for link in links:
                    href = link['href']
                    text = link.get_text(strip=True)
                    
                    # Construct absolute URL safely
                    full_link = urljoin(url, href)
                    
                    is_relevant = False
                    # Check for PDF or Download keywords
                    if "pdf" in href.lower() or "download" in text.lower():
                        is_relevant = True
                    # Check for gazette viewer links
                    if "view" in href.lower() and "gazette" in href.lower():
                        is_relevant = True
                        
                    if is_relevant and len(text) > 5:
                        gazettes.append({
                            "date": "Latest", 
                            "title": text[:100], 
                            "link": full_link,
                            "source": "Gazette Source"
                        })
                        count += 1
                        if count >= 8: break
                        
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            continue

    return gazettes

# --- Market News Scraper (On-Demand) ---
def scrape_market_highlights():
    """Scrapes latest market news for fresh stock signals."""
    news_items = []
    sources = [
        "https://www.economynext.com/category/markets/",
        "https://www.ft.lk/financial-services"
    ]
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for url in sources:
        try:
            response = requests.get(url, headers=headers, timeout=8)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # EconomyNext specific
                if "economynext" in url:
                    articles = soup.find_all('div', class_='story-grid-single-story')
                    for art in articles[:10]:
                        h3 = art.find('h3', class_='story-title')
                        if h3:
                            a_tag = h3.find('a')
                            if a_tag:
                                title = a_tag.get_text(strip=True)
                                link = a_tag['href']
                                news_items.append({'Title': title, 'Link': link, 'cleaned': title})
                                
                # FT.lk specific
                elif "ft.lk" in url:
                    # FT structure varies, generic approach
                    divs = soup.find_all('div', class_='col-md-12') # Often used for lists
                    for div in divs[:15]:
                        a_tag = div.find('a', class_='t-title') # heuristic
                        if not a_tag:
                             # Try finding any headline
                             h5 = div.find('h5')
                             if h5: a_tag = h5.find('a')
                             
                        if a_tag:
                            title = a_tag.get_text(strip=True)
                            link = a_tag['href']
                            if len(title) > 20: 
                                news_items.append({'Title': title, 'Link': link, 'cleaned': title})
                                
        except Exception as e:
            logger.error(f"Market scrape error for {url}: {e}")
            
    return pd.DataFrame(news_items)

def analyze_company_feasibility(name, sector, scale, investment, target_market, location, description, data_file):
    if not os.path.exists(data_file):
        return {"error": "Data file not found"}
        
    try:
        df = pd.read_csv(data_file)
        
        # --- filtering ---
        
        # 1. Sector Filter
        tags = SECTOR_MAP.get(sector, [])
        if tags:
            pattern = '|'.join(tags)
            relevant_df = df[df['operational_tag'].str.contains(pattern, case=False, na=False)]
            # Also text match
            text_match = df['cleaned'].str.contains(pattern, case=False, na=False)
            relevant_df = pd.concat([relevant_df, df[text_match]]).drop_duplicates()
        else:
            relevant_df = df
            
        # 2. Location Filter (if specific)
        if location != 'general':
            loc_keywords = LOCATION_MAP.get(location, [location])
            loc_pattern = '|'.join(loc_keywords)
            # Filter the subset to prioritize location news, BUT we don't want to exclude 
            # national polices (like tax) just because they don't mention "Kandy".
            # So: we boost relevance if location matches, but we keep "General" Economic/Legal news.
            
            # Simple approach: Create a "Local" subset for specific local risks
            local_df = relevant_df[relevant_df['cleaned'].str.contains(loc_pattern, case=False, na=False)]
            
            # If local news is found, we should emphasize it, but not ignore national context.
            # Let's keep `relevant_df` as the broad sector context, but maybe create a `local_context_df`
            if not local_df.empty:
                # Add local news from outside the sector too (e.g. Flood in Kandy affects a startup regardless of sector)
                all_local_df = df[df['cleaned'].str.contains(loc_pattern, case=False, na=False)]
                relevant_df = pd.concat([relevant_df, all_local_df]).drop_duplicates()

        # 3. Description Keywords
        keywords = [w for w in description.lower().split() if len(w) > 4]
        if keywords:
            desc_pattern = '|'.join(keywords)
            desc_df = df[df['cleaned'].str.contains(desc_pattern, case=False, na=False)]
            relevant_df = pd.concat([relevant_df, desc_df]).drop_duplicates()

        if relevant_df.empty:
            relevant_df = df[df['operational_tag'].str.contains('economic', case=False, na=False)]

        # --- Analysis ---
        
        # Weighted Sentiment
        avg_sentiment = get_weighted_sentiment(relevant_df)
        
        # Risk Calculation
        # Base risk from sentiment
        neg_impact_sum = relevant_df[relevant_df['impact_score'] < 0]['impact_score'].sum()
        normalized_risk = abs(neg_impact_sum) / len(relevant_df) if len(relevant_df) > 0 else 0
        
        # Adjust Risk based on Investment Scale (Higher investment = Higher Sensitivity)
        if investment in ['high', 'very_high']:
            normalized_risk *= 1.2 # 20% penalty for high exposure
            
        # Classification
        if normalized_risk > 3.0: risk_level = "High"
        elif normalized_risk > 1.5: risk_level = "Medium"
        else: risk_level = "Low"

        # Opportunities & Threats
        opportunities_df = relevant_df.nlargest(5, 'sentiment_score')
        threats_df = relevant_df.nsmallest(5, 'sentiment_score')
        
        opportunities = opportunities_df['Title'].tolist()
        threats = threats_df['Title'].tolist()
        
        if not opportunities: opportunities = ["No specific data found."]
        if not threats: threats = ["No specific data found."]

        # Suggestions
        context = {
            "investment": investment,
            "target_market": target_market,
            "scale": scale,
            "location": location
        }
        suggestions = generate_suggestions(sector, risk_level, threats_df, opportunities_df, context)

        # Scrape Gazettes (Live Check)
        gazette_list = scrape_recent_gazettes()
        
        # If scraper found nothing, falling back to internal dataset search for history
        if not gazette_list or len(gazette_list) < 2:
             reg_keywords = ["gazette", "parliament", "bill", "act", "regulation"]
             reg_pattern = '|'.join(reg_keywords)
             # Use original large DF
             reg_df = df[df['cleaned'].str.contains(reg_pattern, case=False, na=False)]
             reg_matches = reg_df[reg_df['cleaned'].str.contains('|'.join(tags) if tags else 'economic', case=False, na=False)]
             for _, row in reg_matches.head(5).iterrows():
                gazette_list.append({
                    "date": row.get('Published', 'Archive'),
                    "title": row.get('Title', 'No Title'),
                    "link": row.get('Link', '#')
                })

        # Advanced AI Report Text
        report_text = f"**Feasibility Assessment for {name}**\n"
        report_text += f"**Scenario**: {scale.title()} scale entity in {location.title()}.\n"
        
        report_text += "### Market Conditions\n"
        if avg_sentiment > 0.1:
            report_text += f"The market sentiment is **Positive ({avg_sentiment:.2f})**. Data indicates favorable momentum. "
        elif avg_sentiment < -0.1:
            report_text += f"The market sentiment is **Negative ({avg_sentiment:.2f})**. The sector faces significant headwinds. "
        else:
            report_text += f"The market sentiment is **Neutral ({avg_sentiment:.2f})**. "
            
        report_text += f"\n\n### Risk Profile: {risk_level}\n"
        if risk_level == "High":
            report_text += "High risk detected. Volatility is significant. Careful capital allocation required. "
        elif risk_level == "Medium":
            report_text += "Moderate risk key. Standard risk mitigation recommended. "
        else:
            report_text += "Low risk environment. Good conditions for entry. "
            
        if location != 'general':
            report_text += f"\n\n### Location Analysis: {location.title()}\n"
            report_text += "Regional news has been factored into this assessment. Check for specific local weather or infrastructure alerts."

        # Chart Data
        pos = len(relevant_df[relevant_df['sentiment_score'] > 0.1])
        neu = len(relevant_df[(relevant_df['sentiment_score'] >= -0.1) & (relevant_df['sentiment_score'] <= 0.1)])
        neg = len(relevant_df[relevant_df['sentiment_score'] < -0.1])
        
        trend_data = relevant_df['sentiment_score'].tail(15).tolist()
        trend_labels = [f"{i+1}" for i in range(len(trend_data))]

        return {
            "sentiment_score": round(avg_sentiment, 2),
            "risk_level": risk_level,
            "report_text": report_text,
            "opportunities": opportunities,
            "threats": threats,
            "suggestions": suggestions,
            "gazette_matches": gazette_list,
            "charts": {
                "sentiment_dist": [pos, neu, neg],
                "trend": {
                    "labels": trend_labels,
                    "data": trend_data
                }
            }
        }
    except Exception as e:
        logger.error(f"Feasibility error: {e}", exc_info=True)
        return {"error": f"Analysis failed: {str(e)}"}


# --- Stock Market Add-on Logic ---

CSE_COMPANIES = {
    "JKH": ["John Keells", "JKH", "Keells"],
    "SAMP": ["Sampath Bank", "Sampath"],
    "COMB": ["Commercial Bank", "ComBank"],
    "HNB": ["Hatton National Bank", "HNB"],
    "DIAL": ["Dialog Axiata", "Dialog"],
    "SLTL": ["Sri Lanka Telecom", "SLT"],
    "HAYL": ["Hayleys"],
    "EXPO": ["Expolanka"],
    "LOLC": ["LOLC"],
    "DIST": ["Distilleries"],
    "CARG": ["Cargills"],
    "LION": ["Lion Brewery"],
    "CHEV": ["Chevron Lubricants"],
    "SUN": ["Sunshine Holdings"],
    "TKYO": ["Tokyo Cement"],
    "RCL": ["Royal Ceramics"],
    "AEL": ["Access Engineering"],
    "MELS": ["Melstacorp"]
}

STOCK_KEYWORDS = ["cse", "colombo stock exchange", "share market", "bourse", "equity", "dividend", "earning", "profit", "loss", "ipo", "rights issue", "stock"]

# Map frontend values to SECTOR_MAP keys
STOCK_SECTOR_MAPPING = {
    "Bank": "economic",
    "Material": "manufacturing",
    "Food Beve": "agriculture", 
    "Cap Goods": "construction",
    "Utility": "energy",
    "Telecom": "technology",
    "Consumer": "tourism" # Approximate
}

def analyze_stock_market(horizon, risk, focus_sector, data_file):
    # Always try to scrape fresh market news first
    fresh_news_df = scrape_market_highlights()
    
    df = pd.DataFrame()
    if os.path.exists(data_file):
        try:
            df = pd.read_csv(data_file)
        except: pass
        
    if not fresh_news_df.empty:
        # Normalize columns if needed
        # We need 'Title', 'Link', 'cleaned'
        # Assign basic sentiment to fresh news if missing (simple keyword check)
        fresh_news_df['sentiment_score'] = 0
        fresh_news_df['operational_tag'] = 'economic'
        fresh_news_df['impact_score'] = 1
        
        # Simple sentiment tagging for fresh news
        for i, row in fresh_news_df.iterrows():
            text = str(row['Title']).lower()
            score = 0
            if any(w in text for w in ['gain', 'up', 'higher', 'green', 'bull', 'profit', 'rise']): score += 0.5
            if any(w in text for w in ['loss', 'down', 'lower', 'red', 'bear', 'crash', 'drop']): score -= 0.5
            fresh_news_df.at[i, 'sentiment_score'] = score

        df = pd.concat([fresh_news_df, df], ignore_index=True)

    if df.empty:
        return {"error": "No market data available (scrapers failed and local data missing)."}
        
    try:
        # 1. Filter Overall Market News
        # Pattern matching for ANY stock keywords
        stock_pattern = '|'.join(STOCK_KEYWORDS)
        # Use na=False to handle potential NaNs
        market_news = df[df['cleaned'].str.contains(stock_pattern, case=False, na=False)]
        
        # If market_news is too sparse, fallback to all fresh news
        if len(market_news) < 5 and not fresh_news_df.empty:
             market_news = pd.concat([market_news, fresh_news_df]).drop_duplicates()

        market_sentiment = get_weighted_sentiment(market_news)
        market_sentiment_str = f"{market_sentiment:.2f} (Neutral)"
        if market_sentiment > 0.2: market_sentiment_str = f"{market_sentiment:.2f} (Bullish)"
        elif market_sentiment < -0.2: market_sentiment_str = f"{market_sentiment:.2f} (Bearish)"
        
        # 2. Analyze Specific Company Mentions
        stock_picks = []
        for ticker, aliases in CSE_COMPANIES.items():
            pattern = '|'.join(aliases)
            # Find news mentioning this company
            company_df = df[df['cleaned'].str.contains(pattern, case=False, na=False)]
            
            if not company_df.empty:
                # Top headline
                best_row = company_df.iloc[0]
                headline = best_row['Title']
                score = best_row.get('sentiment_score', 0)
                
                # Signal Logic
                signal = "Hold"
                if score > 0.1: signal = "Buy"
                elif score < -0.1: signal = "Sell"
                
                if risk == "conservative" and signal == "Buy" and score < 0.4:
                    signal = "Hold"
                
                stock_picks.append({
                    "name": f"{ticker} ({aliases[0]})",
                    "sentiment": round(score, 2),
                    "headline": headline,
                    "signal": signal,
                    "ticker": ticker
                })
        
        stock_picks.sort(key=lambda x: x['sentiment'], reverse=True)
        
        # 3. Sector Performance
        sector_perf = []
        top_sector_name = "N/A"
        top_sector_score = -99
        
        mapped_focus = STOCK_SECTOR_MAPPING.get(focus_sector, 'all')
        if focus_sector == 'all':
            target_sectors = SECTOR_MAP.keys()
        else:
             target_sectors = [mapped_focus] if mapped_focus in SECTOR_MAP else []

        for sec in target_sectors:
            tags = SECTOR_MAP.get(sec, [])
            if tags:
                pat = '|'.join(tags)
                sec_df = df[df['operational_tag'].str.contains(pat, case=False, na=False)]
                score = get_weighted_sentiment(sec_df)
                sector_perf.append({"sector": sec.title(), "score": round(score, 2)})
                
                if score > top_sector_score:
                    top_sector_score = score
                    top_sector_name = sec.title()
        
        # 4. Strategy Report
        action = "Accumulate" if market_sentiment > 0.1 else ("Stay Cash" if market_sentiment < -0.2 else "Hold")
        
        report = f"**Market Outlook ({horizon.title()} Term)**\n"
        report += f"The CSE shows a **{market_sentiment_str}** sentiment trend. "
        
        if market_sentiment > 0.1:
            report += "News flow suggests optimism. "
        elif market_sentiment < -0.1:
            report += "Negative sentiment prevails. "
            
        report += f"\n\n**Top Performing Sector**: {top_sector_name}\n"
        
        if risk == "conservative":
            report += "\n\n**Risk Note**: Given your conservative profile, focus on blue-chip stocks with high dividends (e.g. Banking, Telecom)."
        elif risk == "aggressive":
             report += "\n\n**Risk Note**: Aggressive strategy suggests looking for undervalued 'turnaround' plays."

        # 5. Events
        events = []
        event_keywords = {"dividend": "Dividend Declared", "rights issue": "Rights Issue", "earning": "Earnings Report", "agm": "AGM", "ipo": "IPO"}
        
        # Search primarily in fresh/market news
        search_pool = market_news if not market_news.empty else df.head(100)
        
        for _, row in search_pool.iterrows():
            txt = str(row.get('cleaned', '')).lower()
            for k, v in event_keywords.items():
                if k in txt:
                    # Try to extract Likely Company? or just list headline
                    events.append({"company": "News", "type": f"{v}: {str(row.get('Title',''))[:60]}..."})
                    break
            if len(events) >= 5: break

        return {
            "market_sentiment": market_sentiment,
            "market_sentiment_str": market_sentiment_str,
            "top_sector": top_sector_name,
            "recommended_action": action,
            "strategy_report": report,
            "stock_picks": stock_picks, 
            "sector_performance": sector_perf,
            "events": events
        }
        
    except Exception as e:
        logger.error(f"Stock analysis error: {e}", exc_info=True)
        return {"error": f"Analysis Error: {str(e)}"}
