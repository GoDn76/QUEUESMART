import os
from pathlib import Path
from time import sleep

from dotenv import load_dotenv
from twilio.rest import Client


# --------------------------------------------------------
# Load .env from BUILD_B/.env
# --------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


# --------------------------------------------------------
# Environment variables
# --------------------------------------------------------
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

# Twilio Sandbox WhatsApp number
WHATSAPP_FROM = os.getenv(
    "TWILIO_WHATSAPP_FROM",
    "whatsapp:+14155238886"
)

# Your phone number with country code
MY_PHONE = os.getenv("MY_PHONE")


# --------------------------------------------------------
# Validate configuration
# --------------------------------------------------------
missing = []

if not ACCOUNT_SID:
    missing.append("TWILIO_ACCOUNT_SID")

if not AUTH_TOKEN:
    missing.append("TWILIO_AUTH_TOKEN")

if not MY_PHONE:
    missing.append("MY_PHONE")

if missing:
    print("\nMissing environment variables:")
    for item in missing:
        print(f" - {item}")
    exit(1)


# --------------------------------------------------------
# Create Twilio client
# --------------------------------------------------------
client = Client(ACCOUNT_SID, AUTH_TOKEN)


# --------------------------------------------------------
# Send WhatsApp message
# --------------------------------------------------------
try:
    print("\nSending WhatsApp message...\n")

    message = client.messages.create(
        from_=WHATSAPP_FROM,
        to=f"whatsapp:{MY_PHONE}",
        body="""
QueueMind Test

You are only 2 positions away from being served.

Please be ready.
"""
    )

    print("Initial Status :", message.status)
    print("SID            :", message.sid)

    # ----------------------------------------------------
    # Wait a few seconds and fetch latest status
    # ----------------------------------------------------
    sleep(5)

    updated_message = client.messages(message.sid).fetch()

    print("\nUpdated Status :", updated_message.status)
    print("Error Code     :", updated_message.error_code)
    print("Error Message  :", updated_message.error_message)

except Exception as e:
    print("\nFailed to send WhatsApp message.")
    print("Reason:", str(e))