import os
import smtplib
import requests
import json
from email.message import EmailMessage

# Load once from secrets
with open("secrets.json", "r") as f:
    secrets = json.load(f)
EMAIL = secrets.get("email", {})
TELEGRAM = secrets.get("telegram", {})

def send_email_alert(subject, body, attachments=None):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL["from_email"]
    msg["To"] = EMAIL["to_email"]
    msg.set_content(body)

    if attachments:
        for path in attachments:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    data = f.read()
                    msg.add_attachment(data, maintype="image", subtype="png", filename=os.path.basename(path))

    try:
        with smtplib.SMTP_SSL(EMAIL["smtp_server"], EMAIL["smtp_port"]) as smtp:
            smtp.login(EMAIL["from_email"], EMAIL["password"])
            smtp.send_message(msg)
        print("✅ Email alert sent.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


def send_telegram_alert(message, image_path=None):
    try:
        msg_url = f"https://api.telegram.org/bot{TELEGRAM['bot_token']}/sendMessage"
        requests.post(msg_url, data={"chat_id": TELEGRAM["chat_id"], "text": message})

        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM['bot_token']}/sendPhoto",
                    data={"chat_id": TELEGRAM["chat_id"]},
                    files={"photo": f}
                )

        print("✅ Telegram alert sent.")
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")
