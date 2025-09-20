# notifier.py
import os, json, smtplib, ssl
from email.mime.text import MIMEText
from urllib import request

SLACK_URL = os.getenv("SLACK_WEBHOOK_URL")
TO = os.getenv("ALERT_EMAIL_TO")
FROM = os.getenv("ALERT_EMAIL_FROM")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USERNAME")
SMTP_PASS = os.getenv("SMTP_PASSWORD")

def send_slack(text: str) -> bool:
    if not SLACK_URL: return False
    data = json.dumps({"text": text}).encode("utf-8")
    req = request.Request(SLACK_URL, data=data, headers={"Content-Type":"application/json"})
    try:
        with request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False

def send_email(subject: str, body: str) -> bool:
    if not (TO and FROM and SMTP_USER and SMTP_PASS): return False
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = FROM
    msg["To"] = TO
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as s:
            s.starttls(context=ctx)
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(FROM, [TO], msg.as_string())
        return True
    except Exception:
        return False

def notify(subject: str, body: str):
    ok_s = send_slack(f"*{subject}*\n{body}")
    ok_e = send_email(subject, body)
    return ok_s or ok_e

# notifier.py (add at bottom)
from win10toast import ToastNotifier

toaster = ToastNotifier()

def send_toast(title: str, body: str) -> bool:
    try:
        toaster.show_toast(title, body, duration=8, threaded=True)
        return True
    except Exception:
        return False

def notify(subject: str, body: str):
    ok_s = send_slack(f"*{subject}*\n{body}")
    ok_e = send_email(subject, body)
    ok_t = send_toast(subject, body)
    return ok_s or ok_e or ok_t
