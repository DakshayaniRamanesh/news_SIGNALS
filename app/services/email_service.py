import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
import pandas as pd
from datetime import datetime
from flask import render_template, current_app
from xhtml2pdf import pisa
from io import BytesIO

# Configuration - Replace with Environment Variables in Production
# Configuration - Load from Environment Variables
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", SMTP_USER)
APP_NAME = os.environ.get("APP_NAME", "SignalMon")

# Resolve paths relative to this file
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_FILE = os.path.join(BASE_DIR, "data", "final_data.csv")
SUBSCRIBERS_FILE = os.path.join(BASE_DIR, "subscribers.txt")

def generate_pdf_report():
    """Generates the PDF report and returns the bytes."""
    if not os.path.exists(DATA_FILE):
        return None

    try:
        df = pd.read_csv(DATA_FILE)
        
        stats = {
            "high_risk": len(df[df['impact_level'] == 'High Risk']),
            "opportunity": len(df[df['impact_level'] == 'Opportunity']),
            "major_events": len(df[df['event_flag'] == 'Major Event']),
        }
        
        major_events = df[df['event_flag'] == 'Major Event'].to_dict(orient='records')
        high_risk_items = df[df['impact_level'] == 'High Risk'].to_dict(orient='records')
        opportunity_items = df[df['impact_level'] == 'Opportunity'].to_dict(orient='records')
        
        date_str = datetime.now().strftime("%B %d, %Y %I:%M %p")
        
        # We need an app context to render the template if this runs outside a request
        # But if called from scheduler within app context or we push one, it's fine.
        # If running from scheduler, we might need manual context or reuse the app's context.
        # For simplicity, we assume this is called within an app context or we create one.
        
        html = render_template(
            'pdf_report.html',
            stats=stats,
            major_events=major_events,
            high_risk_items=high_risk_items,
            opportunity_items=opportunity_items,
            date=date_str
        )
        
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf_buffer)
        
        if pisa_status.err:
            print("PDF generation error")
            return None
            
        pdf_buffer.seek(0)
        return pdf_buffer.read()
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None

def send_email_with_pdf(recipient_email, pdf_bytes, high_risk_count):
    """Sends the email with PDF attachment."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"Mocking email send to {recipient_email} - SMTP credentials not set. Set SMTP_USER and SMTP_PASSWORD env vars.")
        return False

    msg = MIMEMultipart()
    msg['Subject'] = f"Daily {APP_NAME} Report - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email

    body_text = f"""
    Hello,

    Here is your daily Signal Report.
    
    Snapshot:
    - High Risk Items: {high_risk_count}
    
    Please find the full detailed report attached.
    
    Regards,
    {APP_NAME} Team
    """
    
    msg.attach(MIMEText(body_text, 'plain'))

    if pdf_bytes:
        part = MIMEApplication(pdf_bytes, Name=f"Signal_Report_{datetime.now().strftime('%Y%m%d')}.pdf")
        part['Content-Disposition'] = f'attachment; filename="Signal_Report_{datetime.now().strftime('%Y%m%d')}.pdf"'
        msg.attach(part)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
            print(f"Email sent to {recipient_email}")
            return True
    except Exception as e:
        print(f"Failed to send email to {recipient_email}: {e}")
        return False

def send_confirmation_email(recipient_email):
    """Sends a subscription confirmation email."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"Mocking confirmation email to {recipient_email} - SMTP credentials not set.")
        return False

    msg = MIMEMultipart()
    msg['Subject'] = f"Welcome to {APP_NAME} - Subscription Confirmed"
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg.add_header('Content-Type', 'multipart/alternative')

    # Plain text version
    body_text = f"""
    Hello,

    Thank you for subscribing to {APP_NAME}!
    
    You will now receive:
    - Instant alerts for High Risk events
    - Daily PDF {APP_NAME} Reports
    
    Stay informed and safe.
    
    Regards,
    {APP_NAME} Team
    """
    
    msg.attach(MIMEText(body_text, 'plain'))
    
    # HTML version with animation
    try:
        html_content = render_template('email/welcome.html', app_name=APP_NAME, year=datetime.now().year)
        msg.attach(MIMEText(html_content, 'html'))
    except Exception as e:
        print(f"Error rendering HTML email: {e}")


    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
            print(f"Confirmation email sent to {recipient_email}")
            return True
    except Exception as e:
        print(f"Failed to send confirmation email to {recipient_email}: {e}")
        return False

def send_daily_reports(app_instance):
    """Orchestrate sending reports to all subscribers. 
    Accepts app_instance to push context for render_template."""
    
    print("Starting daily report generation...")
    
    # Push context for render_template to work
    with app_instance.app_context():
        pdf_bytes = generate_pdf_report()
        
        if not pdf_bytes:
            print("Failed to generate PDF, aborting report send.")
            return

        # Get stats for the body
        try:
            df = pd.read_csv(DATA_FILE)
            high_risk_count = len(df[df['impact_level'] == 'High Risk'])
        except:
            high_risk_count = 0

        # Read subscribers
        if not os.path.exists(SUBSCRIBERS_FILE):
            print("No subscribers file found.")
            return

        with open(SUBSCRIBERS_FILE, 'r') as f:
            lines = f.readlines()
            
        for line in lines:
            try:
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    email = parts[1]
                    send_report = parts[3] == 'True' # Check 'report' flag
                    
                    if send_report:
                        send_email_with_pdf(email, pdf_bytes, high_risk_count)
            except Exception as e:
                print(f"Error processing subscriber line '{line.strip()}': {e}")

def send_immediate_report(email):
    """Sends the current report immediately to a specific email."""
    print(f"Sending immediate report to {email}...")
    
    pdf_bytes = generate_pdf_report()
    
    if not pdf_bytes:
        print("Failed to generate PDF for immediate report.")
        return False

    # Get stats for the body
    try:
        df = pd.read_csv(DATA_FILE)
        high_risk_count = len(df[df['impact_level'] == 'High Risk'])
    except:
        high_risk_count = 0
        
    return send_email_with_pdf(email, pdf_bytes, high_risk_count)
