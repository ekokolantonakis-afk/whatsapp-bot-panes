import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from woocommerce import API
import config
import logging
import re

app = Flask(__name__)

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

# Simple in-memory session storage
sessions = {}

@app.route("/webhook", methods=['POST'])
def webhook():
    """Handle incoming WhatsApp messages"""
    
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')
    
    logger.info(f"Received from {from_number}: {incoming_msg}")
    
    # Create response
    resp = MessagingResponse()
    msg = resp.message()
    
    # Get or create session
    if from_number not in sessions:
        sessions[from_number] = {'state': 'welcome'}
    
    session = sessions[from_number]
    
    # Route to appropriate handler
    if session['state'] == 'welcome':
        response_text = handle_welcome(incoming_msg, session)
    elif session['state'] == 'menu':
        response_text = handle_menu(incoming_msg, session)
    elif session['state'] == 'search':
        response_text = handle_search(incoming_msg, session)
    elif session['state'] == 'product_list':
        response_text = handle_product_selection(incoming_msg, session)
    else:
        response_text = "Πληκτρολόγησε 'menu' για το μενού! 😊"
    
    msg.body(response_text)
    return str(resp)

def handle_welcome(msg, session):
    """Handle welcome state"""
    
    if msg.lower() in ['γεια', 'hello', 'hi', 'menu', 'start', 'γειά']:
        session['state'] = 'menu'
        return """🎉 Καλώς ήρθες στο PANES.GR!

Τι θα ήθελες;

1️⃣ Αναζήτηση προϊόντος
2️⃣ Δημοφιλή προϊόντα
3️⃣ Προσφορές

Απάντησε με αριθμό (1, 2 ή 3)"""
    
    return "Γράψε 'menu' για να ξεκινήσουμε! 😊"

def handle_menu(msg, session):
    """Handle menu selection"""
    
    if msg == '1':
        session['state'] = 'search'
        return "🔍 Γράψε το όνομα του προϊόντος:\n\n(π.χ. 'pampers', 'πάνες', 'babylino')"
    
    elif msg == '2':
        products = get_popular_products()
        if products:
            session['state'] = 'product_list'
            session['products'] = products
            return format_product_list(products, "Δημοφιλή Προϊόντα")
        return "Σφάλμα φόρτωσης προϊόντων. Δοκίμασε ξανά!"
    
    elif msg == '3':
        products = get_sale_products()
        if products:
            session['state'] = 'product_list'
            session['products'] = products
            return format_product_list(products, "Προσφορές")
        return "Δεν βρέθηκαν προσφορές αυτή τη στιγμή!"
    
    elif msg.lower() == 'menu':
        return handle_welcome('menu', session)
    
    return "Παρακαλώ επίλεξε 1, 2 ή 3\n(ή γράψε 'menu' για το μενού)"

def handle_search(msg, session):
    """Handle product search"""
    
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return handle_welcome('menu', session)
    
    # Search products
    products = search_products(msg)
    
    if products:
        session['state'] = 'product_list'
        session['products'] = products
        return format_product_list(products, f"Αποτελέσματα για '{msg}'")
    
    return f"Δεν βρέθηκαν προϊόντα για '{msg}' 😔\n\nΔοκίμασε:\n• Άλλες λέξεις\n• Ή γράψε 'menu' για το μενού"

def handle_product_selection(msg, session):
    """Handle product selection from list"""
    
    if msg.lower() == 'menu':
        session['state'] = 'menu'
        return handle_welcome('menu', session)
    
    try:
        index = int(msg) - 1
        products = session.get('products', [])
        
        if 0 <= index < len(products):
            product = products[index]
            return format_product_details(product)
        else:
            return "Μη έγκυρη επιλογή!\n\nΔιάλεξε αριθμό από τη λίστα\n(ή γράψε 'menu' για το μενού)"
    except ValueError:
        return "Παρακαλώ στείλε έναν αριθμό!\n(ή γράψε 'menu' για το μενού)"

def search_products(query):
    """Search products by keyword"""
    
    try:
        response = wcapi.get("products", params={
            "search": query,
            "per_page": 5
        })
                result = response.json()
                logger.info(f"Search query: {query}")
                logger.info(f"API status: {response.status_code}")
                logger.info(f"Result type: {type(result)}")
                logger.info(f"Result length: {len(result) if isinstance(result, list) else 'N/A'}")
                logger.info(f"Result: {result}")
        return result    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

def get_popular_products():
    """Get popular products"""
    
    try:
        response = wcapi.get("products", params={
            "per_page": 5,
            "orderby": "popularity"
        })
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        return []

def get_sale_products():
    """Get products on sale"""
    
    try:
        response = wcapi.get("products", params={
            "per_page": 5,
            "on_sale": True
        })
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching sale products: {e}")
        return []

def format_product_list(products, title):
    """Format product list for display"""
    
    if not products:
        return "Δεν βρέθηκαν προϊόντα 😔"
    
    text = f"📦 {title}\n\n"
    
    for i, product in enumerate(products[:5], 1):
        name = product.get('name', 'N/A')
        price = product.get('price', '0')
        stock = product.get('stock_status', 'outofstock')
        stock_emoji = "✅" if stock == "instock" else "❌"
        
        text += f"{i}. {name}\n"
        text += f"   💰 {price}€ {stock_emoji}\n\n"
    
    text += "Γράψε αριθμό για λεπτομέρειες\n(ή 'menu' για το μενού)"
    
    return text

def format_product_details(product):
    """Format detailed product information"""
    
    name = product.get('name', 'N/A')
    price = product.get('price', '0')
    description = product.get('short_description', '')
    stock = product.get('stock_status', 'outofstock')
    sku = product.get('sku', '')
    
    # Remove HTML tags
    description = re.sub('<[^<]+?>', '', description)
    
    text = f"📦 {name}\n\n"
    text += f"💰 Τιμή: {price}€\n"
    text += f"📊 Απόθεμα: {'Διαθέσιμο ✅' if stock == 'instock' else 'Εξαντλημένο ❌'}\n"
    
    if sku:
        text += f"🔖 Κωδικός: {sku}\n"
    
    if description:
        desc_short = description[:150]
        text += f"\n📝 {desc_short}...\n"
    
    text += "\n📞 Παραγγελία: 210 680 0549"
    text += "\n\n(Γράψε 'menu' για το μενού)"
    
    return text

@app.route("/health", methods=['GET'])
def health():
    """Health check endpoint"""
    return {"status": "ok", "message": "WhatsApp Bot Running!", "version": "1.0"}

@app.route("/", methods=['GET'])
def home():
    """Home page"""
    return """
    <h1>🤖 WhatsApp Bot - PANES.GR</h1>
    <p>Status: <strong style="color: green;">Running</strong></p>
    <p>Webhook: <code>/webhook</code></p>
    <p>Health: <code>/health</code></p>
    <p>Phone: <strong>210 680 0549</strong></p>
    """

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=config.DEVELOPMENT)
