import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Email Configuration
RECIPIENT_EMAIL = "nima.mashayekhi@gmail.com"

# .env must include:
# SENDER_EMAIL=your_email@gmail.com
# SENDER_PASSWORD=your_app_password
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

# SMTP Configuration (Gmail)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def read_newsletter_html(filepath: str = "newsletter.html") -> str:
    """Read the HTML newsletter file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            html_content = f.read()
        print(f"Loaded newsletter from {filepath}")
        return html_content
    except FileNotFoundError:
        print(f"Error: {filepath} not found. Please run newsletter_generator.py first.")
        return None


def extract_date_from_html(html_content: str) -> str:
    """Extract the date from the HTML newsletter file."""

    # Look for <div class="date">Date</div>
    match = re.search(r'<div class="date">([^<]+)</div>', html_content)
    if match:
        return match.group(1).strip()

    # Fallback to <title>Daily News Digest - Date</title>
    match = re.search(r'<title>Daily News Digest - ([^<]+)</title>', html_content)
    if match:
        return match.group(1).strip()

    return None


def read_newsletter_text(filepath: str = "newsletter.txt") -> str:
    """Read the plain text version of the newsletter."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Please view this email in an HTML-friendly email client."


def send_newsletter_email(
    recipient: str,
    html_content: str,
    text_content: str = None,
    subject: str = None
) -> bool:
    """Send the newsletter via email."""

    # Validate credentials
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("Error: Email credentials not found in .env.")
        print("Ensure SENDER_EMAIL and SENDER_PASSWORD are set.")
        print("Note: Use a Gmail App Password, not your regular password.")
        return False

    # Build subject line
    if not subject:
        extracted_date = extract_date_from_html(html_content)
        subject = f"Newsletter {extracted_date}" if extracted_date else "Newsletter"

    # Create email container
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient

    # Fallback plain text
    if not text_content:
        text_content = read_newsletter_text()

    # Attach plain and HTML content
    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    print(f"Sending newsletter to: {recipient}")
    print(f"From: {SENDER_EMAIL}")
    print(f"Subject: {subject}")

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            print("Connecting to SMTP server...")
            server.starttls()
            print("Authenticating...")
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            print("Sending email...")
            server.sendmail(SENDER_EMAIL, recipient, msg.as_string())

        print("Email sent successfully.")
        return True

    except smtplib.SMTPAuthenticationError:
        print("Authentication failed. Check your Gmail App Password.")
        return False

    except smtplib.SMTPException as e:
        print(f"SMTP error: {e}")
        return False

    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def main():
    print("Loading newsletter...")
    html_content = read_newsletter_html("newsletter.html")

    if not html_content:
        print("No newsletter found. Generate one by running newsletter_generator.py.")
        return

    text_content = read_newsletter_text("newsletter.txt")

    print("Sending email...")
    success = send_newsletter_email(
        recipient=RECIPIENT_EMAIL,
        html_content=html_content,
        text_content=text_content,
    )

    if success:
        print(f"Newsletter sent successfully to {RECIPIENT_EMAIL}")
    else:
        print("Failed to send newsletter. Review the error details above.")


if __name__ == "__main__":
    main()
