import os
import uuid
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename

from config import Config
from database import get_db, init_db
from auth import (
    hash_password, verify_password, get_current_user,
    is_owner, owner_required, login_required,
    check_rate_limit, record_failed_attempt, reset_failed_attempts,
    validate_password_strength
)
from seed_data import seed_all

app = Flask(__name__)
app.config.from_object(Config)

# Ensure required upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PAYMENTS_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PRODUCTS_UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def validate_image_bytes(stream):
    """
    Reads initial binary signature to verify magic bytes for PNG, JPEG, WEBP, GIF.
    Resets stream position to 0 after reading.
    """
    header = stream.read(32)
    stream.seek(0)
    if not header:
        return False, "Empty file uploaded."
    if header.startswith(b'\x89PNG\r\n\x1a\n'):
        return True, "image/png"
    if header.startswith(b'\xff\xd8\xff'):
        return True, "image/jpeg"
    if header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
        return True, "image/gif"
    if header.startswith(b'RIFF') and len(header) >= 12 and header[8:12] == b'WEBP':
        return True, "image/webp"
    return False, "Invalid image format. File content must be a genuine PNG, JPG, WEBP, or GIF image."

# ==========================================
# PAGE ROUTES
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/my-orders')
def my_orders_page():
    return render_template('orders.html')

@app.route('/owner/login')
def owner_login_page():
    if is_owner():
        return redirect(url_for('owner_dashboard_page'))
    return render_template('owner_login.html')

@app.route('/owner/dashboard')
@owner_required
def owner_dashboard_page():
    return render_template('owner_dashboard.html')

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # Security: Strictly disallow public direct access to payment proofs
    clean_name = os.path.basename(filename)
    if clean_name.startswith('payment_') or 'payments' in filename:
        return jsonify({'error': 'Forbidden: Direct access to payment screenshots is restricted.', 'status': 403}), 403

    # Check products folder first, then root uploads
    prod_path = os.path.join(app.config['PRODUCTS_UPLOAD_FOLDER'], clean_name)
    if os.path.exists(prod_path):
        return send_from_directory(app.config['PRODUCTS_UPLOAD_FOLDER'], clean_name)
    return send_from_directory(app.config['UPLOAD_FOLDER'], clean_name)

# ==========================================
# AUTHENTICATION APIS (WITH RATE LIMITING)
# ==========================================
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    full_name = data.get('full_name', '').strip()
    phone = data.get('phone', '').strip()
    address = data.get('address', '').strip()

    if not username or not password or not full_name:
        return jsonify({'error': 'Full name, username/phone, and password are required.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'An account with this username/phone already exists.'}), 400

    pw_hash = hash_password(password)
    cursor.execute("""
        INSERT INTO users (username, password_hash, role, full_name, phone, address)
        VALUES (?, ?, 'customer', ?, ?, ?)
    """, (username, pw_hash, full_name, phone, address))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    session['user_id'] = user_id
    session['role'] = 'customer'
    session['username'] = username
    session['full_name'] = full_name

    return jsonify({
        'message': 'Registration successful!',
        'user': {'id': user_id, 'username': username, 'full_name': full_name, 'phone': phone, 'address': address, 'role': 'customer'}
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    ip = request.remote_addr or '127.0.0.1'
    allowed, retry_after = check_rate_limit(ip, scope='customer_login')
    if not allowed:
        return jsonify({
            'error': f'Too many failed login attempts. Please wait {retry_after} seconds before trying again.'
        }), 429

    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'error': 'Username and password are required.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash, role, full_name, phone, address FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if not user or not verify_password(password, user['password_hash']):
        record_failed_attempt(ip, scope='customer_login')
        return jsonify({'error': 'Invalid username or password.'}), 401

    # Reset failed attempts upon successful authentication
    reset_failed_attempts(ip, scope='customer_login')

    session['user_id'] = user['id']
    session['role'] = user['role']
    session['username'] = user['username']
    session['full_name'] = user['full_name']

    return jsonify({
        'message': 'Login successful!',
        'user': {
            'id': user['id'],
            'username': user['username'],
            'full_name': user['full_name'],
            'phone': user['phone'],
            'address': user['address'],
            'role': user['role']
        }
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully.'})

@app.route('/api/auth/me', methods=['GET'])
def get_me():
    user = get_current_user()
    if user:
        return jsonify({'logged_in': True, 'user': user})
    return jsonify({'logged_in': False, 'user': None})

# ==========================================
# PUBLIC STORE & CATALOG APIS
# ==========================================
@app.route('/api/settings', methods=['GET'])
def get_public_settings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT delivery_charge, min_order_amount, free_delivery_threshold, home_delivery_enabled, store_pickup_enabled, upi_qr_url FROM store_settings WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({
        'delivery_charge': 30.0,
        'min_order_amount': 100.0,
        'free_delivery_threshold': 500.0,
        'home_delivery_enabled': 1,
        'store_pickup_enabled': 1,
        'upi_qr_url': ''
    })

@app.route('/api/categories', methods=['GET'])
def get_categories():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM products WHERE is_active = 1 ORDER BY category")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([r['category'] for r in rows])

@app.route('/api/products', methods=['GET'])
def get_products():
    category = request.args.get('category', '').strip()
    search = request.args.get('search', '').strip()

    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM products WHERE is_active = 1"
    params = []

    if category and category.lower() != 'all':
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND (name_en LIKE ? OR name_hi LIKE ? OR description_en LIKE ? OR description_hi LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])

    query += " ORDER BY category, name_en"
    cursor.execute(query, params)
    products = [dict(row) for row in cursor.fetchall()]

    for p in products:
        cursor.execute("""
            SELECT id, unit_name_en, unit_name_hi, multiplier
            FROM product_units
            WHERE product_id = ?
            ORDER BY multiplier ASC
        """, (p['id'],))
        units = []
        for u in cursor.fetchall():
            price = round(p['base_price'] * u['multiplier'], 2)
            units.append({
                'id': u['id'],
                'unit_name_en': u['unit_name_en'],
                'unit_name_hi': u['unit_name_hi'],
                'multiplier': u['multiplier'],
                'calculated_price': price
            })
        p['units'] = units
        p['in_stock'] = p['stock'] > 0

    conn.close()
    return jsonify(products)

# ==========================================
# CUSTOMER ORDER APIS
# ==========================================
@app.route('/api/orders', methods=['POST'])
def place_order():
    data = request.get_json() or {}
    items = data.get('items', [])
    customer_name = data.get('customer_name', '').strip()
    customer_phone = data.get('customer_phone', '').strip()
    delivery_type = data.get('delivery_type', 'HOME_DELIVERY').upper()
    delivery_address = data.get('delivery_address', '').strip()
    special_instructions = data.get('special_instructions', '').strip()
    payment_method = data.get('payment_method', 'ONLINE_UPI').upper()

    if not items:
        return jsonify({'error': 'Cart is empty. Please add items before placing order.'}), 400

    if not customer_name or not customer_phone:
        return jsonify({'error': 'Customer name and phone number are required.'}), 400

    if delivery_type not in ('HOME_DELIVERY', 'STORE_PICKUP'):
        return jsonify({'error': 'Invalid delivery type.'}), 400

    if delivery_type == 'HOME_DELIVERY' and not delivery_address:
        return jsonify({'error': 'Delivery address is required for Home Delivery.'}), 400

    if payment_method not in ('ONLINE_UPI', 'COD', 'PAY_AT_STORE'):
        return jsonify({'error': 'Invalid payment method.'}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM store_settings WHERE id = 1")
    settings = cursor.fetchone()
    if not settings:
        conn.close()
        return jsonify({'error': 'Store settings unavailable.'}), 500

    if delivery_type == 'HOME_DELIVERY' and not settings['home_delivery_enabled']:
        conn.close()
        return jsonify({'error': 'Home delivery is currently disabled by store owner.'}), 400

    if delivery_type == 'STORE_PICKUP' and not settings['store_pickup_enabled']:
        conn.close()
        return jsonify({'error': 'Store pickup is currently disabled by store owner.'}), 400

    subtotal = 0.0
    validated_items = []

    for it in items:
        prod_id = it.get('product_id')
        unit_id = it.get('unit_id')
        qty = int(it.get('quantity', 1))

        if qty <= 0:
            continue

        cursor.execute("SELECT * FROM products WHERE id = ? AND is_active = 1", (prod_id,))
        prod = cursor.fetchone()
        if not prod:
            conn.close()
            return jsonify({'error': f'Product with ID {prod_id} is no longer available.'}), 400

        cursor.execute("SELECT * FROM product_units WHERE id = ? AND product_id = ?", (unit_id, prod_id))
        unit = cursor.fetchone()
        if not unit:
            conn.close()
            return jsonify({'error': f'Invalid unit for product {prod["name_en"]}.'}), 400

        unit_price = round(prod['base_price'] * unit['multiplier'], 2)
        item_total = round(unit_price * qty, 2)
        base_deduction = round(unit['multiplier'] * qty, 3)

        if prod['stock'] < base_deduction:
            conn.close()
            return jsonify({
                'error': f'Insufficient stock for {prod["name_en"]}. Available: {prod["stock"]} {prod["base_unit"]}, Ordered: {base_deduction} {prod["base_unit"]}.'
            }), 400

        subtotal += item_total
        validated_items.append({
            'product_id': prod['id'],
            'product_name_en': prod['name_en'],
            'product_name_hi': prod['name_hi'],
            'unit_name_en': unit['unit_name_en'],
            'unit_name_hi': unit['unit_name_hi'],
            'multiplier': unit['multiplier'],
            'quantity': qty,
            'unit_price': unit_price,
            'item_total': item_total,
            'base_deduction_qty': base_deduction
        })

    if not validated_items:
        conn.close()
        return jsonify({'error': 'No valid items found in order.'}), 400

    if subtotal < settings['min_order_amount']:
        conn.close()
        return jsonify({
            'error': f'Minimum order amount is ₹{settings["min_order_amount"]:.2f}. Your items total is ₹{subtotal:.2f}.'
        }), 400

    delivery_charge = 0.0
    if delivery_type == 'HOME_DELIVERY':
        if subtotal < settings['free_delivery_threshold']:
            delivery_charge = float(settings['delivery_charge'])
        else:
            delivery_charge = 0.0

    total_amount = round(subtotal + delivery_charge, 2)
    order_number = f"YGS-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    customer_id = session.get('user_id')
    guest_token = str(uuid.uuid4()) if not customer_id else None

    # Stock is NOT deducted upon order placement (Stock Safety)
    cursor.execute("""
        INSERT INTO orders (
            order_number, customer_id, customer_name, customer_phone,
            delivery_type, delivery_address, special_instructions,
            subtotal, delivery_charge, total_amount, payment_method,
            status, stock_deducted, guest_token
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_OWNER_APPROVAL', 0, ?)
    """, (
        order_number, customer_id, customer_name, customer_phone,
        delivery_type, delivery_address, special_instructions,
        subtotal, delivery_charge, total_amount, payment_method,
        guest_token
    ))
    order_id = cursor.lastrowid

    for vi in validated_items:
        cursor.execute("""
            INSERT INTO order_items (
                order_id, product_id, product_name_en, product_name_hi,
                unit_name_en, unit_name_hi, multiplier, quantity,
                unit_price, item_total, base_deduction_qty
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id, vi['product_id'], vi['product_name_en'], vi['product_name_hi'],
            vi['unit_name_en'], vi['unit_name_hi'], vi['multiplier'], vi['quantity'],
            vi['unit_price'], vi['item_total'], vi['base_deduction_qty']
        ))

    cursor.execute("""
        INSERT INTO notifications (user_id, order_id, message_en, message_hi)
        VALUES (?, ?, ?, ?)
    """, (
        customer_id, order_id,
        f"Order #{order_number} placed successfully. Awaiting store owner approval.",
        f"ऑर्डर #{order_number} सफलतापूर्वक दर्ज हुआ। दुकानदार की स्वीकृति की प्रतीक्षा है।"
    ))

    conn.commit()
    conn.close()

    if guest_token:
        if 'guest_tokens' not in session:
            session['guest_tokens'] = []
        session['guest_tokens'].append(guest_token)
        session.modified = True

    return jsonify({
        'message': 'Order placed successfully! Awaiting owner approval.',
        'order_id': order_id,
        'order_number': order_number,
        'status': 'PENDING_OWNER_APPROVAL',
        'total_amount': total_amount,
        'guest_token': guest_token
    }), 201

@app.route('/api/my-orders', methods=['GET'])
def get_my_orders():
    user_id = session.get('user_id')
    guest_tokens = session.get('guest_tokens', [])
    token_param = request.args.get('token', '').strip()
    if token_param and token_param not in guest_tokens:
        guest_tokens.append(token_param)

    if not user_id and not guest_tokens:
        return jsonify([])

    conn = get_db()
    cursor = conn.cursor()

    conditions = []
    params = []
    if user_id:
        conditions.append("customer_id = ?")
        params.append(user_id)
    if guest_tokens:
        placeholders = ','.join(['?'] * len(guest_tokens))
        conditions.append(f"guest_token IN ({placeholders})")
        params.extend(guest_tokens)

    query = f"SELECT * FROM orders WHERE ({' OR '.join(conditions)}) ORDER BY created_at DESC"
    cursor.execute(query, params)
    orders = [dict(r) for r in cursor.fetchall()]

    for o in orders:
        cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (o['id'],))
        o['items'] = [dict(i) for i in cursor.fetchall()]

        # Strip UPI details unless accepted (UPI Gating)
        if o['payment_method'] == 'ONLINE_UPI' and o['status'] in ('ACCEPTED', 'PAYMENT_PENDING', 'PAYMENT_VERIFIED'):
            cursor.execute("SELECT upi_id, upi_qr_url, upi_instructions_en, upi_instructions_hi FROM store_settings WHERE id = 1")
            st = cursor.fetchone()
            if st:
                o['upi_details'] = {
                    'upi_id': st['upi_id'],
                    'upi_qr_url': st['upi_qr_url'],
                    'upi_instructions_en': st['upi_instructions_en'],
                    'upi_instructions_hi': st['upi_instructions_hi'],
                    'pay_uri': f"upi://pay?pa={st['upi_id']}&pn=Yadav%20General%20Store&am={o['total_amount']:.2f}&cu=INR"
                }
        else:
            o['upi_details'] = None

    conn.close()
    return jsonify(orders)

@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order_details(order_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    if not order:
        conn.close()
        return jsonify({'error': 'Order not found.'}), 404

    order = dict(order)
    user_id = session.get('user_id')
    guest_tokens = session.get('guest_tokens', [])
    token_param = request.args.get('token', '').strip()

    is_authorized = (
        is_owner() or
        (user_id and order['customer_id'] == user_id) or
        (order['guest_token'] and (order['guest_token'] in guest_tokens or order['guest_token'] == token_param))
    )

    if not is_authorized:
        conn.close()
        return jsonify({'error': 'Access denied to this order.'}), 403

    cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    order['items'] = [dict(i) for i in cursor.fetchall()]

    # UPI Gating: Show payment details ONLY IF status is ACCEPTED/PAYMENT_PENDING and payment_method is ONLINE_UPI
    if order['payment_method'] == 'ONLINE_UPI' and order['status'] in ('ACCEPTED', 'PAYMENT_PENDING', 'PAYMENT_VERIFIED'):
        cursor.execute("SELECT upi_id, upi_qr_url, upi_instructions_en, upi_instructions_hi FROM store_settings WHERE id = 1")
        st = cursor.fetchone()
        if st:
            order['upi_details'] = {
                'upi_id': st['upi_id'],
                'upi_qr_url': st['upi_qr_url'],
                'upi_instructions_en': st['upi_instructions_en'],
                'upi_instructions_hi': st['upi_instructions_hi'],
                'pay_uri': f"upi://pay?pa={st['upi_id']}&pn=Yadav%20General%20Store&am={order['total_amount']:.2f}&cu=INR"
            }
    else:
        order['upi_details'] = None

    conn.close()
    return jsonify(order)

@app.route('/api/orders/<int:order_id>/upload-payment', methods=['POST'])
def upload_payment_screenshot(order_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    if not order:
        conn.close()
        return jsonify({'error': 'Order not found.'}), 404

    order = dict(order)
    user_id = session.get('user_id')
    guest_tokens = session.get('guest_tokens', [])
    token_param = request.form.get('token', '').strip()
    is_authorized = (
        is_owner() or
        (user_id and order['customer_id'] == user_id) or
        (order['guest_token'] and (order['guest_token'] in guest_tokens or order['guest_token'] == token_param))
    )
    if not is_authorized:
        conn.close()
        return jsonify({'error': 'Access denied.'}), 403

    if order['payment_method'] != 'ONLINE_UPI':
        conn.close()
        return jsonify({'error': 'This order does not use Online UPI payment.'}), 400

    if order['status'] not in ('ACCEPTED', 'PAYMENT_PENDING'):
        conn.close()
        return jsonify({'error': f'Cannot upload payment screenshot when order status is {order["status"]}.'}), 400

    if 'screenshot' not in request.files:
        conn.close()
        return jsonify({'error': 'No screenshot file provided.'}), 400

    file = request.files['screenshot']
    if file.filename == '':
        conn.close()
        return jsonify({'error': 'Empty filename.'}), 400

    if file and allowed_file(file.filename):
        # Validate binary magic bytes to prevent spoofed/malicious uploads
        is_valid, err_or_mime = validate_image_bytes(file.stream)
        if not is_valid:
            conn.close()
            return jsonify({'error': err_or_mime}), 400

        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"payment_{order_id}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(app.config['PAYMENTS_UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Store authenticated media endpoint path (not a public URL)
        screenshot_url = f"/api/orders/{order_id}/payment-proof"
        cursor.execute("""
            UPDATE orders
            SET payment_screenshot_url = ?, status = 'PAYMENT_PENDING', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (screenshot_url, order_id))

        cursor.execute("""
            INSERT INTO notifications (user_id, order_id, message_en, message_hi)
            VALUES (?, ?, ?, ?)
        """, (
            order['customer_id'], order_id,
            f"Payment screenshot uploaded for Order #{order['order_number']}. Awaiting store verification.",
            f"ऑर्डर #{order['order_number']} के लिए भुगतान का स्क्रीनशॉट अपलोड किया गया। सत्यापन की प्रतीक्षा है।"
        ))

        conn.commit()
        conn.close()
        return jsonify({
            'message': 'Payment screenshot uploaded successfully! Store owner will verify shortly.',
            'screenshot_url': screenshot_url,
            'status': 'PAYMENT_PENDING'
        })

    conn.close()
    return jsonify({'error': 'Invalid file format. Allowed formats: PNG, JPG, JPEG, WEBP, GIF.'}), 400

@app.route('/api/orders/<int:order_id>/payment-proof', methods=['GET'])
def get_payment_proof(order_id):
    """
    Authenticated access guard for payment screenshot documents.
    Strictly restricted to Store Owner or the customer who placed the order.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    conn.close()

    if not order:
        return jsonify({'error': 'Order not found.'}), 404

    order = dict(order)
    user_id = session.get('user_id')
    guest_tokens = session.get('guest_tokens', [])
    token_param = request.args.get('token', '').strip()

    is_authorized = (
        is_owner() or
        (user_id and order['customer_id'] == user_id) or
        (order['guest_token'] and (order['guest_token'] in guest_tokens or order['guest_token'] == token_param))
    )

    if not is_authorized:
        return jsonify({'error': 'Unauthorized: Access to this payment proof is strictly restricted.', 'status': 403}), 403

    if not order['payment_screenshot_url']:
        return jsonify({'error': 'No payment screenshot on file.'}), 404

    # Search payments directory for payment_{order_id}_*
    prefix = f"payment_{order_id}_"
    if os.path.exists(app.config['PAYMENTS_UPLOAD_FOLDER']):
        for fname in os.listdir(app.config['PAYMENTS_UPLOAD_FOLDER']):
            if fname.startswith(prefix):
                return send_from_directory(app.config['PAYMENTS_UPLOAD_FOLDER'], fname)

    return jsonify({'error': 'Payment screenshot file not found on disk.'}), 404

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    user_id = session.get('user_id')
    guest_tokens = session.get('guest_tokens', [])

    conn = get_db()
    cursor = conn.cursor()

    if user_id:
        cursor.execute("""
            SELECT n.* FROM notifications n
            WHERE n.user_id = ?
            ORDER BY n.created_at DESC LIMIT 20
        """, (user_id,))
    elif guest_tokens:
        placeholders = ','.join(['?'] * len(guest_tokens))
        cursor.execute(f"""
            SELECT n.* FROM notifications n
            JOIN orders o ON n.order_id = o.id
            WHERE o.guest_token IN ({placeholders})
            ORDER BY n.created_at DESC LIMIT 20
        """, guest_tokens)
    else:
        conn.close()
        return jsonify([])

    notifs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(notifs)

@app.route('/api/notifications/mark-read', methods=['POST'])
def mark_notifications_read():
    user_id = session.get('user_id')
    guest_tokens = session.get('guest_tokens', [])

    conn = get_db()
    cursor = conn.cursor()

    if user_id:
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
    elif guest_tokens:
        placeholders = ','.join(['?'] * len(guest_tokens))
        cursor.execute(f"""
            UPDATE notifications SET is_read = 1
            WHERE order_id IN (SELECT id FROM orders WHERE guest_token IN ({placeholders}))
        """, guest_tokens)

    conn.commit()
    conn.close()
    return jsonify({'message': 'Notifications marked as read.'})

# ==========================================
# OWNER APIS (STRICT ROLE-BASED ACCESS CONTROL)
# ==========================================
@app.route('/api/owner/login', methods=['POST'])
def owner_login_api():
    ip = request.remote_addr or '127.0.0.1'
    allowed, retry_after = check_rate_limit(ip, scope='owner_login')
    if not allowed:
        return jsonify({
            'error': f'Too many failed owner login attempts. Please wait {retry_after} seconds before trying again.'
        }), 429

    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'error': 'Username and password required.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND role = 'owner'", (username,))
    user = cursor.fetchone()
    conn.close()

    if not user or not verify_password(password, user['password_hash']):
        record_failed_attempt(ip, scope='owner_login')
        return jsonify({'error': 'Invalid owner credentials.'}), 401

    # Reset failed attempts
    reset_failed_attempts(ip, scope='owner_login')

    session['user_id'] = user['id']
    session['role'] = 'owner'
    session['username'] = user['username']
    session['full_name'] = user['full_name']

    return jsonify({
        'message': 'Owner login successful!',
        'user': {'id': user['id'], 'username': user['username'], 'full_name': user['full_name'], 'role': 'owner'}
    })

@app.route('/api/owner/change-password', methods=['POST'])
@owner_required
def owner_change_password():
    data = request.get_json() or {}
    current_password = data.get('current_password', '').strip()
    new_password = data.get('new_password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()

    if not current_password or not new_password or not confirm_password:
        return jsonify({'error': 'Current password, new password, and confirmation are required.'}), 400

    if new_password != confirm_password:
        return jsonify({'error': 'New passwords do not match.'}), 400

    is_valid, msg = validate_password_strength(new_password)
    if not is_valid:
        return jsonify({'error': msg}), 400

    user_id = session.get('user_id')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE id = ? AND role = 'owner'", (user_id,))
    user = cursor.fetchone()

    if not user or not verify_password(current_password, user['password_hash']):
        conn.close()
        return jsonify({'error': 'Current password is incorrect.'}), 401

    new_hash = hash_password(new_password)
    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Owner password updated successfully!'})

@app.route('/api/owner/orders', methods=['GET'])
@owner_required
def get_owner_orders():
    status_filter = request.args.get('status', '').strip()
    conn = get_db()
    cursor = conn.cursor()

    if status_filter and status_filter.upper() != 'ALL':
        cursor.execute("SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC", (status_filter.upper(),))
    else:
        cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")

    orders = [dict(r) for r in cursor.fetchall()]

    for o in orders:
        cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (o['id'],))
        o['items'] = [dict(i) for i in cursor.fetchall()]

    conn.close()
    return jsonify(orders)

@app.route('/api/owner/orders/<int:order_id>/accept', methods=['POST'])
@owner_required
def accept_order(order_id):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = cursor.fetchone()
        if not order:
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Order not found.'}), 404

        order = dict(order)

        # Idempotency guard: Prevent duplicate deductions
        if order['status'] in ('ACCEPTED', 'PAYMENT_PENDING', 'PAYMENT_VERIFIED', 'PROCESSING', 'COMPLETED') and order['stock_deducted'] == 1:
            conn.commit()
            conn.close()
            return jsonify({'message': 'Order is already accepted and stock was already deducted.', 'status': order['status']})

        if order['status'] in ('REJECTED', 'CANCELLED'):
            conn.rollback()
            conn.close()
            return jsonify({'error': f'Cannot accept order with status {order["status"]}.'}), 400

        cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
        items = [dict(i) for i in cursor.fetchall()]

        # Verify stock sufficiency for all items
        for it in items:
            cursor.execute("SELECT id, name_en, stock, base_unit FROM products WHERE id = ?", (it['product_id'],))
            prod = cursor.fetchone()
            if not prod:
                conn.rollback()
                conn.close()
                return jsonify({'error': f'Product ID {it["product_id"]} no longer exists in database.'}), 400

            if prod['stock'] < it['base_deduction_qty']:
                conn.rollback()
                conn.close()
                return jsonify({
                    'error': f'Insufficient stock for "{prod["name_en"]}". Current stock: {prod["stock"]} {prod["base_unit"]}, Required: {it["base_deduction_qty"]} {prod["base_unit"]}. Please restock before accepting.'
                }), 400

        # Safe atomic deduction
        for it in items:
            cursor.execute("""
                UPDATE products
                SET stock = ROUND(stock - ?, 3), updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND stock >= ?
            """, (it['base_deduction_qty'], it['product_id'], it['base_deduction_qty']))
            if cursor.rowcount == 0:
                conn.rollback()
                conn.close()
                return jsonify({'error': f'Stock deduction failed for product ID {it["product_id"]}. Stock changed concurrently.'}), 400

        new_status = 'ACCEPTED'
        cursor.execute("""
            UPDATE orders
            SET status = ?, stock_deducted = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, order_id))

        cursor.execute("""
            INSERT INTO notifications (user_id, order_id, message_en, message_hi)
            VALUES (?, ?, ?, ?)
        """, (
            order['customer_id'], order_id,
            f"Great news! Store owner has accepted Order #{order['order_number']}.",
            f"खुशखबरी! दुकानदार ने आपका ऑर्डर #{order['order_number']} स्वीकार कर लिया है।"
        ))

        conn.commit()
        conn.close()

        return jsonify({
            'message': 'Order accepted successfully and stock deducted safely.',
            'order_id': order_id,
            'status': new_status,
            'stock_deducted': 1
        })

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': f'Database error during order acceptance: {str(e)}'}), 500

@app.route('/api/owner/orders/<int:order_id>/reject', methods=['POST'])
@owner_required
def reject_order(order_id):
    data = request.get_json() or {}
    reason = data.get('reason', 'Order rejected by store owner.').strip()

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = cursor.fetchone()
        if not order:
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Order not found.'}), 404

        order = dict(order)
        if order['status'] in ('REJECTED', 'CANCELLED'):
            conn.commit()
            conn.close()
            return jsonify({'message': 'Order is already rejected/cancelled.'})

        # If stock was previously deducted, restore it safely
        if order['stock_deducted'] == 1:
            cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
            items = cursor.fetchall()
            for it in items:
                cursor.execute("""
                    UPDATE products
                    SET stock = ROUND(stock + ?, 3), updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (it['base_deduction_qty'], it['product_id']))

        cursor.execute("""
            UPDATE orders
            SET status = 'REJECTED', stock_deducted = 0, payment_notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (reason, order_id))

        cursor.execute("""
            INSERT INTO notifications (user_id, order_id, message_en, message_hi)
            VALUES (?, ?, ?, ?)
        """, (
            order['customer_id'], order_id,
            f"Order #{order['order_number']} was rejected. Reason: {reason}",
            f"ऑर्डर #{order['order_number']} निरस्त कर दिया गया। कारण: {reason}"
        ))

        conn.commit()
        conn.close()

        return jsonify({'message': 'Order rejected. Stock preserved/restored safely.', 'status': 'REJECTED'})

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': f'Error rejecting order: {str(e)}'}), 500

@app.route('/api/owner/orders/<int:order_id>/verify-payment', methods=['POST'])
@owner_required
def verify_payment(order_id):
    data = request.get_json() or {}
    decision = data.get('decision', 'APPROVE').upper()
    notes = data.get('notes', '').strip()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    if not order:
        conn.close()
        return jsonify({'error': 'Order not found.'}), 404

    order = dict(order)
    if decision == 'APPROVE':
        new_status = 'PAYMENT_VERIFIED'
        cursor.execute("""
            UPDATE orders
            SET status = ?, payment_notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, notes, order_id))

        cursor.execute("""
            INSERT INTO notifications (user_id, order_id, message_en, message_hi)
            VALUES (?, ?, ?, ?)
        """, (
            order['customer_id'], order_id,
            f"Payment verified for Order #{order['order_number']}! Your order is being packed.",
            f"ऑर्डर #{order['order_number']} का भुगतान सत्यापित हुआ! आपका सामान पैक किया जा रहा है।"
        ))
    else:
        new_status = 'ACCEPTED'
        rejection_reason = notes or 'Payment screenshot could not be verified. Please re-upload clear proof.'
        cursor.execute("""
            UPDATE orders
            SET status = ?, payment_notes = ?, payment_screenshot_url = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, rejection_reason, order_id))

        cursor.execute("""
            INSERT INTO notifications (user_id, order_id, message_en, message_hi)
            VALUES (?, ?, ?, ?)
        """, (
            order['customer_id'], order_id,
            f"Payment proof rejected for Order #{order['order_number']}: {rejection_reason}",
            f"ऑर्डर #{order['order_number']} का भुगतान प्रमाण अस्वीकार: {rejection_reason}"
        ))

    conn.commit()
    conn.close()
    return jsonify({'message': f'Payment {decision.lower()}d successfully.', 'status': new_status})

@app.route('/api/owner/orders/<int:order_id>/status', methods=['POST'])
@owner_required
def update_order_status(order_id):
    data = request.get_json() or {}
    new_status = data.get('status', '').upper()
    valid_statuses = ('PENDING_OWNER_APPROVAL', 'ACCEPTED', 'PAYMENT_PENDING', 'PAYMENT_VERIFIED', 'PROCESSING', 'COMPLETED', 'REJECTED', 'CANCELLED')

    if new_status not in valid_statuses:
        return jsonify({'error': 'Invalid status.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    if not order:
        conn.close()
        return jsonify({'error': 'Order not found.'}), 404

    order = dict(order)
    cursor.execute("UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, order_id))

    status_messages = {
        'PROCESSING': (f"Order #{order['order_number']} is being prepared.", f"ऑर्डर #{order['order_number']} तैयार किया जा रहा है।"),
        'COMPLETED': (f"Order #{order['order_number']} has been completed/delivered! Thank you!", f"ऑर्डर #{order['order_number']} पूरा / डिलीवर हो गया है। धन्यवाद!"),
    }

    if new_status in status_messages:
        msg_en, msg_hi = status_messages[new_status]
        cursor.execute("""
            INSERT INTO notifications (user_id, order_id, message_en, message_hi)
            VALUES (?, ?, ?, ?)
        """, (order['customer_id'], order_id, msg_en, msg_hi))

    conn.commit()
    conn.close()
    return jsonify({'message': 'Order status updated successfully.', 'status': new_status})

# ==========================================
# OWNER PRODUCT MANAGEMENT APIS
# ==========================================
@app.route('/api/owner/products', methods=['GET'])
@owner_required
def get_owner_products():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY category, name_en")
    products = [dict(r) for r in cursor.fetchall()]

    for p in products:
        cursor.execute("SELECT * FROM product_units WHERE product_id = ? ORDER BY multiplier ASC", (p['id'],))
        p['units'] = [dict(u) for u in cursor.fetchall()]

    conn.close()
    return jsonify(products)

@app.route('/api/owner/products', methods=['POST'])
@owner_required
def add_product():
    data = request.get_json() or {}
    name_en = data.get('name_en', '').strip()
    name_hi = data.get('name_hi', '').strip()
    category = data.get('category', '').strip()
    base_price = float(data.get('base_price', 0))
    base_unit = data.get('base_unit', 'piece').strip()
    stock = float(data.get('stock', 0))
    image_url = data.get('image_url', '/static/images/default.svg').strip() or '/static/images/default.svg'
    description_en = data.get('description_en', '').strip()
    description_hi = data.get('description_hi', '').strip()
    units = data.get('units', [])

    if not name_en or not name_hi or not category or base_price <= 0:
        return jsonify({'error': 'English name, Hindi name, category, and positive price are required.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO products (
            name_en, name_hi, category, base_price, base_unit,
            stock, image_url, description_en, description_hi, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (name_en, name_hi, category, base_price, base_unit, stock, image_url, description_en, description_hi))
    prod_id = cursor.lastrowid

    if not units:
        units = [{"unit_name_en": f"1 {base_unit}", "unit_name_hi": f"१ {base_unit}", "multiplier": 1.0}]

    for u in units:
        cursor.execute("""
            INSERT INTO product_units (product_id, unit_name_en, unit_name_hi, multiplier)
            VALUES (?, ?, ?, ?)
        """, (prod_id, u.get('unit_name_en', '1 unit'), u.get('unit_name_hi', '१ यूनिट'), float(u.get('multiplier', 1.0))))

    conn.commit()
    conn.close()
    return jsonify({'message': 'Product added successfully!', 'product_id': prod_id}), 201

@app.route('/api/owner/products/<int:prod_id>', methods=['PUT'])
@owner_required
def edit_product(prod_id):
    data = request.get_json() or {}
    name_en = data.get('name_en', '').strip()
    name_hi = data.get('name_hi', '').strip()
    category = data.get('category', '').strip()
    base_price = float(data.get('base_price', 0))
    base_unit = data.get('base_unit', '').strip()
    stock = float(data.get('stock', 0))
    image_url = data.get('image_url', '').strip()
    description_en = data.get('description_en', '').strip()
    description_hi = data.get('description_hi', '').strip()
    units = data.get('units')

    if not name_en or not name_hi or not category or base_price <= 0:
        return jsonify({'error': 'Invalid product details.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM products WHERE id = ?", (prod_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Product not found.'}), 404

    cursor.execute("""
        UPDATE products
        SET name_en = ?, name_hi = ?, category = ?, base_price = ?,
            base_unit = ?, stock = ?, image_url = ?, description_en = ?,
            description_hi = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (name_en, name_hi, category, base_price, base_unit, stock, image_url, description_en, description_hi, prod_id))

    if units is not None:
        cursor.execute("DELETE FROM product_units WHERE product_id = ?", (prod_id,))
        for u in units:
            cursor.execute("""
                INSERT INTO product_units (product_id, unit_name_en, unit_name_hi, multiplier)
                VALUES (?, ?, ?, ?)
            """, (prod_id, u.get('unit_name_en', '1 unit'), u.get('unit_name_hi', '१ यूनिट'), float(u.get('multiplier', 1.0))))

    conn.commit()
    conn.close()
    return jsonify({'message': 'Product updated successfully!'})

@app.route('/api/owner/products/<int:prod_id>/toggle-active', methods=['POST'])
@owner_required
def toggle_product_active(prod_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT is_active FROM products WHERE id = ?", (prod_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Product not found.'}), 404

    new_active = 0 if row['is_active'] == 1 else 1
    cursor.execute("UPDATE products SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_active, prod_id))
    conn.commit()
    conn.close()
    return jsonify({'message': f'Product is now {"active" if new_active == 1 else "deactivated"}.', 'is_active': new_active})

@app.route('/api/owner/products/<int:prod_id>/restock', methods=['POST'])
@owner_required
def restock_product(prod_id):
    data = request.get_json() or {}
    add_qty = float(data.get('quantity', 0))
    if add_qty <= 0:
        return jsonify({'error': 'Restock quantity must be greater than zero.'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT stock FROM products WHERE id = ?", (prod_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Product not found.'}), 404

    new_stock = round(row['stock'] + add_qty, 3)
    cursor.execute("UPDATE products SET stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_stock, prod_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Product restocked successfully!', 'new_stock': new_stock})

@app.route('/api/owner/products/<int:prod_id>', methods=['DELETE'])
@owner_required
def delete_product(prod_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM products WHERE id = ?", (prod_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Product not found.'}), 404

    cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Product deleted successfully.'})

# ==========================================
# OWNER STORE SETTINGS & UPLOAD APIS
# ==========================================
@app.route('/api/owner/settings', methods=['GET', 'POST'])
@owner_required
def owner_settings():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.get_json() or {}
        delivery_charge = float(data.get('delivery_charge', 30.0))
        min_order_amount = float(data.get('min_order_amount', 100.0))
        free_delivery_threshold = float(data.get('free_delivery_threshold', 500.0))
        home_delivery_enabled = 1 if data.get('home_delivery_enabled', True) else 0
        store_pickup_enabled = 1 if data.get('store_pickup_enabled', True) else 0
        upi_id = data.get('upi_id', 'yadavstore@oksbi').strip()
        upi_qr_url = data.get('upi_qr_url', '').strip()
        upi_instructions_en = data.get('upi_instructions_en', '').strip()
        upi_instructions_hi = data.get('upi_instructions_hi', '').strip()

        cursor.execute("""
            UPDATE store_settings
            SET delivery_charge = ?, min_order_amount = ?, free_delivery_threshold = ?,
                home_delivery_enabled = ?, store_pickup_enabled = ?,
                upi_id = ?, upi_qr_url = ?,
                upi_instructions_en = ?, upi_instructions_hi = ?
            WHERE id = 1
        """, (
            delivery_charge, min_order_amount, free_delivery_threshold,
            home_delivery_enabled, store_pickup_enabled,
            upi_id, upi_qr_url,
            upi_instructions_en, upi_instructions_hi
        ))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Store settings updated successfully!'})

    cursor.execute("SELECT * FROM store_settings WHERE id = 1")
    settings = dict(cursor.fetchone())
    conn.close()
    return jsonify(settings)

@app.route('/api/owner/upload', methods=['POST'])
@owner_required
def owner_upload():
    """
    Owner image uploader for product photos and custom QR codes.
    Validates file extension and binary magic bytes.
    Saves to PRODUCTS_UPLOAD_FOLDER.
    """
    file = request.files.get('file') or request.files.get('image')
    if not file:
        return jsonify({'error': 'No file uploaded.'}), 400
    if file.filename == '':
        return jsonify({'error': 'Empty filename.'}), 400

    if file and allowed_file(file.filename):
        is_valid, err_or_mime = validate_image_bytes(file.stream)
        if not is_valid:
            return jsonify({'error': err_or_mime}), 400

        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"asset_{uuid.uuid4().hex[:10]}.{ext}"
        filepath = os.path.join(app.config['PRODUCTS_UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({'url': f"/uploads/{filename}", 'message': 'Upload successful!'})

    return jsonify({'error': 'Invalid file type. Allowed formats: PNG, JPG, JPEG, WEBP, GIF.'}), 400

with app.app_context():
    init_db()
    seed_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
