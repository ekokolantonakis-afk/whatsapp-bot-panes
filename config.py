import os

# Twilio Configuration - Using environment variables
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# WooCommerce - panes.gr
PANES_URL = "https://panes.gr"
PANES_CONSUMER_KEY = os.environ.get("PANES_CONSUMER_KEY", "")
PANES_CONSUMER_SECRET = os.environ.get("PANES_CONSUMER_SECRET", "")

# Admin Phone (for notifications)
ADMIN_PHONE = "whatsapp:+306942508739"

# Development Mode
DEVELOPMENT = os.environ.get("DEVELOPMENT", "False") == "True"
