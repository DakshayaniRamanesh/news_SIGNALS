from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash, make_response, send_from_directory
from datetime import datetime
from io import BytesIO
from xhtml2pdf import pisa
import pandas as pd
import os
import time
from app.scheduler import refresh_now, update_interval, get_next_run_time, get_interval
from app.services.data_processor import get_current_model_info, switch_model
from app.services.historical_scraper import scrape_historical_data
from app.services import market_data

main = Blueprint('main', __name__)

# Resolve paths relative to this file
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_FILE = os.path.join(BASE_DIR, "data", "final_data.csv")
SUBSCRIBERS_FILE = os.path.join(BASE_DIR, "subscribers.txt")

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/feed')
def live_feed():
    return render_template('feed.html')

@main.route('/clusters')
def clusters():
    return render_template('clusters.html')

@main.route('/insights')
def insights():
    return render_template('insights.html')

@main.route('/map')
def location_map():
    return render_template('map.html')

@main.route('/data')
def raw_data():
    return render_template('data.html')

@main.route('/settings')
def settings():
    return render_template('settings.html')

@main.route('/api/data')
def get_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            # Replace NaN with None (null in JSON)
            df = df.where(pd.notnull(df), None)
            return jsonify(df.to_dict(orient='records'))
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify([]), 200

@main.route('/api/history')
def get_history():
    history_path = os.path.join(BASE_DIR, "data", "news_history.json")
    if os.path.exists(history_path):
        try:
            # Serve the static JSON file directly effectively
            with open(history_path, 'r') as f:
                import json
                data = json.load(f)
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        # If no history exists yet, fallback to current data or empty
        return jsonify([]), 200

@main.route('/api/scrape_history', methods=['POST'])
def scrape_history_endpoint():
    print("DEBUG: /api/scrape_history hit")
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON or Content-Type"}), 400
    start = data.get('start')
    end = data.get('end')
    
    if not start or not end:
        return jsonify({"error": "Missing start or end date"}), 400
        
    try:
        results = scrape_historical_data(start, end)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main.route('/api/stats')
def get_stats():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            stats = {
                "total_articles": len(df),
                "high_risk": len(df[df['impact_level'] == 'High Risk']),
                "opportunity": len(df[df['impact_level'] == 'Opportunity']),
                "major_events": len(df[df['event_flag'] == 'Major Event']),
                "last_updated": time.ctime(os.path.getmtime(DATA_FILE))
            }
            return jsonify(stats)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"total_articles": 0, "high_risk": 0, "opportunity": 0, "major_events": 0, "last_updated": "Never"})

@main.route('/api/refresh', methods=['POST'])
def refresh_data():
    if refresh_now():
        return jsonify({"status": "success", "message": "Refresh triggered"}), 200
    else:
        return jsonify({"status": "error", "message": "Scheduler not running"}), 500

@main.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    if request.method == 'POST':
        data = request.get_json()
        interval = data.get('interval')
        if interval and isinstance(interval, int) and interval >= 5:
            if update_interval(interval):
                return jsonify({"status": "success", "next_run": get_next_run_time()}), 200
            else:
                return jsonify({"status": "error", "message": "Failed to update scheduler"}), 500
        return jsonify({"status": "error", "message": "Invalid interval"}), 400
    else:
        return jsonify({
            "interval": get_interval(),
            "next_run": get_next_run_time()
        })

@main.route('/api/model', methods=['GET', 'POST'])
def api_model():
    if request.method == 'POST':
        data = request.get_json()
        model_name = data.get('model_name')
        if model_name:
            success, msg = switch_model(model_name)
            if success:
                return jsonify({"status": "success", "message": msg}), 200
            else:
                return jsonify({"status": "error", "message": msg}), 400
        return jsonify({"status": "error", "message": "Model name required"}), 400
    else:
        return jsonify(get_current_model_info())

@main.route('/api/market/usd-lkr')
def get_usd_lkr():
    """Get USD/LKR exchange rate with historical data"""
    try:
        data = market_data.get_usd_lkr_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/api/market/gold')
def get_gold():
    """Get gold price per gram with historical data"""
    try:
        data = market_data.get_gold_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/api/market/fuel')
def get_fuel():
    """Get fuel prices with historical data"""
    try:
        data = market_data.get_fuel_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/api/market/inflation')
def get_inflation():
    """Get inflation rate with historical data"""
    try:
        data = market_data.get_inflation_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/api/market/update', methods=['POST'])
def update_market():
    """Manually trigger market data update"""
    try:
        market_data.update_market_data()
        return jsonify({"status": "success", "message": "Market data updated"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@main.route('/api/proxy-settings', methods=['GET', 'POST'])
def proxy_settings():
    """Get or update proxy settings"""
    from app.services.proxy_manager import proxy_manager
    
    if request.method == 'GET':
        return jsonify(proxy_manager.config)
    
    elif request.method == 'POST':
        try:
            data = request.json
            # Update configuration
            proxy_manager.config.update(data)
            proxy_manager.save_config(proxy_manager.config)
            
            # If enabled status changed, log it
            if 'enabled' in data:
                status = "enabled" if data['enabled'] else "disabled"
                proxy_manager.log_rotation(f"Proxy rotation {status} via settings")
            
            return jsonify({"status": "success", "message": "Proxy settings updated"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

@main.route('/api/proxy-status')
def proxy_status():
    """Get current proxy status and logs"""
    from app.services.proxy_manager import proxy_manager
    
    try:
        status = proxy_manager.get_status()
        logs = proxy_manager.get_recent_logs(50)
        
        return jsonify({
            "status": status,
            "logs": logs
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/api/location-data')
def get_location_data():
    """Get location frequency data for heatmap"""
    try:
        from app.services.nlp_service import get_location_summary
        data = get_location_summary()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/api/heatmap-data')
def get_heatmap_data():
    """Get heatmap points data [lat, lon, intensity]"""
    try:
        from app.services.nlp_service import get_heatmap_data
        points = get_heatmap_data()
        return jsonify({"points": points})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main.route('/api/location-update', methods=['POST'])
def update_location_data():
    """Manually trigger location data update"""
    try:
        from app.services.nlp_service import get_location_summary
        data = get_location_summary()
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@main.route('/api/export-pdf')
def export_pdf():
    """Generate and return a PDF report"""
    from app.services.email_service import generate_pdf_report
    
    pdf_bytes = generate_pdf_report()
    
    if not pdf_bytes:
         return "Error generating PDF or no data", 500
         
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=signal_report_{int(time.time())}.pdf'
    
    return response

@main.route('/api/subscribers')
def get_subscribers():
    """Get subscriber count"""
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE, 'r') as f:
                lines = [line.strip() for line in f if line.strip()]
            return jsonify({"count": len(lines)})
        except Exception:
            return jsonify({"count": 0})
    else:
        return jsonify({"count": 0})

@main.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    if request.method == 'POST':
        email = request.form.get('email')
        notifications = request.form.get('notifications') == 'on'
        report = request.form.get('report') == 'on'
        
        if email:
            try:
                # Check for duplicates
                exists = False
                if os.path.exists(SUBSCRIBERS_FILE):
                    with open(SUBSCRIBERS_FILE, 'r') as f:
                        for line in f:
                            if email in line:
                                exists = True
                                break
                
                if exists:
                    return redirect(url_for('main.subscribe', status='duplicate'))

                # Simple storage for demo
                with open(SUBSCRIBERS_FILE, 'a') as f:
                    f.write(f"{datetime.now()},{email},{notifications},{report}\n")

                # Send confirmation email
                from app.services.email_service import send_confirmation_email, send_immediate_report
                send_confirmation_email(email)

                # If user opted for reports, send the latest one immediately
                if report:
                    send_immediate_report(email)

                # Redirect with success status to show confirmation screen
                return redirect(url_for('main.subscribe', status='success'))
            except Exception as e:
                flash(f"Error subscribing: {e}", "error")
                return redirect(url_for('main.subscribe'))
        
    return render_template('subscribe.html')

@main.route('/api/admin/send-report', methods=['POST'])
def trigger_daily_report():
    """Manually trigger the daily report blast to all subscribers."""
    try:
        from app.services.email_service import send_daily_reports
        from flask import current_app
        send_daily_reports(current_app._get_current_object())
        return jsonify({"status": "success", "message": "Daily reports triggered"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
