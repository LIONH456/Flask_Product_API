from flask import Flask, render_template, session, redirect, url_for, request
import requests
from datetime import datetime

TELEGRAM_API = "https://api.telegram.org/bot7844343757:AAEXyswSudN9N2VHTVVDMe-pYbrC5g0uJTU/sendMessage"
CHAT_ID = "977184900"  # Your Telegram chat ID or channel username

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure key in production


# Home page: show all products
@app.route('/')
def index():
    res = requests.get('https://fakestoreapi.com/products')
    products = res.json()
    return render_template('index.html', products=products)


# Product detail view
@app.route('/product/<int:id>')
def product(id):
    res = requests.get(f'https://fakestoreapi.com/products/{id}')
    product = res.json()
    return render_template('product.html', product=product)


# Add to cart
@app.route('/add-to-cart/<int:id>')
def add_to_cart(id):
    qty = int(request.args.get('qty', 1))
    cart = session.get('cart', {})

    if not isinstance(cart, dict):
        cart = {}

    id = str(id)  # session keys must be strings
    if id in cart:
        cart[id] += qty
    else:
        cart[id] = qty

    session['cart'] = cart
    return '', 204  # Empty response for JavaScript fetch


# View cart
@app.route('/cart')
def cart():
    cart_data = session.get('cart', {})
    if not isinstance(cart_data, dict):
        cart_data = {}

    items = []
    total = 0

    for id, qty in cart_data.items():
        res = requests.get(f'https://fakestoreapi.com/products/{id}')
        item = res.json()
        item['qty'] = qty
        item['subtotal'] = item['price'] * qty
        total += item['subtotal']
        items.append(item)

    return render_template('cart.html', items=items, total=total)


# Update or remove cart items
# @app.route('/update-cart', methods=['POST'])
# def update_cart():
#     cart = session.get('cart', {})
#     if not isinstance(cart, dict):
#         cart = {}
#
#     for key, value in request.form.items():
#         if key.startswith('qty_'):
#             id = key.replace('qty_', '')
#             try:
#                 cart[id] = max(1, int(value))  # Prevent zero or negative quantity
#             except ValueError:
#                 continue
#         elif key == 'remove':
#             cart.pop(value, None)
#
#     session['cart'] = cart
#     return redirect(url_for('cart'))

@app.route('/update-cart-item/<int:id>')
def update_cart_item(id):
    qty = int(request.args.get('qty', 1))
    cart = session.get('cart', {})
    cart[str(id)] = qty
    session['cart'] = cart

    # Recalculate subtotal and total
    res = requests.get(f'https://fakestoreapi.com/products/{id}')
    item = res.json()
    subtotal = item['price'] * qty

    total = 0
    for pid, qty in cart.items():
        pres = requests.get(f'https://fakestoreapi.com/products/{pid}')
        total += pres.json()['price'] * qty

    return {"subtotal": subtotal, "total": total}


@app.route('/remove-cart-item/<int:id>')
def remove_cart_item(id):
    cart = session.get('cart', {})
    cart.pop(str(id), None)
    session['cart'] = cart

    total = 0
    for pid, qty in cart.items():
        res = requests.get(f'https://fakestoreapi.com/products/{pid}')
        total += res.json()['price'] * qty

    return {"total": total}


# Checkout page (GET + POST)
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        address = request.form['address']

        cart = session.get('cart', {})
        items = []
        total = 0

        for id_str, qty in cart.items():
            res = requests.get(f'https://fakestoreapi.com/products/{id_str}')
            if res.status_code != 200:
                continue
            product = res.json()
            subtotal = product['price'] * qty
            total += subtotal
            items.append((product['title'], product['price'], qty, subtotal))

        # 🕒 Add timestamp
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 📦 Create message for Telegram
        message_lines = [
            "🛍️ *New Order Received!*",
            f"🕒 Time: {now}",
            f"👤 Name: {name}",
            f"📧 Email: {email}",
            f"📦 Address: {address}",
            "",
            "🧾 *Order Details:*"
        ]

        for title, price, qty, subtotal in items:
            message_lines.append(f"• {title} x{qty} - ${subtotal:.2f}")

        message_lines.append("")
        message_lines.append(f"💰 *Total:* ${total:.2f}")

        telegram_message = "\n".join(message_lines)

        # 📲 Send message to Telegram
        payload = {
            'chat_id': CHAT_ID,
            'text': telegram_message,
            'parse_mode': 'Markdown'
        }

        try:
            telegram_response = requests.get(TELEGRAM_API, params=payload)
            if telegram_response.status_code == 200:
                print("✅ Message sent to Telegram.")
            else:
                print("❌ Failed to send message to Telegram:", telegram_response.text)
        except Exception as e:
            print("❌ Error sending to Telegram:", e)

        # 🧹 Clear the cart
        session.pop('cart', None)

        return render_template('checkout_success.html', name=name, email=email, address=address)

    return render_template('checkout.html')


# Run the app
if __name__ == '__main__':
    app.run(debug=True)
