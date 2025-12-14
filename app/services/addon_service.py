
import pandas as pd
import os
import numpy as np
from datetime import datetime, timedelta
import re

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

        # Gazette Search
        reg_keywords = ["gazette", "parliament", "bill", "act", "regulation", "ministry", "policy", "circular"]
        reg_pattern = '|'.join(reg_keywords)
        reg_df = df[df['cleaned'].str.contains(reg_pattern, case=False, na=False)]
        
        # Filter for Sector OR Location relevant gazettes
        reg_matches = reg_df[reg_df['cleaned'].str.contains('|'.join(tags) if tags else 'economic', case=False, na=False)]

        gazette_list = []
        for _, row in reg_matches.head(10).iterrows():
            gazette_list.append({
                "date": row.get('Published', 'Unknown Date'),
                "title": row.get('Title', 'No Title'),
                "link": row.get('Link', '#')
            })

        # Advanced AI Report Text
        report_text = f"**Feasibility Assessment for {name}**\n"
        report_text += f"**Scenario**: {scale.title()} scale entity in {location.title()}, focused on {target_market} market.\n"
        report_text += f"**Sector**: {sector.title()} | Data Points: {len(relevant_df)}\n\n"
        
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
        return {"error": str(e)}
