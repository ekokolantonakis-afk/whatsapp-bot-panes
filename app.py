import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from woocommerce import API
import config
import logging
import re
from datetime import datetime

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

# Product categories mapping
CATEGORIES = {
        '1': {'name': '👶 Βρεφικές Πάνες', 'search': 'baby diapers πάνες μωρού'},
        '2': {'name': '👴 Πάνες Ενηλίκων', 'search': 'adult diapers πάνες ενηλίκων'},
        '3': {'name': '🧻 Χαρτικά', 'search': 'paper χαρτί toilet'},
        '4': {'name': '🧼 Απορρυπαντικά', 'search': 'detergent απορρυπαντικό καθαριστικό'},
        '5': {'name': '💊 Βιταμίνες', 'search': 'vitamins βιταμίνες'},
        '6': {'name': '💄 Καλλυντικά', 'search': 'cosmetics καλλυντικά'},
        '7': {'name': '🧽 Μαντηλάκια', 'search': 'wipes μαντηλάκια'},
        '8': {'name': '🩹 Sudocrem & Βρεφική Φροντίδα', 'search': 'sudocrem baby care κρέμα'}
}

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
elif session['state'] == 'services':
            response_text = handle_services_menu(incoming_msg, session)
elif session['state'] == 'customer_service':
            response_text = handle_customer_service(incoming_msg, session)
elif session['state'] == 'categories':
            response_text = handle_categories(incoming_msg, session)
elif session['state'] == 'complaint_form':
            response_text = handle_complaint_form(incoming_msg, session)
elif session['state'] == 'product_request':
            response_text = handle_product_request(incoming_msg, session)
elif session['state'] == 'feedback':
            response_text = handle_feedback(incoming_msg, session)
else:
            response_text = "Πληκτρολόγησε 'menu' για το μενού! 😊"

    msg.body(response_text)
    return str(resp)

def handle_welcome(msg, session):
        """Handle welcome state"""

    if msg.lower() in ['γεια', 'hello', 'hi', 'menu', 'start', 'γειά']:
                session['state'] = 'menu'
                return """🎉 Καλώς ήρθες στο PANES.GR!

        Το WhatsApp Bot σου για γρήγορες αγορές! 🛍️

        Τι θα ήθελες;

        1️⃣ Αναζήτηση Προϊόντος
        2️⃣ Δημοφιλή Προϊόντα
        3️⃣ Προσφορές 💰
        4️⃣ Υπηρεσίες & Προνόμια 🎁
        5️⃣ Εξυπηρέτηση Πελατών 📞
        6️⃣ Κατηγορίες Προϊόντων 📦

        Απάντησε με αριθμό (1-6)"""

    return "Γράψε 'menu' για να ξεκινήσουμε! 😊"

def handle_menu(msg, session):
        """Handle menu selection"""

    if msg == '1':
                session['state'] = 'search'
                return "🔍 Γράψε το όνομα του προϊόντος:\n\n(π.χ. 'pampers', 'πάνες', 'babylino', 'sudocrem')"

elif msg == '2':
            products = get_popular_products()
            if products:
                            session['state'] = 'product_list'
                            session['products'] = products
                            return format_product_list(products, "🔥 Δημοφιλή Προϊόντα")
                        return "Σφάλμα φόρτωσης προϊόντων. Δοκίμασε ξανά!"

elif msg == '3':
        products = get_sale_products()
        if products:
                        session['state'] = 'product_list'
                        session['products'] = products
                        return format_product_list(products, "💰 Προσφορές")
                    return "Δεν βρέθηκαν προσφορές αυτή τη στιγμή!"

elif msg == '4':
        session['state'] = 'services'
        return """🎁 ΥΠΗΡΕΣΙΕΣ & ΠΡΟΝΟΜΙΑ

        Απόλαυσε τα οφέλη του PANES.GR:

        1️⃣ 🎁 Προπαραγγελία -10% ΕΚΠΤΩΣΗ
        2️⃣ 🚗 Drive-Through Παραλαβή
        3️⃣ 🔁 Επαναλαμβανόμενες Παραγγελίες -5%
        4️⃣ ⏰ Έτοιμο σε 30 λεπτά!
        5️⃣ 📦 Προπαραγγελία Μη Διαθέσιμων
        6️⃣ 💬 Γρήγορη Παραγγελία WhatsApp

        Επίλεξε αριθμό (1-6) ή 'menu' για πίσω"""

elif msg == '5':
        session['state'] = 'customer_service'
        return """📞 ΕΞΥΠΗΡΕΤΗΣΗ ΠΕΛΑΤΩΝ

        Πώς μπορούμε να σε βοηθήσουμε;

        1️⃣ 💬 Chat με Υποστήριξη
        2️⃣ 🆘 Καταχώρηση Παραπόνου
        3️⃣ 🎯 Αίτημα Προϊόντος
        4️⃣ ⭐ Αξιολόγηση/Feedback
        5️⃣ 📞 Τηλεφωνική Επικοινωνία

        Τηλέφωνο: 210 680 0549

        Επίλεξε αριθμό (1-5) ή 'menu'"""

elif msg == '6':
        session['state'] = 'categories'
        return """📦 ΚΑΤΗΓΟΡΙΕΣ ΠΡΟΪΟΝΤΩΝ

        Επίλεξε κατηγορία:

        1️⃣ 👶 Βρεφικές Πάνες
        2️⃣ 👴 Πάνες Ενηλίκων
        3️⃣ 🧻 Χαρτικά
        4️⃣ 🧼 Απορρυπαντικά
        5️⃣ 💊 Βιταμίνες
        6️⃣ 💄 Καλλυντικά
        7️⃣ 🧽 Μαντηλάκια
        8️⃣ 🩹 Sudocrem & Βρεφική Φροντίδα

        Επίλεξε αριθμό (1-8) ή 'menu'"""

elif msg.lower() == 'menu':
        return handle_welcome('menu', session)

    return "Παρακαλώ επίλεξε 1-6\n(ή γράψε 'menu' για το μενού)"

def handle_services_menu(msg, session):
        """Handle services and benefits menu"""

    if msg.lower() == 'menu':
                session['state'] = 'menu'
                return handle_welcome('menu', session)

    if msg == '1':
                return """🎁 ΠΡΟΠΑΡΑΓΓΕΛΙΑ -10% ΕΚΠΤΩΣΗ!

                Προπαραγγείλε τώρα και κέρδισε:
                ✅ 10% έκπτωση σε όλα
                ✅ Εγγυημένη διαθεσιμότητα
                ✅ Προτεραιότητα στην παραλαβή
                ✅ Χωρίς ουρές

                📞 Κάλεσε: 210 680 0549
                💬 Ή παράγγειλε εδώ στο WhatsApp!

                Γράψε 'menu' για το μενού"""

elif msg == '2':
        return """🚗 DRIVE-THROUGH ΠΑΡΑΛΑΒΗ

        Μείνε στο αυτοκίνητό σου!

        ✅ Παραγγελία από το κινητό
        ✅ Έτοιμο σε 30 λεπτά
        ✅ Παραλαβή χωρίς να κατέβεις
        ✅ Ασφαλής & γρήγορη εξυπηρέτηση

        📍 Διεύθυνση: [Η διεύθυνσή σας]
        📞 Κάλεσε: 210 680 0549

        Γράψε 'menu' για το μενού"""

elif msg == '3':
        return """🔁 ΜΠΟΝΟΥΣ ΕΠΑΝΑΛΗΨΗΣ -5%!

        Παραγγέλνεις συχνά;
        Κέρδισε 5% έκπτωση!

        ✅ Σε κάθε επαναλαμβανόμενη παραγγελία
        ✅ Πάνες, μαντηλάκια, απορρυπαντικά
        ✅ Αυτόματη εφαρμογή έκπτωσης
        ✅ Δωρεάν παράδοση >50€

        📞 Ενεργοποίηση: 210 680 0549

        Γράψε 'menu' για το μενού"""

elif msg == '4':
        return """⏰ ΕΤΟΙΜΟ ΣΕ 30 ΛΕΠΤΑ!

        Βιάζεσαι; Εμείς όχι!

        ✅ Προετοιμασία σε 30 λεπτά
        ✅ Ειδοποίηση όταν είναι έτοιμο
        ✅ Express παραλαβή
        ✅ Χωρίς αναμονή

        📞 Παράγγειλε: 210 680 0549
        💬 WhatsApp: Στείλε μας λίστα!

        Γράψε 'menu' για το μενού"""

elif msg == '5':
        return """📦 ΠΡΟΠΑΡΑΓΓΕΛΙΑ ΜΗ ΔΙΑΘΕΣΙΜΩΝ

        Λείπει κάτι; Θα το φέρουμε!

        ✅ Παράγγειλε μη διαθέσιμα προϊόντα
        ✅ Ειδοποίηση όταν φτάσουν
        ✅ Κράτηση για εσένα
        ✅ Εγγυημένη διαθεσιμότητα

        📞 Αίτημα: 210 680 0549
        💬 Ή γράψε εδώ: Option 5 → Αίτημα

        Γράψε 'menu' για το μενού"""

elif msg == '6':
        return """💬 ΓΡΗΓΟΡΗ ΠΑΡΑΓΓΕΛΙΑ WHATSAPP

        Παράγγειλε σε 3 βήματα:

        1️⃣ Στείλε λίστα προϊόντων
        2️⃣ Επιβεβαίωση & τιμή
        3️⃣ Παραλαβή!

        ✅ Χωρίς τηλέφωνο
        ✅ Όλο το 24ωρο
        ✅ Γρήγορη απάντηση
        ✅ Εύκολο & άμεσο

        📞 Support: 210 680 0549

        Γράψε 'menu' για το μενού"""

    return "Επίλεξε 1-6 ή 'menu' για πίσω"

def handle_customer_service(msg, session):
        """Handle customer service menu"""

    if msg.lower() == 'menu':
                session['state'] = 'menu'
                return handle_welcome('menu', session)

    if msg == '1':
                return """💬 LIVE CHAT SUPPORT

                Είμαστε εδώ για εσένα!

                Στείλε το μήνυμά σου εδώ και θα σου απαντήσουμε το συντομότερο δυνατό.

                ⏰ Ώρες: 08:00-20:00
                📞 Τηλέφωνο: 210 680 0549

                Ή γράψε 'menu' για το μενού"""

elif msg == '2':
        session['state'] = 'complaint_form'
        session['complaint_step'] = 'name'
        return """🆘 ΚΑΤΑΧΩΡΗΣΗ ΠΑΡΑΠΟΝΟΥ

        Λυπούμαστε για την ταλαιπωρία!
        Θα το λύσουμε άμεσα.

        Παρακαλώ γράψε το όνομά σου:"""

elif msg == '3':
        session['state'] = 'product_request'
        session['request_step'] = 'product'
        return """🎯 ΑΙΤΗΜΑ ΠΡΟΪΟΝΤΟΣ

        Δεν βρίσκεις κάτι στο κατάστημα;
        Πες μας τι χρειάζεσαι!

        Γράψε το όνομα του προϊόντος:"""

elif msg == '4':
        session['state'] = 'feedback'
        session['feedback_step'] = 'rating'
        return """⭐ ΑΞΙΟΛΟΓΗΣΗ

        Η γνώμη σου μετράει!

        Πόσα αστέρια θα μας έδινες; (1-5)

        5⭐ Τέλειο
        4⭐ Πολύ καλό
        3⭐ Καλό
        2⭐ Μέτριο
        1⭐ Χρειάζεται βελτίωση

        Γράψε αριθμό 1-5:"""

elif msg == '5':
        return """📞 ΤΗΛΕΦΩΝΙΚΗ ΕΠΙΚΟΙΝΩΝΙΑ

        Κάλεσέ μας:
        📞 210 680 0549

        ⏰ Ώρες λειτουργίας:
        Δευτέρα-Παρασκευή: 08:00-20:00
        Σάββατο: 09:00-18:00
        Κυριακή: Κλειστά

        📍 Διεύθυνση: [Η διεύθυνσή σας]

        Γράψε 'menu' για το μενού"""

    return "Επίλεξε 1-5 ή 'menu' για πίσω"

def handle_categories(msg, session):
        """Handle product categories"""

    if msg.lower() == 'menu':
                session['state'] = 'menu'
                return handle_welcome('menu', session)

    if msg in CATEGORIES:
                category = CATEGORIES[msg]
                products = search_products(category['search'])
                if products:
                                session['state'] = 'product_list'
                                session['products'] = products
                                return format_product_list(products, category['name'])
                            return f"Δεν βρέθηκαν προϊόντα στην κατηγορία {category['name']} 😔"

    return "Επίλεξε 1-8 ή 'menu' για το μενού"

def handle_complaint_form(msg, session):
        """Handle complaint form submission"""

    if msg.lower() == 'menu':
                session['state'] = 'menu'
        return handle_welcome('menu', session)

    step = session.get('complaint_step', 'name')

    if step == 'name':
                session['complaint_name'] = msg
        session['complaint_step'] = 'issue'
        return "Ευχαριστούμε! Τώρα περίγραψε το πρόβλημα:"

elif step == 'issue':
        complaint_name = session.get('complaint_name', 'Άγνωστος')
        complaint_text = msg

        # Log the complaint
        logger.info(f"COMPLAINT from {complaint_name}: {complaint_text}")

        session['state'] = 'menu'
        return f"""✅ ΠΑΡΑΠΟΝΟ ΚΑΤΑΧΩΡΗΘΗΚΕ!

        Όνομα: {complaint_name}
        Αρ. Αναφοράς: #{datetime.now().strftime('%Y%m%d%H%M')}

        Θα επικοινωνήσουμε μαζί σου το συντομότερο!

        📞 210 680 0549

        Γράψε 'menu' για το μενού"""

def handle_product_request(msg, session):
        """Handle product request"""

    if msg.lower() == 'menu':
                session['state'] = 'menu'
                return handle_welcome('menu', session)

    step = session.get('request_step', 'product')

    if step == 'product':
                session['requested_product'] = msg
                session['request_step'] = 'quantity'
                return "Πόσα κομμάτια θέλεις;"

elif step == 'quantity':
        product = session.get('requested_product', 'Άγνωστο')
        quantity = msg

        # Log the request
        logger.info(f"PRODUCT REQUEST: {product} x{quantity}")

        session['state'] = 'menu'
        return f"""✅ ΑΙΤΗΜΑ ΚΑΤΑΧΩΡΗΘΗΚΕ!

        Προϊόν: {product}
        Ποσότητα: {quantity}
        Αρ. Αιτήματος: #{datetime.now().strftime('%Y%m%d%H%M')}

        Θα σε ενημερώσουμε όταν διατίθεται!

        📞 210 680 0549

        Γράψε 'menu' για το μενού"""

def handle_feedback(msg, session):
        """Handle customer feedback"""

    if msg.lower() == 'menu':
                session['state'] = 'menu'
                return handle_welcome('menu', session)

    step = session.get('feedback_step', 'rating')

    if step == 'rating':
                if msg in ['1', '2', '3', '4', '5']:
                                session['rating'] = msg
                                session['feedback_step'] = 'comment'
                                stars = '⭐' * int(msg)
                                return f"""{stars}

                    Ευχαριστούμε! Θέλεις να μας πεις κάτι;
                    (Γράψε σχόλιο ή 'skip' για παράλειψη)"""
                            return "Παρακαλώ γράψε αριθμό 1-5"

elif step == 'comment':
        rating = session.get('rating', '5')
        comment = msg if msg.lower() != 'skip' else 'Χωρίς σχόλιο'

        # Log feedback
        logger.info(f"FEEDBACK: {rating}⭐ - {comment}")

        session['state'] = 'menu'
        return f"""✅ ΕΥΧΑΡΙΣΤΟΥΜΕ!

        Αξιολόγηση: {rating}⭐
        Σχόλιο: {comment}

        Η γνώμη σου μας βοηθά να βελτιωνόμαστε!

        📞 210 680 0549

        Γράψε 'menu' για το μενού"""

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
        return format_product_list(products, f"🔍 Αποτελέσματα για '{msg}'")

    return f"""Δεν βρέθηκαν προϊόντα για '{msg}' 😔

    💡 Δοκίμασε:
    • Άλλες λέξεις
    • Κατηγορίες (menu → 6)
    • Δημοφιλή (menu → 2)

    Ή γράψε 'menu' για το μενού"""

def handle_product_selection(msg, session):
        """Handle product selection from list"""

    if msg.lower() == 'menu':
                session['state'] = 'menu'
        return handle_welcome('menu', session)

    # Check for pagination commands
    if msg.lower() == 'more' or msg.lower() == 'περισσότερα':
                page = session.get('current_page', 1) + 1
        session['current_page'] = page
        products = session.get('all_products', [])
        if products:
                        return format_product_list(products, session.get('list_title', 'Προϊόντα'), page)

    try:
                index = int(msg) - 1
        products = session.get('products', [])
        page = session.get('current_page', 1)

        # Adjust index for current page
        adjusted_index = (page - 1) * 10 + index

        if 0 <= adjusted_index < len(products):
                        product = products[adjusted_index]
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
                    "per_page": 20  # Increased from 5 to 20
    })
        result = response.json()
        logger.info(f"Search '{query}': {len(result) if isinstance(result, list) else 0} products")
        return result
except Exception as e:
        logger.error(f"Search error: {e}")
        return []

def get_popular_products():
        """Get popular products"""

    try:
                response = wcapi.get("products", params={
                    "per_page": 20,  # Increased from 5 to 20
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
                    "per_page": 20,  # Increased from 5 to 20
                    "on_sale": True
    })
        return response.json()
except Exception as e:
        logger.error(f"Error fetching sale products: {e}")
        return []

def format_product_list(products, title, page=1):
        """Format product list for display with pagination"""

    if not products:
                return "Δεν βρέθηκαν προϊόντα 😔"

    # Pagination: show 10 products per page
    per_page = 10
    start = (page - 1) * per_page
    end = start + per_page
    page_products = products[start:end]

    if not page_products:
                return "Δεν υπάρχουν άλλα προϊόντα."

    text = f"📦 {title}\n"
    if len(products) > per_page:
                text += f"(Σελίδα {page}/{(len(products)-1)//per_page + 1})\n"
    text += "\n"

    for i, product in enumerate(page_products, start + 1):
                name = product.get('name', 'N/A')
        price = product.get('price', '0')
        stock = product.get('stock_status', 'outofstock')
        stock_emoji = "✅" if stock == "instock" else "❌"

        text += f"{i}. {name}\n"
        text += f"   💰 {price}€ {stock_emoji}\n\n"

    text += "Γράψε αριθμό για λεπτομέρειες\n"

    # Show "more" option if there are more products
    if end < len(products):
                text += "\n💡 Γράψε 'more' για περισσότερα\n"

    text += "(ή 'menu' για το μενού)"

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
    text += f"📊 Απόθεμα: {'Διαθέσιμο ✅' if stock == 'instock' else 'Μη Διαθέσιμο ❌'}\n"

    if sku:
                text += f"🔖 Κωδικός: {sku}\n"

    if description:
                desc_short = description[:150]
        text += f"\n📝 {desc_short}...\n"

    text += "\n🎁 ΠΡΟΝΟΜΙΑ:"
    text += "\n• Προπαραγγελία -10%"
    text += "\n• Drive-Through διαθέσιμο"
    text += "\n• Έτοιμο σε 30 λεπτά"
    text += "\n\n📞 Παραγγελία: 210 680 0549"
    text += "\n💬 WhatsApp: Γράψε 'παραγγελία'"
    text += "\n\n(Γράψε 'menu' για το μενού)"

    return text

@app.route("/health", methods=['GET'])
def health():
        """Health check endpoint"""
    return {"status": "ok", "message": "WhatsApp Bot Running!", "version": "2.0-Enhanced"}

@app.route("/", methods=['GET'])
def home():
        """Home page"""
    return """
        <h1>🤖 WhatsApp Bot - PANES.GR v2.0</h1>
            <p>Status: <strong style="color: green;">Running</strong></p>
                <p>Version: <strong>2.0 Enhanced</strong></p>
                    <h2>Features:</h2>
                        <ul>
                                <li>✅ Product Search (20+ results)</li>
                                        <li>✅ Popular Products</li>
                                                <li>✅ Special Offers</li>
                                                        <li>✅ Services & Benefits</li>
                                                                <li>✅ Customer Support</li>
                                                                        <li>✅ Product Categories</li>
                                                                                <li>✅ Complaint Forms</li>
                                                                                        <li>✅ Product Requests</li>
                                                                                                <li>✅ Customer Feedback</li>
                                                                                                    </ul>
                                                                                                        <p>Webhook: <code>/webhook</code></p>
                                                                                                            <p>Health: <code>/health</code></p>
                                                                                                                <p>Phone: <strong>210 680 0549</strong></p>
                                                                                                                    """

if __name__ == "__main__":
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=config.DEVELOPMENT)
