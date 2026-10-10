import sqlite3
import os
from flask import current_app, has_app_context
from config import Config

def get_db(db_path=None):
    if db_path:
        path = db_path
    elif has_app_context() and current_app and 'DB_PATH' in current_app.config:
        path = current_app.config['DB_PATH']
    else:
        path = Config.DB_PATH

    conn = sqlite3.connect(path, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db(db_path=None):
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'customer',
        full_name TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_en TEXT NOT NULL,
        name_hi TEXT NOT NULL,
        category TEXT NOT NULL,
        base_price REAL NOT NULL,
        base_unit TEXT NOT NULL,
        stock REAL NOT NULL DEFAULT 0.0,
        image_url TEXT,
        description_en TEXT,
        description_hi TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS product_units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        unit_name_en TEXT NOT NULL,
        unit_name_hi TEXT NOT NULL,
        multiplier REAL NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS store_settings (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        delivery_charge REAL NOT NULL DEFAULT 30.0,
        min_order_amount REAL NOT NULL DEFAULT 100.0,
        free_delivery_threshold REAL NOT NULL DEFAULT 500.0,
        home_delivery_enabled INTEGER NOT NULL DEFAULT 1,
        store_pickup_enabled INTEGER NOT NULL DEFAULT 1,
        upi_id TEXT NOT NULL DEFAULT 'yadavstore@upi',
        upi_qr_url TEXT,
        upi_instructions_en TEXT,
        upi_instructions_hi TEXT
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE NOT NULL,
        customer_id INTEGER,
        customer_name TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        delivery_type TEXT NOT NULL,
        delivery_address TEXT,
        special_instructions TEXT,
        subtotal REAL NOT NULL,
        delivery_charge REAL NOT NULL DEFAULT 0.0,
        total_amount REAL NOT NULL,
        payment_method TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING_OWNER_APPROVAL',
        stock_deducted INTEGER NOT NULL DEFAULT 0,
        payment_screenshot_url TEXT,
        payment_notes TEXT,
        guest_token TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        product_name_en TEXT NOT NULL,
        product_name_hi TEXT NOT NULL,
        unit_name_en TEXT NOT NULL,
        unit_name_hi TEXT NOT NULL,
        multiplier REAL NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        item_total REAL NOT NULL,
        base_deduction_qty REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id)
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        order_id INTEGER NOT NULL,
        message_en TEXT NOT NULL,
        message_hi TEXT NOT NULL,
        is_read INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("SELECT id FROM store_settings WHERE id = 1")
    if not cursor.fetchone():
        cursor.execute("""
        INSERT INTO store_settings (
            id, delivery_charge, min_order_amount, free_delivery_threshold,
            home_delivery_enabled, store_pickup_enabled,
            upi_id, upi_qr_url, upi_instructions_en, upi_instructions_hi
        ) VALUES (
            1, 30.0, 100.0, 500.0,
            1, 1,
            'yadavstore@oksbi', '',
            'Pay exact amount via Google Pay, PhonePe, or Paytm and upload screenshot below.',
            'कृपया गूगल पे, फोनपे, या पेटीएम से सही राशि भेजें और नीचे स्क्रीनशॉट अपलोड करें।'
        )
        """)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
