import os
from database import get_db, init_db
from auth import hash_password

def seed_owner(db_path=None, username=None, password=None, full_name=None, phone=None, address=None):
    """
    Provisions an initial store owner if no owner currently exists.
    Requires password provided via arguments or environment variables:
    OWNER_PASSWORD or INITIAL_OWNER_PASSWORD.
    If no password is provided and no owner exists, no owner is created.
    If an owner already exists, existing credentials are left unchanged.
    Never prints or exposes passwords or secret values.
    """
    init_db(db_path)
    conn = get_db(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE role = 'owner'")
    if cursor.fetchone():
        conn.close()
        return False  # Existing owner preserved

    owner_user = (username or os.environ.get('OWNER_USERNAME') or 'owner').strip()
    owner_pwd = password or os.environ.get('OWNER_PASSWORD') or os.environ.get('INITIAL_OWNER_PASSWORD')

    if not owner_pwd or not owner_pwd.strip():
        conn.close()
        return False

    owner_pwd = owner_pwd.strip()
    owner_name = full_name or os.environ.get('OWNER_FULL_NAME', 'Yadav Store Owner')
    owner_phone = phone or os.environ.get('OWNER_PHONE', '9876543210')
    owner_address = address or os.environ.get('OWNER_ADDRESS', 'Shop No. 4, Main Market, Yadav Chowk')

    cursor.execute("""
        INSERT INTO users (username, password_hash, role, full_name, phone, address)
        VALUES (?, ?, 'owner', ?, ?, ?)
    """, (
        owner_user,
        hash_password(owner_pwd),
        owner_name,
        owner_phone,
        owner_address
    ))
    conn.commit()
    conn.close()
    print(f"Store owner '{owner_user}' provisioned successfully.")
    return True

def seed_all(db_path=None, owner_username=None, owner_password=None):
    init_db(db_path)
    seed_owner(db_path, username=owner_username, password=owner_password)
    conn = get_db(db_path)
    cursor = conn.cursor()

    # Seed Products if empty
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        sample_products = [
            {
                "name_en": "Aashirvaad Shudh Chakki Atta",
                "name_hi": "आशीर्वाद शुद्ध चक्की आटा",
                "category": "Atta, Rice & Dals",
                "base_price": 45.0,
                "base_unit": "kg",
                "stock": 100.0,
                "image_url": "/static/images/atta.svg",
                "description_en": "100% pure whole wheat flour processed hygienically.",
                "description_hi": "१००% शुद्ध साबुत गेहूं का आटा।",
                "units": [
                    {"name_en": "1 kg", "name_hi": "१ किलो", "multiplier": 1.0},
                    {"name_en": "5 kg", "name_hi": "५ किलो", "multiplier": 5.0},
                    {"name_en": "10 kg", "name_hi": "१० किलो", "multiplier": 10.0}
                ]
            },
            {
                "name_en": "India Gate Basmati Rice Feast",
                "name_hi": "इंडिया गेट बासमती चावल",
                "category": "Atta, Rice & Dals",
                "base_price": 110.0,
                "base_unit": "kg",
                "stock": 50.0,
                "image_url": "/static/images/rice.svg",
                "description_en": "Long grain aromatic basmati rice for biryani and daily meals.",
                "description_hi": "स्वादिष्ट और खुशबूदार लंबा बासमती चावल।",
                "units": [
                    {"name_en": "500g", "name_hi": "५०० ग्राम", "multiplier": 0.5},
                    {"name_en": "1 kg", "name_hi": "१ किलो", "multiplier": 1.0},
                    {"name_en": "5 kg", "name_hi": "५ किलो", "multiplier": 5.0}
                ]
            },
            {
                "name_en": "Desi Toor / Arhar Dal Unpolished",
                "name_hi": "देसी अरहर / तूर दाल",
                "category": "Atta, Rice & Dals",
                "base_price": 160.0,
                "base_unit": "kg",
                "stock": 40.0,
                "image_url": "/static/images/dal.svg",
                "description_en": "Protein rich unpolished desi toor dal.",
                "description_hi": "शुद्ध और बिना पॉलिश की पौष्टिक अरहर दाल।",
                "units": [
                    {"name_en": "250g", "name_hi": "२५० ग्राम", "multiplier": 0.25},
                    {"name_en": "500g", "name_hi": "५०० ग्राम", "multiplier": 0.5},
                    {"name_en": "1 kg", "name_hi": "१ किलो", "multiplier": 1.0}
                ]
            },
            {
                "name_en": "Fortune Kachi Ghani Mustard Oil",
                "name_hi": "फॉर्च्यून कच्ची घानी सरसों का तेल",
                "category": "Oils & Ghee",
                "base_price": 145.0,
                "base_unit": "packet",
                "stock": 35.0,
                "image_url": "/static/images/oil.svg",
                "description_en": "Pure cold pressed mustard oil with authentic pungent aroma.",
                "description_hi": "शुद्ध कच्ची घानी सरसों का तेल तीखे स्वाद के साथ।",
                "units": [
                    {"name_en": "1 Litre Pouch", "name_hi": "१ लीटर पाउच", "multiplier": 1.0}
                ]
            },
            {
                "name_en": "Madhur Pure & Hygienic Sugar",
                "name_hi": "मधुर शुद्ध चीनी",
                "category": "Atta, Rice & Dals",
                "base_price": 44.0,
                "base_unit": "kg",
                "stock": 80.0,
                "image_url": "/static/images/sugar.svg",
                "description_en": "Sulphur-free sparkling white refined sugar crystals.",
                "description_hi": "सल्फर मुक्त चमकदार दानेदार शुद्ध चीनी।",
                "units": [
                    {"name_en": "500g", "name_hi": "५०० ग्राम", "multiplier": 0.5},
                    {"name_en": "1 kg", "name_hi": "१ किलो", "multiplier": 1.0},
                    {"name_en": "5 kg", "name_hi": "५ किलो", "multiplier": 5.0}
                ]
            },
            {
                "name_en": "Tata Salt Vacuum Evaporated Iodised",
                "name_hi": "टाटा आयोडीन युक्त नमक",
                "category": "Spices & Masalas",
                "base_price": 28.0,
                "base_unit": "packet",
                "stock": 50.0,
                "image_url": "/static/images/salt.svg",
                "description_en": "Desh ka namak with guaranteed iodine purity.",
                "description_hi": "देश का नमक, आयोडीन से भरपूर।",
                "units": [
                    {"name_en": "1 kg Packet", "name_hi": "१ किलो पैकेट", "multiplier": 1.0}
                ]
            },
            {
                "name_en": "Catch Turmeric / Haldi Powder",
                "name_hi": "कैच हल्दी पाउडर",
                "category": "Spices & Masalas",
                "base_price": 240.0,
                "base_unit": "kg",
                "stock": 25.0,
                "image_url": "/static/images/haldi.svg",
                "description_en": "Rich color and aromatic ground turmeric powder.",
                "description_hi": "शुद्ध और प्राकृतिक रंग वाली पिसवाई हल्दी।",
                "units": [
                    {"name_en": "100g", "name_hi": "१०० ग्राम", "multiplier": 0.1},
                    {"name_en": "250g", "name_hi": "२५० ग्राम", "multiplier": 0.25},
                    {"name_en": "500g", "name_hi": "५०० ग्राम", "multiplier": 0.5},
                    {"name_en": "1 kg", "name_hi": "१ किलो", "multiplier": 1.0}
                ]
            },
            {
                "name_en": "MDH Deggi Mirch Powder",
                "name_hi": "एमडीएच देगी मिर्च पाउडर",
                "category": "Spices & Masalas",
                "base_price": 340.0,
                "base_unit": "kg",
                "stock": 20.0,
                "image_url": "/static/images/mirch.svg",
                "description_en": "Adds brilliant natural red color and balanced pungency.",
                "description_hi": "सब्जी को दे सुंदर लाल रंग और बेहतरीन स्वाद।",
                "units": [
                    {"name_en": "100g", "name_hi": "१०० ग्राम", "multiplier": 0.1},
                    {"name_en": "250g", "name_hi": "२५० ग्राम", "multiplier": 0.25},
                    {"name_en": "500g", "name_hi": "५०० ग्राम", "multiplier": 0.5}
                ]
            },
            {
                "name_en": "Amul Taaza Fresh Toned Milk",
                "name_hi": "अमूल ताज़ा टोन्ड दूध",
                "category": "Dairy & Bakery",
                "base_price": 27.0,
                "base_unit": "packet",
                "stock": 40.0,
                "image_url": "/static/images/milk.svg",
                "description_en": "Pasteurised toned milk with essential nutrients.",
                "description_hi": "ताज़ा और पाश्चुरीकृत टोन्ड दूध।",
                "units": [
                    {"name_en": "500ml Pouch", "name_hi": "५०० मिली पाउच", "multiplier": 1.0}
                ]
            },
            {
                "name_en": "Wagh Bakri Premium CTC Tea",
                "name_hi": "वाघ बकरी प्रीमियम सीटीसी चाय",
                "category": "Beverages & Tea",
                "base_price": 130.0,
                "base_unit": "packet",
                "stock": 30.0,
                "image_url": "/static/images/tea.svg",
                "description_en": "Strong blend tea delivering rich color and aroma.",
                "description_hi": "कड़क स्वाद और सुगंधित ताजगी वाली चाय।",
                "units": [
                    {"name_en": "250g Packet", "name_hi": "२५० ग्राम पैकेट", "multiplier": 1.0},
                    {"name_en": "500g Packet", "name_hi": "५०० ग्राम पैकेट", "multiplier": 2.0}
                ]
            },
            {
                "name_en": "Haldiram Nagpur Aloo Bhujia",
                "name_hi": "हल्दीराम आलू भुजिया",
                "category": "Snacks & Biscuits",
                "base_price": 48.0,
                "base_unit": "packet",
                "stock": 40.0,
                "image_url": "/static/images/bhujia.svg",
                "description_en": "Crispy and spicy potato noodles snack.",
                "description_hi": "कुरकुरी और चटपटी आलू भुजिया नमकीन।",
                "units": [
                    {"name_en": "200g Packet", "name_hi": "२०० ग्राम पैकेट", "multiplier": 1.0},
                    {"name_en": "400g Packet", "name_hi": "४०० ग्राम पैकेट", "multiplier": 2.0}
                ]
            },
            {
                "name_en": "Britannia Marie Gold Biscuits",
                "name_hi": "ब्रिटानिया मारी गोल्ड बिस्कुट",
                "category": "Snacks & Biscuits",
                "base_price": 35.0,
                "base_unit": "packet",
                "stock": 45.0,
                "image_url": "/static/images/biscuit.svg",
                "description_en": "Crispy and light tea-time biscuits with vitamins.",
                "description_hi": "चाय के साथ हल्का और कुरकुरा बिस्कुट।",
                "units": [
                    {"name_en": "250g Family Pack", "name_hi": "२५० ग्राम पैक", "multiplier": 1.0}
                ]
            }
        ]

        for p in sample_products:
            cursor.execute("""
                INSERT INTO products (
                    name_en, name_hi, category, base_price, base_unit,
                    stock, image_url, description_en, description_hi, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                p["name_en"], p["name_hi"], p["category"], p["base_price"],
                p["base_unit"], p["stock"], p["image_url"], p["description_en"], p["description_hi"]
            ))
            prod_id = cursor.lastrowid
            for u in p["units"]:
                cursor.execute("""
                    INSERT INTO product_units (product_id, unit_name_en, unit_name_hi, multiplier)
                    VALUES (?, ?, ?, ?)
                """, (prod_id, u["name_en"], u["name_hi"], u["multiplier"]))

        print(f"Seeded {len(sample_products)} grocery products with bilingual unit variants.")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    seed_all()
    print("Database seeding completed successfully.")
