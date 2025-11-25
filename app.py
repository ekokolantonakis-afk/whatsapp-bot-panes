import os
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from woocommerce import API
import config
import logging
import re
import json
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# 📧 EMAIL CONFIGURATION
# ============================================
EMAIL_CONFIG = {
    'smtp_server': getattr(config, 'SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': getattr(config, 'SMTP_PORT', 587),
    'smtp_user': getattr(config, 'SMTP_USER', ''),
    'smtp_password': getattr(config, 'SMTP_PASSWORD', ''),
    'from_email': getattr(config, 'FROM_EMAIL', 'noreply@panes.gr'),
    'store_emails': {
        'chalandri': 'halandri@panes.gr',
        'support': 'support@panes.gr'
    }
}

def send_email(to_emails, subject, body_html, body_text=None):
    """Send email notification"""
    try:
        if not EMAIL_CONFIG['smtp_user'] or not EMAIL_CONFIG['smtp_password']:
            logger.warning("Email not configured - skipping send")
            return False
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_CONFIG['from_email']
        msg['To'] = ', '.join(to_emails) if isinstance(to_emails, list) else to_emails
        
        if body_text:
            msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
        msg.attach(MIMEText(body_html, 'html', 'utf-8'))
        
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['smtp_user'], EMAIL_CONFIG['smtp_password'])
            server.send_message(msg)
        
        logger.info(f"📧 Email sent to: {to_emails}")
        return True
    except Exception as e:
        logger.error(f"❌ Email error: {e}")
        return False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Twilio client
twilio_client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

# Initialize WooCommerce API
wcapi = API(
    url=config.PANES_URL,
    consumer_key=config.PANES_CONSUMER_KEY,
    consumer_secret=config.PANES_CONSUMER_SECRET,
    version="wc/v3",
    timeout=30
)

# Initialize Claude AI
claude_client = None
try:
    from anthropic import Anthropic
    if hasattr(config, 'ANTHROPIC_API_KEY') and config.ANTHROPIC_API_KEY:
        claude_client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        logger.info("✅ Claude AI initialized successfully!")
except Exception as e:
    logger.warning(f"⚠️ Claude AI not available: {e}")

# ============================================
# 🏪 ALL CARESTORES LOCATIONS
# ============================================
STORES = {
    'chalandri': {
        'id': 'chalandri',
        'name': 'CARESTORES Χαλάνδρι',
        'short_name': 'Χαλάνδρι',
        'address': 'Λ. Πεντέλης 58, Χαλάνδρι 15233',
        'phone': '210 680 0549',
        'hours': {'weekdays': '09:00 - 21:00', 'saturday': '09:00 - 15:00', 'sunday': 'Κλειστά'},
        'parking': '10 θέσεις parking',
        'lat': '38.0217',
        'lng': '23.8003',
        'google_maps': 'https://maps.app.goo.gl/H8ofyNhr1vuEUJeF7',
        'waze': 'https://waze.com/ul?ll=38.0217,23.8003&navigate=yes',
        'drive_through': True,
        'active': True
    },
    'ampelokipoi': {
        'id': 'ampelokipoi',
        'name': 'CARESTORES Αμπελόκηποι',
        'short_name': 'Αμπελόκηποι',
        'address': 'Αμπελόκηποι, Αθήνα',
        'phone': '',
        'hours': {'weekdays': '09:00 - 21:00', 'saturday': '09:00 - 15:00', 'sunday': 'Κλειστά'},
        'parking': 'Διαθέσιμο parking',
        'lat': '37.9878',
        'lng': '23.7650',
        'google_maps': 'https://www.google.com/maps/search/?api=1&query=CARESTORES+Αμπελόκηποι',
        'waze': '',
        'drive_through': False,
        'active': True
    },
    'gerakas': {
        'id': 'gerakas',
        'name': 'CARESTORES Γέρακας',
        'short_name': 'Γέρακας',
        'address': 'Γέρακας, Αττική',
        'phone': '',
        'hours': {'weekdays': '09:00 - 21:00', 'saturday': '09:00 - 15:00', 'sunday': 'Κλειστά'},
        'parking': 'Διαθέσιμο parking',
        'lat': '38.0167',
        'lng': '23.8500',
        'google_maps': 'https://www.google.com/maps/search/?api=1&query=CARESTORES+Γέρακας',
        'waze': '',
        'drive_through': False,
        'active': True
    },
    'cholargos': {
        'id': 'cholargos',
        'name': 'CARESTORES Χολαργός',
        'short_name': 'Χολαργός',
        'address': 'Χολαργός, Αττική',
        'phone': '',
        'hours': {'weekdays': '09:00 - 21:00', 'saturday': '09:00 - 15:00', 'sunday': 'Κλειστά'},
        'parking': 'Διαθέσιμο parking',
        'lat': '38.0044',
        'lng': '23.7992',
        'google_maps': 'https://www.google.com/maps/search/?api=1&query=CARESTORES+Χολαργός',
        'waze': '',
        'drive_through': False,
        'active': True
    },
    'kalymnos': {
        'id': 'kalymnos',
        'name': 'CARESTORES Κάλυμνος',
        'short_name': 'Κάλυμνος',
        'address': 'Κάλυμνος, Δωδεκάνησα',
        'phone': '',
        'hours': {'weekdays': '09:00 - 21:00', 'saturday': '09:00 - 15:00', 'sunday': 'Κλειστά'},
        'parking': 'Διαθέσιμο parking',
        'lat': '36.9500',
        'lng': '26.9833',
        'google_maps': 'https://www.google.com/maps/search/?api=1&query=CARESTORES+Κάλυμνος',
        'waze': '',
        'drive_through': False,
        'active': True
    },
    'lamia': {
        'id': 'lamia',
        'name': 'CARESTORES Λαμία',
        'short_name': 'Λαμία',
        'address': 'Λαμία, Φθιώτιδα',
        'phone': '',
        'hours': {'weekdays': '09:00 - 21:00', 'saturday': '09:00 - 15:00', 'sunday': 'Κλειστά'},
        'parking': 'Διαθέσιμο parking',
        'lat': '38.8991',
        'lng': '22.4342',
        'google_maps': 'https://www.google.com/maps/search/?api=1&query=CARESTORES+Λαμία',
        'waze': '',
        'drive_through': False,
        'active': True
    }
}

# Default store
DEFAULT_STORE = 'chalandri'

# ============================================
# 🏢 FRANCHISE INFORMATION
# ============================================
FRANCHISE_INFO = {
    'website': 'https://carestores.gr/franchise',
    'youtube': 'https://youtu.be/eA5Lk0t7P1o?si=UJ2nG2RU0hME7M_z',
    'email': 'franchise@carestores.gr',
    'benefits': [
        'Αποκλειστική περιοχή',
        'Πλήρης εκπαίδευση',
        'Marketing υποστήριξη',
        'Χαμηλό κόστος εκκίνησης',
        'Δοκιμασμένο επιχειρηματικό μοντέλο'
    ]
}

# ============================================
# 🏭 WHOLESALE / B2B INFORMATION
# ============================================
WHOLESALE_INFO = {
    'website': 'https://easycaremarket.gr',
    'b2b_portal': 'https://b2b.easycaremarket.gr',
    'discount': '20%',
    'min_order_free_shipping': 350,  # Minimum order for free shipping
    'shipping_cost': 15,  # Shipping cost if below minimum
    'target_customers': [
        {'type': 'daycare', 'name': '🏫 Παιδικός Σταθμός'},
        {'type': 'nursing_home', 'name': '🏥 Γηροκομείο'},
        {'type': 'church', 'name': '⛪ Εκκλησιαστικό Ίδρυμα'},
        {'type': 'elderly_care', 'name': '👴 Κέντρο Φροντίδας Ηλικιωμένων'},
        {'type': 'kapi', 'name': '🏛️ ΚΑΠΗ'},
        {'type': 'hotel', 'name': '🏨 Ξενοδοχείο'},
        {'type': 'other', 'name': '🏢 Άλλη Επιχείρηση'}
    ],
    'benefits': [
        'Έκπτωση -20%',
        'Τιμολόγιο',
        'Παράδοση στις αποθήκες σας',
        'ΔΩΡΕΑΝ μεταφορικά (παραγγελίες 350€+)',
        'Πίστωση'
    ],
    'contact_phone': '210 680 0549'
}

# ============================================
# ⚠️ DISCOUNT EXCLUSIONS
# ============================================
NO_DISCOUNT_KEYWORDS = [
    'humana', 'βρεφικό γάλα', 'βρεφικο γαλα', 'baby formula',
    'nan ', 'nestle nan', 'γάλα 1', 'γάλα 2', 'γάλα 3',
    'βρεφική διατροφή', 'βρεφικη διατροφη',
    '1ης ηλικίας', '2ης ηλικίας', '3ης ηλικίας',
    'solgar', 'βιταμίνες solgar'
]

NO_DISCOUNT_PRODUCT_IDS = ['1446845', '1211051']

NO_DISCOUNT_CATEGORIES = [
    'βρεφικό γάλα', 'βρεφικο γαλα', 'baby formula',
    'βρεφική διατροφή', 'solgar'
]

# ============================================
# 🏭 B2B TAG CONFIGURATION
# ============================================
B2B_TAG_SLUG = 'b2b'  # WooCommerce tag slug
B2B_DISCOUNT = 0.20   # 20% discount

# ============================================
# 🔄 SUBSCRIPTION TAG CONFIGURATION
# ============================================
SUBSCRIBE_TAG_SLUG = 'subscribe'  # WooCommerce tag slug
SUBSCRIPTION_DISCOUNT = 0.10  # 10% discount

def is_b2b_product(product):
    """Check if product has b2b tag"""
    tags = product.get('tags', [])
    for tag in tags:
        if tag.get('slug', '').lower() == B2B_TAG_SLUG:
            return True
    return False

def get_b2b_price(product):
    """Calculate B2B price (20% discount)"""
    try:
        price = float(product.get('price', 0))
        if price <= 0:
            return None
        
        # Apply 20% B2B discount
        b2b_price = price * (1 - B2B_DISCOUNT)
        
        return round(b2b_price, 2)
    except:
        return None

def get_b2b_products():
    """Get all products with b2b tag from WooCommerce"""
    try:
        # First get the b2b tag ID
        tags_response = wcapi.get("products/tags", params={"slug": B2B_TAG_SLUG})
        tags = tags_response.json()
        
        if not tags or not isinstance(tags, list):
            logger.warning("B2B tag not found in WooCommerce")
            return []
        
        tag_id = tags[0].get('id')
        if not tag_id:
            return []
        
        # Get products with this tag
        response = wcapi.get("products", params={"tag": tag_id, "per_page": 50})
        products = response.json()
        
        return products if isinstance(products, list) else []
    except Exception as e:
        logger.error(f"Error fetching B2B products: {e}")
        return []

def get_subscription_products():
    """Get all products with subscribe tag from WooCommerce"""
    try:
        # First get the subscribe tag ID
        tags_response = wcapi.get("products/tags", params={"slug": SUBSCRIBE_TAG_SLUG})
        tags = tags_response.json()
        
        if not tags or not isinstance(tags, list):
            logger.warning("Subscribe tag not found in WooCommerce")
            return []
        
        tag_id = tags[0].get('id')
        if not tag_id:
            return []
        
        # Get products with this tag
        response = wcapi.get("products", params={"tag": tag_id, "per_page": 50})
        products = response.json()
        
        # Filter out no-discount products
        products = [p for p in products if not is_discount_excluded(p)] if isinstance(products, list) else []
        
        return products
    except Exception as e:
        logger.error(f"Error fetching subscription products: {e}")
        return []

def is_subscription_product(product):
    """Check if product has subscribe tag"""
    tags = product.get('tags', [])
    for tag in tags:
        if tag.get('slug', '').lower() == SUBSCRIBE_TAG_SLUG:
            return True
    return False

def is_discount_excluded(product):
    """Check if product is excluded from discounts"""
    product_id = str(product.get('id', ''))
    name = product.get('name', '').lower()
    
    if product_id in NO_DISCOUNT_PRODUCT_IDS:
        return True
    
    for keyword in NO_DISCOUNT_KEYWORDS:
        if keyword.lower() in name:
            return True
    
    categories = product.get('categories', [])
    for cat in categories:
        cat_name = cat.get('name', '').lower()
        for excluded in NO_DISCOUNT_CATEGORIES:
            if excluded.lower() in cat_name:
                return True
    
    return False

# ============================================
# 🎁 PROMOTIONS
# ============================================
PROMO_ATTRIBUTE = 'whatsapp promo'

ACTIVE_PROMOS = {
    'pampers_wipes': {
        'name': '🎁 ΔΩΡΟ Μωρομάντηλα Pampers!',
        'description': 'Με κάθε Pampers Premium Care Jumbo Pack, ΔΩΡΟ Pampers Aqua Harmonie 48τεμ!',
        'gift_product_id': '1446148',
        'gift_name': 'Pampers Aqua Harmonie Μωρομάντηλα 48τεμ',
        'valid_until': '2026-01-31',
        'active': True,
        'type': 'gift'
    },
    'epithimies_cashback': {
        'name': '💰 Cashback από Epithimies.gr!',
        'description': 'Επιστροφή 10€ ή 20€ σε επιλεγμένα προϊόντα!',
        'website': 'https://epithimies.gr',
        'valid_until': '2026-01-31',
        'active': True,
        'type': 'cashback'
    },
    'easypants_cashback': {
        'name': '💶 EasyPants 30τεμ = Cashback 3€!',
        'description': 'Αγόρασε EasyPants 30τεμ και πάρε 3€ επιστροφή!',
        'product_ids': ['1446701', '1446694', '1446698'],
        'cashback_amount': 3,
        'valid_until': '2026-01-31',
        'active': True,
        'type': 'cashback'
    }
}

SPECIAL_PRODUCTS = {
    'kera_bed': {
        'id': '1441515',
        'name': 'Kera Bed Υποσέντονα XL 75×90 30τμχ'
    }
}

EASYPANTS_PROMO_IDS = ['1446701', '1446694', '1446698']

# ============================================
# CUSTOMER & SESSION STORAGE
# ============================================
customers = {}
sessions = {}

# ============================================
# SUBSCRIPTION PLANS
# ============================================
SUBSCRIPTION_PLANS = {
    'weekly': {'days': 7, 'discount': 10, 'name': 'Εβδομαδιαία'},
    'biweekly': {'days': 14, 'discount': 10, 'name': 'Κάθε 2 εβδομάδες'},
    'monthly': {'days': 30, 'discount': 10, 'name': 'Μηνιαία'},
}

PICKUP_DAYS = {
    '1': 'Δευτέρα', '2': 'Τρίτη', '3': 'Τετάρτη',
    '4': 'Πέμπτη', '5': 'Παρασκευή', '6': 'Σάββατο'
}

# ============================================
# PRODUCT CATEGORIES
# ============================================
CATEGORIES = {
    '1': {'name': '👶 Βρεφικές Πάνες', 'search': 'baby diapers πάνες μωρού pampers babylino', 'type': 'baby'},
    '2': {'name': '👴 Πάνες Ενηλίκων', 'search': 'adult diapers πάνες ενηλίκων kera tena easypants', 'type': 'adult'},
    '3': {'name': '🐕 Pet Πάνες & Τροφές', 'search': 'pet easypet training pads σκύλος γάτα', 'type': 'pet'},
    '4': {'name': '🍼 Βρεφικό Γάλα', 'search': 'humana nan βρεφικό γάλα formula', 'type': 'formula', 'no_discount': True},
    '5': {'name': '🧻 Χαρτικά', 'search': 'paper χαρτί toilet', 'type': 'general'},
    '6': {'name': '🧼 Απορρυπαντικά', 'search': 'detergent απορρυπαντικό', 'type': 'general'},
    '7': {'name': '💊 Βιταμίνες', 'search': 'vitamins βιταμίνες', 'type': 'vitamins', 'no_discount': True},
    '8': {'name': '🧽 Μαντηλάκια', 'search': 'wipes μαντηλάκια', 'type': 'both'},
    '9': {'name': '🩹 Sudocrem & Φροντίδα', 'search': 'sudocrem baby care κρέμα', 'type': 'both'},
    '10': {'name': '🛏️ Υποσέντονα', 'search': 'υποσέντονα bed pads kera bed', 'type': 'adult'}
}

# ============================================
# MAIN WEBHOOK
# ============================================
@app.route("/webhook", methods=['POST'])
def webhook():
    """Handle incoming WhatsApp messages"""
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')

    logger.info(f"📱 Received from {from_number}: {incoming_msg}")

    resp = MessagingResponse()
    msg = resp.message()

    customer = get_or_create_customer(from_number)
    
    if from_number not in sessions:
        sessions[from_number] = {'state': 'welcome'}
    session = sessions[from_number]

    if session.get('ai_mode') and claude_client:
        response_text = handle_ai_conversation(incoming_msg, customer, session)
    else:
        response_text = route_message(incoming_msg, customer, session)

    customer['last_interaction'] = datetime.now().isoformat()
    
    msg.body(response_text)
    return str(resp)

def route_message(msg, customer, session):
    """Route message to appropriate handler"""
    state = session.get('state', 'welcome')
    msg_lower = msg.lower()
    
    # Global commands
    if msg_lower in ['menu', 'μενού', 'αρχή', 'start', '0']:
        session['state'] = 'menu'
        session['ai_mode'] = False
        return get_main_menu(customer)
    
    if msg_lower in ['help', 'βοήθεια', '?']:
        return get_help_message()
    
    if msg_lower in ['καταστήματα', 'stores', 'αλλαγή καταστήματος']:
        session['state'] = 'store_selection'
        return get_store_selection_menu()
    
    if msg_lower in ['franchise', 'franchising', 'δικαιόχρηση']:
        return get_franchise_menu()
    
    if msg_lower in ['wholesale', 'χονδρική', 'b2b', 'επαγγελματίες']:
        session['state'] = 'wholesale'
        return get_wholesale_menu()
    
    if msg_lower in ['θέση', 'location', 'διεύθυνση', 'χάρτης', 'map']:
        return get_location_message(customer)
    
    if msg_lower in ['ai', 'claude', 'chat']:
        if claude_client:
            session['ai_mode'] = True
            session['ai_history'] = []
            return "🤖 AI Βοηθός!\n\nΡώτα με οτιδήποτε!\n\n(Γράψε 'menu')"
        return "AI δεν είναι διαθέσιμο."

    handlers = {
        'welcome': handle_welcome,
        'menu': handle_menu,
        'search': handle_search,
        'product_list': handle_product_selection,
        'product_choice': handle_product_choice,
        'categories': handle_categories,
        'promos': handle_promos_menu,
        'subscription': handle_subscription,
        'subscription_product': handle_subscription_product,
        'subscription_frequency': handle_subscription_frequency,
        'subscription_day': handle_subscription_day,
        'subscription_confirm': handle_subscription_confirm,
        'my_account': handle_my_account,
        'customer_service': handle_customer_service,
        'complaint_form': handle_complaint_form,
        'product_request': handle_product_request,
        'feedback': handle_feedback,
        'store_selection': handle_store_selection,
        'franchise': handle_franchise,
        'wholesale': handle_wholesale,
        'wholesale_inquiry': handle_wholesale_inquiry,
        'wholesale_phone': handle_wholesale_phone,
    }
    
    handler = handlers.get(state, handle_welcome)
    return handler(msg, customer, session)

# ============================================
# CUSTOMER MANAGEMENT
# ============================================
def get_or_create_customer(phone):
    """Get or create customer profile"""
    if phone not in customers:
        customers[phone] = {
            'phone': phone,
            'created': datetime.now().isoformat(),
            'last_interaction': datetime.now().isoformat(),
            'orders': [],
            'subscriptions': [],
            'preferences': {},
            'points': 0,
            'selected_store': DEFAULT_STORE,
            'customer_type': None,
            'is_business': False,
            'business_type': None
        }
    return customers[phone]

def get_customer_store(customer):
    """Get customer's selected store"""
    store_id = customer.get('selected_store', DEFAULT_STORE)
    return STORES.get(store_id, STORES[DEFAULT_STORE])

def get_customer_greeting(customer):
    """Get personalized greeting"""
    name = customer.get('name')
    hour = datetime.now().hour
    
    if hour < 12:
        greeting = "Καλημέρα"
    elif hour < 17:
        greeting = "Καλησπέρα"
    else:
        greeting = "Καλησπέρα"
    
    if name:
        return f"{greeting} {name}! 👋"
    return f"{greeting}! 👋"

# ============================================
# 🏪 STORE SELECTION
# ============================================
def get_store_selection_menu():
    """Get store selection menu"""
    text = """🏪 ΕΠΙΛΕΞΕ ΚΑΤΑΣΤΗΜΑ

"""
    store_list = list(STORES.keys())
    for i, store_id in enumerate(store_list, 1):
        store = STORES[store_id]
        drive = " 🚗" if store.get('drive_through') else ""
        text += f"{i}️⃣ {store['short_name']}{drive}\n"
    
    text += """
🚗 = Drive-Through διαθέσιμο

Επίλεξε 1-6 (ή 'menu')"""
    return text

def handle_store_selection(msg, customer, session):
    """Handle store selection"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)
    
    store_list = list(STORES.keys())
    
    try:
        index = int(msg) - 1
        if 0 <= index < len(store_list):
            store_id = store_list[index]
            customer['selected_store'] = store_id
            store = STORES[store_id]
            
            session['state'] = 'menu'
            
            drive_text = "\n🚗 Drive-Through διαθέσιμο!" if store.get('drive_through') else ""
            
            return f"""✅ ΕΠΙΛΕΧΘΗΚΕ!

🏪 {store['name']}
📍 {store['address']}
{drive_text}

Γράψε 'menu' για να συνεχίσεις!"""
    except ValueError:
        pass
    
    return "Επίλεξε 1-6 (ή 'menu')"

# ============================================
# 🏢 FRANCHISE
# ============================================
def get_franchise_menu():
    """Get franchise information"""
    benefits = "\n".join([f"✅ {b}" for b in FRANCHISE_INFO['benefits']])
    
    return f"""🏢 FRANCHISE CARESTORES

Θέλεις να ανοίξεις δικό σου κατάστημα;

{benefits}

━━━━━━━━━━━━━━━━━━━━

📺 VIDEO: {FRANCHISE_INFO['youtube']}
🌐 INFO: {FRANCHISE_INFO['website']}

━━━━━━━━━━━━━━━━━━━━

1️⃣ 📝 ΘΕΛΩ ΠΛΗΡΟΦΟΡΙΕΣ
   (θα σας καλέσουμε)

📧 {FRANCHISE_INFO.get('email', 'franchise@carestores.gr')}
📞 6942508739

('menu' για επιστροφή)"""

def handle_franchise(msg, customer, session):
    """Handle franchise lead capture"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)
    
    step = session.get('franchise_step', 'intro')
    
    if step == 'intro':
        if msg == '1':
            session['franchise_step'] = 'name'
            return "📝 ΑΙΤΗΣΗ FRANCHISE\n\nΠαρακαλώ πείτε μας το όνομά σας:"
        return get_franchise_menu()
    
    elif step == 'name':
        session['franchise_name'] = msg
        session['franchise_step'] = 'phone'
        return f"✅ {msg}\n\nΤηλέφωνο επικοινωνίας:"
    
    elif step == 'phone':
        phone_clean = msg.strip().replace(' ', '').replace('-', '')
        if len(phone_clean) >= 10:
            session['franchise_phone'] = msg
            session['franchise_step'] = 'email'
            return f"✅ {msg}\n\nEmail (ή 'skip' για παράλειψη):"
        return "❌ Μη έγκυρο τηλέφωνο.\nΠαρακαλώ ξαναπροσπαθήστε:"
    
    elif step == 'email':
        email = msg.strip()
        if email.lower() == 'skip':
            email = "Δεν δόθηκε"
        elif '@' not in email or '.' not in email:
            return "❌ Μη έγκυρο email.\nΠροσπαθήστε ξανά (ή 'skip'):"
        
        # Collect all data
        name = session.get('franchise_name', 'N/A')
        phone = session.get('franchise_phone', 'N/A')
        customer_phone = customer.get('phone', 'N/A')
        
        # Log the lead
        logger.info(f"🏢 FRANCHISE LEAD: {name} - {phone} - {email} - {customer_phone}")
        
        # Send email
        email_subject = f"🏢 Νέο Ενδιαφέρον Franchise - {name}"
        email_html = f"""
        <h2>🏢 Νέο Ενδιαφέρον Franchise</h2>
        <hr>
        <p><strong>Όνομα:</strong> {name}</p>
        <p><strong>Τηλέφωνο:</strong> {phone}</p>
        <p><strong>Email:</strong> {email}</p>
        <p><strong>WhatsApp:</strong> {customer_phone}</p>
        <p><strong>Ημερομηνία:</strong> {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
        <hr>
        <p>Παρακαλώ επικοινωνήστε το συντομότερο δυνατό.</p>
        """
        
        send_email([EMAIL_CONFIG['store_emails']['support']], email_subject, email_html)
        
        # Clear session
        session['franchise_step'] = 'intro'
        session['state'] = 'menu'
        
        return f"""✅ ΑΙΤΗΣΗ ΚΑΤΑΧΩΡΗΘΗΚΕ!

📋 Στοιχεία:
👤 {name}
📞 {phone}
📧 {email}

━━━━━━━━━━━━━━━━━━━━

Η ομάδα μας θα επικοινωνήσει
μαζί σας εντός 24-48 ωρών!

Ευχαριστούμε για το ενδιαφέρον! 🙏

Γράψε 'menu' για αρχικό"""
    
    return get_franchise_menu()

# ============================================
# 🏭 WHOLESALE / B2B
# ============================================
def get_wholesale_menu():
    """Get wholesale/B2B menu"""
    return f"""🏭 ΧΟΝΔΡΙΚΗ / B2B

Είστε επαγγελματίας;
Ειδικές τιμές για:

1️⃣ 🏫 Παιδικός Σταθμός
2️⃣ 🏥 Γηροκομείο
3️⃣ ⛪ Εκκλησιαστικό Ίδρυμα
4️⃣ 👴 Κέντρο Φροντίδας Ηλικιωμένων
5️⃣ 🏛️ ΚΑΠΗ
6️⃣ 🏨 Ξενοδοχείο / Άλλο

━━━━━━━━━━━━━━━━━━━━

💰 ΠΛΕΟΝΕΚΤΗΜΑΤΑ:
• Έκπτωση -20%
• Τιμολόγιο
• Παράδοση στην αποθήκη σας

🚚 ΜΕΤΑΦΟΡΙΚΑ:
• ΔΩΡΕΑΝ για παραγγελίες 350€+
• 15€ για μικρότερες παραγγελίες

━━━━━━━━━━━━━━━━━━━━

7️⃣ 📦 ΔΕΣ ΠΡΟΪΟΝΤΑ B2B

🌐 {WHOLESALE_INFO['website']}
🏢 {WHOLESALE_INFO['b2b_portal']}

Επίλεξε 1-7 (ή 'menu')"""

def handle_wholesale(msg, customer, session):
    """Handle wholesale menu"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)
    
    # Option 7: View B2B products
    if msg == '7':
        # Mark customer as business to see B2B prices
        customer['is_business'] = True
        products = get_b2b_products()
        if products:
            session['state'] = 'product_list'
            session['products'] = products
            return format_b2b_product_list(products, "🏭 ΠΡΟΪΟΝΤΑ B2B")
        return "Δεν βρέθηκαν B2B προϊόντα.\n\n(Πληκτρολόγησε 'menu')"
    
    business_types = {
        '1': {'type': 'daycare', 'name': 'Παιδικός Σταθμός'},
        '2': {'type': 'nursing_home', 'name': 'Γηροκομείο'},
        '3': {'type': 'church', 'name': 'Εκκλησιαστικό Ίδρυμα'},
        '4': {'type': 'elderly_care', 'name': 'Κέντρο Φροντίδας'},
        '5': {'type': 'kapi', 'name': 'ΚΑΠΗ'},
        '6': {'type': 'other', 'name': 'Ξενοδοχείο/Άλλο'}
    }
    
    if msg in business_types:
        biz = business_types[msg]
        customer['is_business'] = True
        customer['business_type'] = biz['type']
        
        session['state'] = 'wholesale_inquiry'
        session['business_info'] = biz
        
        return f"""✅ {biz['name']}

━━━━━━━━━━━━━━━━━━━━
💰 ΤΙΜΕΣ ΧΟΝΔΡΙΚΗΣ
━━━━━━━━━━━━━━━━━━━━

📊 Έκπτωση: -20%
📄 Τιμολόγιο: ΝΑΙ

━━━━━━━━━━━━━━━━━━━━
🚚 ΠΑΡΑΔΟΣΗ ΣΤΗΝ ΑΠΟΘΗΚΗ ΣΑΣ
━━━━━━━━━━━━━━━━━━━━

✅ ΔΩΡΕΑΝ για παραγγελίες 350€+
💵 15€ για μικρότερες παραγγελίες

━━━━━━━━━━━━━━━━━━━━

🌐 B2B Portal:
{WHOLESALE_INFO['b2b_portal']}

📞 {WHOLESALE_INFO['contact_phone']}

━━━━━━━━━━━━━━━━━━━━

Θέλετε να επικοινωνήσουμε μαζί σας;

1️⃣ Ναι, στείλτε τηλέφωνο/email
2️⃣ Όχι, θα επικοινωνήσω
3️⃣ 📦 Δες προϊόντα B2B

(ή 'menu')"""
    
    return get_wholesale_menu()

def handle_wholesale_inquiry(msg, customer, session):
    """Handle wholesale inquiry"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)
    
    if msg == '1':
        session['state'] = 'wholesale_phone'
        return """📞 Στείλτε τηλέφωνο ή email:

(σταθερό, κινητό ή email)"""
    
    elif msg == '2':
        session['state'] = 'menu'
        biz = session.get('business_info', {})
        return f"""📋 ΕΠΙΚΟΙΝΩΝΗΣΤΕ ΜΑΖΙ ΜΑΣ

🌐 {WHOLESALE_INFO['b2b_portal']}
📞 {WHOLESALE_INFO['contact_phone']}

Αναφέρατε ότι είστε: {biz.get('name', 'Επαγγελματίας')}

Γράψε 'menu'"""
    
    elif msg == '3':
        # Show B2B products
        products = get_b2b_products()
        if products:
            session['state'] = 'product_list'
            session['products'] = products
            return format_b2b_product_list(products, "ΠΡΟΪΟΝΤΑ B2B")
        return "Δεν βρέθηκαν B2B προϊόντα.\n\n(Γράψε 'menu')"
    
    # Assume it's a phone number
    if len(msg) >= 10:
        biz = session.get('business_info', {})
        logger.info(f"B2B LEAD: {biz.get('name')} - {msg} - {customer['phone']}")
        session['state'] = 'menu'
        return f"""✅ ΚΑΤΑΧΩΡΗΘΗΚΕ!

Θα σας καλέσουμε σύντομα στο:
📞 {msg}

Τύπος: {biz.get('name', 'Επαγγελματίας')}

Ευχαριστούμε!

Γράψε 'menu'"""
    
    return "Επίλεξε 1, 2 ή 3 (ή στείλε τηλέφωνο)"

def handle_wholesale_phone(msg, customer, session):
    """Handle B2B phone/email capture"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)
    
    # Clean input
    contact = msg.strip()
    biz = session.get('business_info', {})
    business_name = biz.get('name', 'Επαγγελματίας')
    
    # Check if it's an email
    is_email = '@' in contact and '.' in contact
    
    # Check if it's a phone (mobile or landline, 10+ digits)
    phone_clean = contact.replace(' ', '').replace('-', '').replace('+', '')
    is_phone = len(phone_clean) >= 10 and phone_clean.isdigit()
    
    if is_email or is_phone:
        contact_type = "Email" if is_email else "Τηλέφωνο"
        
        # LOG THE B2B LEAD
        logger.info(f"🏭 B2B LEAD: {business_name} - {contact} - {customer['phone']}")
        
        # Save to customer profile
        customer['b2b_contact'] = contact
        customer['is_business'] = True
        
        session['state'] = 'menu'
        return f"""✅ ΚΑΤΑΧΩΡΗΘΗΚΕ!

Θα επικοινωνήσουμε σύντομα:
📞 {contact}

Τύπος: {business_name}

━━━━━━━━━━━━━━━━━━━━

Ευχαριστούμε για το ενδιαφέρον!
Η ομάδα μας θα επικοινωνήσει
μαζί σας εντός 24 ωρών.

Γράψε 'menu' για αρχικό μενού"""
    
    return f"""❌ Μη έγκυρο στοιχείο επικοινωνίας.

Παρακαλώ στείλτε:
📞 Τηλέφωνο (σταθερό ή κινητό)
📧 Ή email

Π.χ. 6912345678, 2101234567
     info@company.gr

(ή 'menu' για έξοδο)"""

# ============================================
# MAIN MENU
# ============================================
def get_main_menu(customer):
    """Get personalized main menu"""
    greeting = get_customer_greeting(customer)
    store = get_customer_store(customer)
    
    store_text = f"📍 {store['short_name']}"
    if store.get('drive_through'):
        store_text += " 🚗"
    
    return f"""{greeting}
🛒 CARESTORES - {store_text}

1️⃣ 🔍 Αναζήτηση
2️⃣ 🔥 Δημοφιλή
3️⃣ 🎁 Προσφορές
4️⃣ 📦 Κατηγορίες
5️⃣ 🔄 Συνδρομή -10%
6️⃣ 👤 Λογαριασμός
7️⃣ 📍 Google Maps
8️⃣ 📞 Εξυπηρέτηση
9️⃣ 🏪 Αλλαγή Καταστ.
🔟 🏢 Franchise
1️⃣1️⃣ 🏭 B2B/Χονδρική

Απάντησε 1-11"""

def handle_welcome(msg, customer, session):
    """Handle welcome"""
    session['state'] = 'menu'
    return get_main_menu(customer)

def handle_menu(msg, customer, session):
    """Handle menu selection"""
    if msg == '1':
        session['state'] = 'search'
        return "🔍 Γράψε το προϊόν:"

    elif msg == '2':
        products = get_popular_products()
        if products:
            session['state'] = 'product_list'
            session['products'] = products
            return format_product_list(products, "🔥 Δημοφιλή", check_promo=True)
        return "Σφάλμα!"

    elif msg == '3':
        session['state'] = 'promos'
        return get_all_promos_message()

    elif msg == '4':
        session['state'] = 'categories'
        return get_categories_menu()

    elif msg == '5':
        session['state'] = 'subscription'
        return get_subscription_intro(customer)

    elif msg == '6':
        session['state'] = 'my_account'
        return get_account_info(customer)

    elif msg == '7':
        return get_location_message(customer)

    elif msg == '8':
        session['state'] = 'customer_service'
        return get_customer_service_menu()

    elif msg == '9':
        session['state'] = 'store_selection'
        return get_store_selection_menu()

    elif msg == '10':
        session['state'] = 'franchise'
        session['franchise_step'] = 'intro'
        return get_franchise_menu()

    elif msg == '11':
        session['state'] = 'wholesale'
        return get_wholesale_menu()

    return "Επίλεξε 1-11"

# ============================================
# LOCATION
# ============================================
def get_location_message(customer):
    """Get store location"""
    store = get_customer_store(customer)
    
    drive_text = "\n🚗 DRIVE-THROUGH διαθέσιμο!" if store.get('drive_through') else ""
    parking_text = f"\n🅿️ {store['parking']}" if store.get('parking') else ""
    
    return f"""📍 {store['name']}

🏪 {store['address']}

🗺️ Google Maps:
{store['google_maps']}
{drive_text}{parking_text}

⏰ ΩΡΑΡΙΟ:
• Δευ-Παρ: {store['hours']['weekdays']}
• Σάββατο: {store['hours']['saturday']}
• Κυριακή: {store['hours']['sunday']}

📞 {store.get('phone', '210 680 0549')}

━━━━━━━━━━━━━━━━━━━━
🏪 Άλλα καταστήματα; Γράψε '9'

Γράψε 'menu'"""

# ============================================
# AI CONVERSATION
# ============================================
def handle_ai_conversation(msg, customer, session):
    """Handle AI conversation"""
    if msg.lower() == 'menu':
        session['ai_mode'] = False
        session['state'] = 'menu'
        return get_main_menu(customer)
    
    if not claude_client:
        session['ai_mode'] = False
        return "AI δεν είναι διαθέσιμο."
    
    try:
        store = get_customer_store(customer)
        
        context = f"""
CARESTORES - {store['name']}
Location: {store['address']}
Hours: Mon-Fri {store['hours']['weekdays']}, Sat {store['hours']['saturday']}

STORES: Χαλάνδρι, Αμπελόκηποι, Γέρακας, Χολαργός, Κάλυμνος, Λαμία

PRODUCTS: Baby diapers, Adult incontinence, Pet products, Baby formula (Humana, NAN - NO DISCOUNTS), Wipes, Sudocrem, Vitamins (Solgar - NO DISCOUNTS)

PROMOS: Pampers Jumbo = FREE wipes, EasyPants 30pcs = 3€ cashback

B2B/WHOLESALE: For daycares, nursing homes, churches, KAPI - 15-30% discounts
Website: easycaremarket.gr, b2b.easycaremarket.gr

FRANCHISE: carestores.gr/franchise - YouTube: youtu.be/eA5Lk0t7P1o

RULES: Answer in Greek, be concise, mention promos when relevant, NEVER suggest discounts for baby formula or Solgar
"""
        
        if 'ai_history' not in session:
            session['ai_history'] = []
        
        session['ai_history'].append({"role": "user", "content": msg})
        history = session['ai_history'][-10:]
        
        response = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            system=f"You are a WhatsApp assistant for CARESTORES. Respond in Greek. Be friendly and concise.\n\n{context}",
            messages=history
        )
        
        ai_response = response.content[0].text
        session['ai_history'].append({"role": "assistant", "content": ai_response})
        
        return f"🤖 {ai_response}\n\n('menu')"
        
    except Exception as e:
        logger.error(f"AI error: {e}")
        session['ai_mode'] = False
        return "Σφάλμα AI. Γράψε 'menu'."

# ============================================
# CATEGORIES
# ============================================
def get_categories_menu():
    """Get categories menu"""
    return """📦 ΚΑΤΗΓΟΡΙΕΣ

1️⃣ 👶 Βρεφικές Πάνες
2️⃣ 👴 Πάνες Ενηλίκων
3️⃣ 🐕 Pet Πάνες & Τροφές
4️⃣ 🍼 Βρεφικό Γάλα ⚠️
5️⃣ 🧻 Χαρτικά
6️⃣ 🧼 Απορρυπαντικά
7️⃣ 💊 Βιταμίνες ⚠️
8️⃣ 🧽 Μαντηλάκια
9️⃣ 🩹 Sudocrem & Φροντίδα
🔟 🛏️ Υποσέντονα

⚠️ = Χωρίς εκπτώσεις

Επίλεξε 1-10"""

def handle_categories(msg, customer, session):
    """Handle category selection"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)

    cat_map = {'1': '1', '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9', '10': '10'}
    
    if msg in cat_map and cat_map[msg] in CATEGORIES:
        category = CATEGORIES[cat_map[msg]]
        products = search_products(category['search'])
        
        if products:
            session['state'] = 'product_list'
            session['products'] = products
            session['current_category'] = category
            
            no_discount = category.get('no_discount', False)
            return format_product_list(products, f"📦 {category['name']}", check_promo=True, no_discount_category=no_discount)
        return "Δεν βρέθηκαν προϊόντα."

    return "Επίλεξε 1-10"

# ============================================
# SEARCH
# ============================================
def handle_search(msg, customer, session):
    """Handle product search"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)

    products = search_products(msg)

    if products:
        session['state'] = 'product_list'
        session['products'] = products
        return format_product_list(products, f"🔍 '{msg}'", check_promo=True)

    return f"Δεν βρέθηκαν για '{msg}'\n\nΔοκίμασε: pampers, humana, kera\n\nΓράψε 'menu'"

def handle_product_selection(msg, customer, session):
    """Handle product selection"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)

    if msg.lower() in ['more', 'περισσότερα']:
        page = session.get('current_page', 1) + 1
        session['current_page'] = page
        products = session.get('products', [])
        if products:
            return format_product_list(products, session.get('list_title', 'Προϊόντα'), page)

    try:
        index = int(msg) - 1
        products = session.get('products', [])
        page = session.get('current_page', 1)
        adjusted_index = (page - 1) * 10 + index
        
        if 0 <= adjusted_index < len(products):
            product = products[adjusted_index]
            session['selected_product'] = product
            
            # If coming from subscription flow, go directly to frequency
            if session.get('after_product') == 'subscription_frequency':
                if is_discount_excluded(product):
                    session['state'] = 'menu'
                    return f"⚠️ Το \"{product.get('name')}\" δεν συμμετέχει σε εκπτώσεις.\n\nΓράψε 'menu'"
                
                session['state'] = 'subscription_frequency'
                session['sub_frequency_shown'] = False
                return handle_subscription_frequency('', customer, session)
            
            # Normal product view - show options (1 or 2)
            session['state'] = 'product_choice'
            return format_product_details(product, customer)
        else:
            return "Μη έγκυρη επιλογή!"
    except ValueError:
        return "Στείλε αριθμό!"

def generate_order_id():
    """Generate unique order ID"""
    import random
    timestamp = datetime.now().strftime("%H%M")
    random_part = random.randint(100, 999)
    return f"DT-{timestamp}-{random_part}"

def handle_product_choice(msg, customer, session):
    """Handle product purchase choice (one-off vs subscription vs drive-through)"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)
    
    product = session.get('selected_product')
    if not product:
        session['state'] = 'menu'
        return get_main_menu(customer)
    
    store = get_customer_store(customer)
    name = product.get('name', 'N/A')
    price = product.get('price', '0')
    
    if msg == '1':
        # One-off purchase - show store info for pickup
        session['state'] = 'menu'
        return f"""🛒 ΑΓΟΡΑ: {name}

💰 Τιμή: {price}€

📍 Παραλαβή από:
{store['name']}
{store['address']}

📞 {store.get('phone', '210 680 0549')}

🗺️ {store.get('google_maps', '')}

Γράψε 'menu' για αρχικό"""
    
    elif msg == '2':
        # Subscription
        if is_discount_excluded(product):
            session['state'] = 'menu'
            return f"⚠️ Το \"{name}\" δεν συμμετέχει σε εκπτώσεις.\n\nΓράψε 'menu'"
        
        session['state'] = 'subscription_frequency'
        session['sub_frequency_shown'] = False
        return handle_subscription_frequency('', customer, session)
    
    elif msg == '3' and store.get('drive_through'):
        # Drive-through reservation
        order_id = generate_order_id()
        expires = datetime.now() + timedelta(hours=3)
        expires_str = expires.strftime("%H:%M")
        
        # Log the reservation
        logger.info(f"🚗 DRIVE-THROUGH ORDER: {order_id} - {name} - {price}€ - {customer['phone']}")
        
        # Prepare email
        customer_phone = customer.get('phone', 'N/A')
        email_subject = f"🚗 Drive-Through Order: {order_id}"
        email_html = f"""
        <h2>🚗 Νέα Παραγγελία Drive-Through</h2>
        <hr>
        <p><strong>Order ID:</strong> {order_id}</p>
        <p><strong>Προϊόν:</strong> {name}</p>
        <p><strong>Τιμή:</strong> {price}€</p>
        <p><strong>Κατάστημα:</strong> {store['name']}</p>
        <p><strong>Πελάτης:</strong> {customer_phone}</p>
        <p><strong>Ώρα:</strong> {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
        <p><strong>Λήξη κράτησης:</strong> {expires_str}</p>
        <hr>
        <p>⚠️ Η κράτηση ισχύει για 3 ώρες.</p>
        """
        
        # Send emails
        store_email = EMAIL_CONFIG['store_emails'].get(store['id'], EMAIL_CONFIG['store_emails']['chalandri'])
        send_email([store_email, EMAIL_CONFIG['store_emails']['support']], email_subject, email_html)
        
        session['state'] = 'menu'
        return f"""✅ ΚΡΑΤΗΣΗ ΕΠΙΒΕΒΑΙΩΘΗΚΕ!

🎫 Order ID: {order_id}

📦 {name}
💰 {price}€

━━━━━━━━━━━━━━━━━━━━

🚗 DRIVE-THROUGH
📍 {store['name']}
{store['address']}

⏰ Ισχύει μέχρι: {expires_str}
(3 ώρες από τώρα)

━━━━━━━━━━━━━━━━━━━━

📞 {store.get('phone', '')}
🗺️ {store.get('google_maps', '')}

Δείξτε το Order ID στο κατάστημα!

Γράψε 'menu' για αρχικό"""
    
    return "Επίλεξε 1, 2 ή 3 (ή 'menu')"

# ============================================
# PRODUCT FORMATTING
# ============================================
def format_b2b_product_list(products, title):
    """Format B2B product list with 20% discount"""
    if not products:
        return "Δεν βρέθηκαν B2B προϊόντα 😔"
    
    text = f"🏭 {title}\n"
    text += f"━━━━━━━━━━━━━━━━━━━━\n"
    text += f"💰 Έκπτωση: -20%\n"
    text += f"🚚 ΔΩΡΕΑΝ μεταφορικά 350€+\n"
    text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, product in enumerate(products[:15], 1):
        name = product.get('name', 'N/A')
        retail_price = product.get('price', '0')
        stock = product.get('stock_status', 'outofstock')
        stock_emoji = "✅" if stock == "instock" else "❌"
        
        # Calculate B2B price (20% off)
        b2b_price = get_b2b_price(product)
        b2b_str = f"{b2b_price}€" if b2b_price else "N/A"
        
        text += f"{i}. {name}\n"
        text += f"   💶 B2B: {b2b_str} (Λιανική: {retail_price}€) {stock_emoji}\n\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += "Αριθμό για λεπτομέρειες\n"
    text += "('menu' | 'wholesale')"
    
    return text

def format_subscription_product_list(products, title):
    """Format subscription product list with 10% discount"""
    if not products:
        return "Δεν βρέθηκαν προϊόντα συνδρομής 😔"
    
    text = f"🔄 {title}\n"
    text += f"━━━━━━━━━━━━━━━━━━━━\n"
    text += f"💰 Έκπτωση: -10% ΠΑΝΤΑ\n"
    text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, product in enumerate(products[:15], 1):
        name = product.get('name', 'N/A')
        try:
            retail_price = float(product.get('price', '0'))
            sub_price = round(retail_price * 0.90, 2)
        except:
            retail_price = 0
            sub_price = 0
        
        stock = product.get('stock_status', 'outofstock')
        stock_emoji = "✅" if stock == "instock" else "❌"
        
        text += f"{i}. {name}\n"
        text += f"   🔄 Συνδρομή: {sub_price}€ (Λιαν: {retail_price}€) {stock_emoji}\n\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += "Αριθμό για επιλογή προϊόντος\n"
    text += "('menu')"
    
    return text

def format_product_list(products, title, page=1, check_promo=False, no_discount_category=False):
    """Format product list"""
    if not products:
        return "Δεν βρέθηκαν 😔"

    per_page = 10
    start = (page - 1) * per_page
    end = start + per_page
    page_products = products[start:end]

    if not page_products:
        return "Δεν υπάρχουν άλλα."

    easypants_ids = ACTIVE_PROMOS.get('easypants_cashback', {}).get('product_ids', [])

    text = f"📦 {title}\n"
    if len(products) > per_page:
        text += f"(Σελ. {page}/{(len(products)-1)//per_page + 1})\n"
    
    if no_discount_category:
        text += "⚠️ Χωρίς εκπτώσεις\n"
    
    text += "\n"

    for i, product in enumerate(page_products, start + 1):
        name = product.get('name', 'N/A')
        price = product.get('price', '0')
        stock = product.get('stock_status', 'outofstock')
        stock_emoji = "✅" if stock == "instock" else "❌"
        product_id = str(product.get('id', ''))
        
        indicators = ""
        excluded = is_discount_excluded(product)
        
        if excluded:
            indicators += " ⚠️"
        
        if check_promo and not excluded:
            name_lower = name.lower()
            if 'jumbo' in name_lower and 'premium' in name_lower:
                indicators += " 🎁"
        
        if product_id in easypants_ids:
            indicators += " 💶3€"
        
        text += f"{i}. {name}{indicators}\n   💰 {price}€ {stock_emoji}\n\n"

    text += "Αριθμό για λεπτομέρειες\n"
    if end < len(products):
        text += "'more' για περισσότερα\n"
    text += "('menu')"

    return text

def format_product_details(product, customer=None):
    """Format product details with purchase options"""
    name = product.get('name', 'N/A')
    price = product.get('price', '0')
    stock = product.get('stock_status', 'outofstock')
    product_id = str(product.get('id', ''))
    name_lower = name.lower()
    
    excluded = is_discount_excluded(product)
    store = get_customer_store(customer) if customer else STORES[DEFAULT_STORE]
    is_b2b = is_b2b_product(product)
    is_business_customer = customer and customer.get('is_business', False)
    has_drive_through = store.get('drive_through', False)

    text = f"📦 {name}\n\n"
    text += f"💰 Τιμή: {price}€\n"
    
    # Show B2B price if product has b2b tag AND customer is business
    if is_b2b and is_business_customer:
        b2b_price = get_b2b_price(product)
        if b2b_price:
            text += f"🏭 B2B: {b2b_price}€ (-20%)\n"
    elif is_b2b:
        text += f"🏭 Διαθέσιμο για B2B\n"
    
    text += f"📊 {'Διαθέσιμο ✅' if stock == 'instock' else 'Εξαντλήθηκε ❌'}\n"

    if excluded:
        text += "\n⚠️ Σταθερή τιμή - χωρίς εκπτώσεις.\n"
        text += f"\n📍 {store['short_name']}\n"
        if has_drive_through:
            text += f"\n1️⃣ 🚗 Κράτηση Drive-Through (3 ώρες)"
        text += "\n('menu' για αρχικό)"
    else:
        easypants_ids = EASYPANTS_PROMO_IDS
        if product_id in easypants_ids:
            text += "\n💶 CASHBACK 3€!\n"
        
        if 'jumbo' in name_lower and 'premium' in name_lower and 'pampers' in name_lower:
            text += "\n🎁 ΔΩΡΟ Pampers Aqua Harmonie!\n"
        
        sub_price = float(price) * 0.9
        text += f"""
━━━━━━━━━━━━━━━━━━━━
ΤΙ ΘΕΛΕΤΕ ΝΑ ΚΑΝΕΤΕ;

1️⃣ 🛒 Μία αγορά ({price}€)
2️⃣ 🔄 Συνδρομή ({sub_price:.2f}€ -10%)"""
        
        if has_drive_through:
            text += f"\n3️⃣ 🚗 Drive-Through κράτηση"
        
        text += f"""

📍 {store['short_name']}
('menu' για αρχικό)"""

    return text

# ============================================
# PROMOS
# ============================================
def get_all_promos_message():
    """Get all promotions"""
    return f"""🎁 ΠΡΟΣΦΟΡΕΣ!

━━━━━━━━━━━━━━━━━━━━
🎁 Pampers Premium Care Jumbo
= ΔΩΡΟ Aqua Harmonie 48τεμ!
━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━
💶 EasyPants 30τεμ = 3€ Cashback!
━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━
💰 Epithimies.gr Cashback 10€/20€!
🌐 https://epithimies.gr
━━━━━━━━━━━━━━━━━━━━

⚠️ Βρεφικό γάλα & Solgar 
χωρίς εκπτώσεις.

1️⃣ Δες προϊόντα
2️⃣ Αναζήτηση

('menu')"""

def handle_promos_menu(msg, customer, session):
    """Handle promos"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)
    
    if msg == '1':
        products = get_sale_products()
        if products:
            session['state'] = 'product_list'
            session['products'] = products
            return format_product_list(products, "💰 Προσφορές", check_promo=True)
        return "Δεν βρέθηκαν."
    elif msg == '2':
        session['state'] = 'search'
        return "🔍 Γράψε προϊόν:"
    
    return get_all_promos_message()

# ============================================
# SUBSCRIPTION
# ============================================
def get_subscription_intro(customer):
    """Get subscription intro"""
    return """🔄 ΣΥΝΔΡΟΜΗ -10%

✅ 10% ΕΚΠΤΩΣΗ πάντα
✅ Υπενθύμιση WhatsApp
✅ Αλλαγή/ακύρωση ελεύθερα

⚠️ ΕΞΑΙΡΕΣΕΙΣ:
• Βρεφικό γάλα (Humana, NAN)
• Solgar

1️⃣ 📦 Δες προϊόντα συνδρομής
2️⃣ 🔍 Αναζήτηση προϊόντος
3️⃣ ℹ️ Περισσότερες πληροφορίες

('menu')"""

def handle_subscription(msg, customer, session):
    """Handle subscription"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)

    if msg == '1':
        # Get products with subscribe tag
        products = get_subscription_products()
        if products:
            session['products'] = products
            session['state'] = 'product_list'
            session['after_product'] = 'subscription_frequency'
            return format_subscription_product_list(products, "ΠΡΟΪΟΝΤΑ ΣΥΝΔΡΟΜΗΣ")
        return "Δεν βρέθηκαν προϊόντα συνδρομής.\n\nΓράψε '2' για αναζήτηση ή 'menu'"
    
    elif msg == '2':
        session['state'] = 'subscription_product'
        return """📦 ΚΑΤΗΓΟΡΙΑ

1️⃣ 👶 Βρεφικές Πάνες
2️⃣ 👴 Πάνες Ενηλίκων
3️⃣ 🐕 Pet
4️⃣ 🧽 Μαντηλάκια
5️⃣ 🔍 Άλλο

Επίλεξε 1-5"""

    elif msg == '3':
        return """📋 ΠΩΣ ΛΕΙΤΟΥΡΓΕΙ

1️⃣ Επιλέγεις προϊόν
2️⃣ Επιλέγεις συχνότητα
3️⃣ Επιλέγεις ημέρα παραλαβής
4️⃣ Παίρνεις -10% ΠΑΝΤΑ!

✅ Υπενθύμιση 1 μέρα πριν
✅ Αλλαγή/ακύρωση ελεύθερα

Γράψε '1' για να ξεκινήσεις!"""

    return get_subscription_intro(customer)

def handle_subscription_product(msg, customer, session):
    """Handle subscription product"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)

    search_map = {
        '1': 'baby diapers pampers babylino',
        '2': 'adult diapers kera tena easypants',
        '3': 'pet easypet training',
        '4': 'wipes μαντηλάκια'
    }
    
    if msg in search_map:
        products = search_products(search_map[msg])
        products = [p for p in products if not is_discount_excluded(p)]
        
        if products:
            session['products'] = products[:10]
            session['state'] = 'product_list'
            session['after_product'] = 'subscription_frequency'
            return format_product_list(products[:10], "📦 Επέλεξε")
        return "Δεν βρέθηκαν."

    elif msg == '5':
        session['state'] = 'search'
        session['after_product'] = 'subscription_frequency'
        return "🔍 Γράψε προϊόν:"

    return "Επίλεξε 1-5"

def handle_subscription_frequency(msg, customer, session):
    """Handle subscription frequency"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)

    product = session.get('selected_product', {})

    if not session.get('sub_frequency_shown'):
        session['sub_frequency_shown'] = True
        return f"""📅 ΣΥΧΝΟΤΗΤΑ

{product.get('name', 'N/A')}

1️⃣ Εβδομάδα
2️⃣ 2 εβδομάδες ⭐
3️⃣ Μήνα

Επίλεξε 1-3"""

    freq_map = {
        '1': ('weekly', 7, 'Εβδομαδιαία'),
        '2': ('biweekly', 14, 'Κάθε 2 εβδομάδες'),
        '3': ('monthly', 30, 'Μηνιαία')
    }

    if msg in freq_map:
        session['sub_frequency'] = freq_map[msg]
        session['state'] = 'subscription_day'
        return """📆 ΗΜΕΡΑ

1️⃣ Δευτέρα
2️⃣ Τρίτη
3️⃣ Τετάρτη
4️⃣ Πέμπτη
5️⃣ Παρασκευή
6️⃣ Σάββατο

Επίλεξε 1-6"""

    return "Επίλεξε 1-3"

def handle_subscription_day(msg, customer, session):
    """Handle subscription day"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)

    if msg in PICKUP_DAYS:
        session['sub_day'] = PICKUP_DAYS[msg]
        session['state'] = 'subscription_confirm'
        
        product = session.get('selected_product', {})
        freq_name, freq_days, freq_text = session.get('sub_frequency', ('biweekly', 14, '2 εβδομάδες'))
        
        price = float(product.get('price', 0))
        discounted = price * 0.9
        
        return f"""✅ ΕΠΙΒΕΒΑΙΩΣΗ

📦 {product.get('name', 'N/A')}
💰 {price:.2f}€ → {discounted:.2f}€
📅 {freq_text}
📆 {session['sub_day']}

1️⃣ ✅ OK
2️⃣ ❌ Ακύρωση"""

    return "Επίλεξε 1-6"

def handle_subscription_confirm(msg, customer, session):
    """Handle subscription confirm"""
    if msg == '1':
        product = session.get('selected_product', {})
        freq_name, freq_days, freq_text = session.get('sub_frequency', ('biweekly', 14, '2 εβδομάδες'))
        
        subscription = {
            'id': hashlib.md5(f"{customer['phone']}{datetime.now()}".encode()).hexdigest()[:8],
            'product_id': product.get('id'),
            'product_name': product.get('name'),
            'price': float(product.get('price', 0)) * 0.9,
            'frequency': freq_name,
            'pickup_day': session.get('sub_day'),
            'next_pickup': calculate_next_pickup(session.get('sub_day')),
            'status': 'active'
        }
        
        customer['subscriptions'].append(subscription)
        logger.info(f"✅ Subscription: {subscription}")
        
        session['state'] = 'menu'
        store = get_customer_store(customer)
        
        return f"""🎉 ΕΝΕΡΓΗ!

📦 {product.get('name')}
💰 {subscription['price']:.2f}€ (-10%)
📅 {subscription['next_pickup']}

📍 {store['address']}

Γράψε 'menu'"""

    elif msg == '2':
        session['state'] = 'menu'
        return "Ακυρώθηκε.\n\nΓράψε 'menu'"

    return "Επίλεξε 1-2"

def calculate_next_pickup(day_name):
    """Calculate next pickup"""
    days = {'Δευτέρα': 0, 'Τρίτη': 1, 'Τετάρτη': 2, 'Πέμπτη': 3, 'Παρασκευή': 4, 'Σάββατο': 5}
    today = datetime.now()
    target_day = days.get(day_name, 0)
    days_ahead = target_day - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    next_date = today + timedelta(days=days_ahead)
    return next_date.strftime('%d/%m/%Y')

# ============================================
# ACCOUNT & SERVICE
# ============================================
def get_account_info(customer):
    """Get account"""
    subs = customer.get('subscriptions', [])
    store = get_customer_store(customer)
    
    sub_text = "Καμία" if not subs else "\n".join([f"• {s['product_name']}" for s in subs[:3]])
    
    return f"""👤 ΛΟΓΑΡΙΑΣΜΟΣ

📦 Συνδρομές: {len(subs)}
{sub_text}

🏪 Κατάστημα: {store['short_name']}

1️⃣ Διαχείριση
2️⃣ Αλλαγή καταστήματος

('menu')"""

def handle_my_account(msg, customer, session):
    """Handle account"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)
    
    if msg == '1':
        session['state'] = 'subscription'
        return get_subscription_intro(customer)
    elif msg == '2':
        session['state'] = 'store_selection'
        return get_store_selection_menu()
    
    return "Επίλεξε 1-2"

def get_customer_service_menu():
    """Get customer service"""
    return f"""📞 ΕΞΥΠΗΡΕΤΗΣΗ

1️⃣ 🤖 AI Βοηθός
2️⃣ 🆘 Παράπονο
3️⃣ 🎯 Αίτημα Προϊόντος
4️⃣ ⭐ Αξιολόγηση
5️⃣ 📞 Τηλέφωνο

📞 210 680 0549

Επίλεξε 1-5"""

def handle_customer_service(msg, customer, session):
    """Handle customer service"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)

    if msg == '1':
        if claude_client:
            session['ai_mode'] = True
            return "🤖 AI ενεργοποιήθηκε!"
        return "AI δεν είναι διαθέσιμο."
    elif msg == '2':
        session['state'] = 'complaint_form'
        session['complaint_step'] = 'type'
        return "🆘 ΠΑΡΑΠΟΝΟ\n\n1️⃣ Προϊόν\n2️⃣ Παραλαβή\n3️⃣ Άλλο"
    elif msg == '3':
        session['state'] = 'product_request'
        return "🎯 Γράψε το προϊόν:"
    elif msg == '4':
        session['state'] = 'feedback'
        return "⭐ 1-5 αστέρια;"
    elif msg == '5':
        return "📞 210 680 0549\n\nΓράψε 'menu'"

    return "Επίλεξε 1-5"

def handle_complaint_form(msg, customer, session):
    """Handle complaint with email notification"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)

    step = session.get('complaint_step', 'type')

    if step == 'type':
        types = {'1': 'Προϊόν', '2': 'Παραλαβή', '3': 'Άλλο'}
        if msg in types:
            session['complaint_type'] = types[msg]
            session['complaint_step'] = 'description'
            return "Περιέγραψε το πρόβλημα:"
        return "Επίλεξε 1-3"

    elif step == 'description':
        complaint_type = session.get('complaint_type', 'Γενικό')
        customer_phone = customer.get('phone', 'N/A')
        store = get_customer_store(customer)
        
        # Log complaint
        logger.info(f"📢 COMPLAINT: {complaint_type} - {msg} - {customer_phone}")
        
        # Send email to support
        email_subject = f"📢 Παράπονο Πελάτη - {complaint_type}"
        email_html = f"""
        <h2>📢 Νέο Παράπονο Πελάτη</h2>
        <hr>
        <p><strong>Τύπος:</strong> {complaint_type}</p>
        <p><strong>Περιγραφή:</strong></p>
        <blockquote style="background:#f5f5f5;padding:10px;border-left:3px solid #e74c3c;">
            {msg}
        </blockquote>
        <p><strong>Πελάτης:</strong> {customer_phone}</p>
        <p><strong>Κατάστημα:</strong> {store['name']}</p>
        <p><strong>Ημερομηνία:</strong> {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
        <hr>
        <p>Παρακαλώ απαντήστε το συντομότερο δυνατό.</p>
        """
        
        send_email([EMAIL_CONFIG['store_emails']['support']], email_subject, email_html)
        
        session['state'] = 'menu'
        return "✅ ΚΑΤΑΧΩΡΗΘΗΚΕ!\n\nΘα επικοινωνήσουμε σύντομα.\n\nΓράψε 'menu'"

    return "Γράψε 'menu'"

def handle_product_request(msg, customer, session):
    """Handle product request"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)

    logger.info(f"PRODUCT REQUEST: {msg} - {customer['phone']}")
    session['state'] = 'menu'
    return "✅ ΚΑΤΑΧΩΡΗΘΗΚΕ!\n\nΓράψε 'menu'"

def handle_feedback(msg, customer, session):
    """Handle feedback"""
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return get_main_menu(customer)

    if msg in ['1', '2', '3', '4', '5']:
        logger.info(f"FEEDBACK: {msg}⭐ - {customer['phone']}")
        session['state'] = 'menu'
        return "✅ ΕΥΧΑΡΙΣΤΟΥΜΕ!\n\nΓράψε 'menu'"
    return "Επίλεξε 1-5"

# ============================================
# HELPERS
# ============================================
def get_help_message():
    """Get help"""
    return """❓ ΒΟΗΘΕΙΑ

• 'menu' - Μενού
• 'καταστήματα' - Επιλογή
• 'franchise' - Δικαιόχρηση
• 'wholesale' - Χονδρική

Γράψε 'menu'"""

def search_products(query):
    """Search products"""
    try:
        response = wcapi.get("products", params={"search": query, "per_page": 20})
        result = response.json()
        return result if isinstance(result, list) else []
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

def get_popular_products():
    """Get popular"""
    try:
        response = wcapi.get("products", params={"per_page": 20, "orderby": "popularity"})
        return response.json()
    except:
        return []

def get_sale_products():
    """Get sale"""
    try:
        response = wcapi.get("products", params={"per_page": 20, "on_sale": True})
        return response.json()
    except:
        return []

# ============================================
# ROUTES
# ============================================
@app.route("/health", methods=['GET'])
def health():
    """Health"""
    return {
        "status": "ok",
        "version": "3.4-MultiStore-Franchise-B2B",
        "stores": list(STORES.keys()),
        "ai_enabled": claude_client is not None
    }

@app.route("/", methods=['GET'])
def home():
    """Home"""
    store_list = "".join([f"<li>{s['name']}</li>" for s in STORES.values()])
    return f"""
    <h1>🏪 CARESTORES Bot v3.4</h1>
    <p>Status: <strong style="color:green;">Running</strong></p>
    <h2>🏪 Καταστήματα:</h2>
    <ul>{store_list}</ul>
    <h2>Features:</h2>
    <ul>
        <li>✅ Multi-Store Selection</li>
        <li>✅ Franchise Info</li>
        <li>✅ Wholesale/B2B Portal</li>
        <li>✅ Subscriptions -10%</li>
        <li>✅ Baby Formula (NO discount)</li>
        <li>✅ Pet Products</li>
    </ul>
    <h2>B2B:</h2>
    <p>easycaremarket.gr | b2b.easycaremarket.gr</p>
    """

@app.route("/api/stores", methods=['GET'])
def get_stores():
    """Get all stores"""
    return jsonify(STORES)

@app.route("/api/franchise", methods=['GET'])
def get_franchise():
    """Get franchise info"""
    return jsonify(FRANCHISE_INFO)

@app.route("/api/wholesale", methods=['GET'])
def get_wholesale():
    """Get wholesale info"""
    return jsonify(WHOLESALE_INFO)

@app.route("/api/send-reminders", methods=['POST'])
def send_reminders():
    """Send reminders"""
    api_key = request.headers.get('X-API-Key')
    if not hasattr(config, 'API_SECRET_KEY') or api_key != config.API_SECRET_KEY:
        return jsonify({"error": "Unauthorized"}), 401
    
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y')
    sent = 0
    
    for phone, customer in customers.items():
        store = get_customer_store(customer)
        for sub in customer.get('subscriptions', []):
            if sub.get('next_pickup') == tomorrow and sub.get('status') == 'active':
                try:
                    twilio_client.messages.create(
                        body=f"⏰ Αύριο: {sub['product_name']} - {sub['price']:.2f}€\n📍 {store['address']}",
                        from_=config.TWILIO_WHATSAPP_NUMBER,
                        to=phone
                    )
                    sent += 1
                except Exception as e:
                    logger.error(f"Reminder error: {e}")
    
    return jsonify({"sent": sent})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=getattr(config, 'DEVELOPMENT', False))
