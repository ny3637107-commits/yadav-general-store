// Yadav General Store - Customer Front-end Application
let allProducts = [];
let currentCategory = 'all';
let cart = JSON.parse(localStorage.getItem('ygs_cart') || '[]');
let storeSettings = {
  delivery_charge: 30,
  min_order_amount: 100,
  free_delivery_threshold: 500,
  home_delivery_enabled: 1,
  store_pickup_enabled: 1
};
let currentUser = null;

// Toast Notification
function showToast(message, type = 'success') {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.className = `toast ${type}`;
  toast.style.display = 'block';
  setTimeout(() => {
    toast.style.display = 'none';
  }, 3500);
}

// Fetch Initial Settings & User Info
async function initApp() {
  try {
    const [settingsRes, userRes] = await Promise.all([
      fetch('/api/settings'),
      fetch('/api/auth/me')
    ]);

    if (settingsRes.ok) {
      storeSettings = await settingsRes.json();
    }

    if (userRes.ok) {
      const userData = await userRes.json();
      if (userData.logged_in) {
        currentUser = userData.user;
        renderUserHeader();
      }
    }
  } catch (err) {
    console.error("Initialization error:", err);
  }

  await loadCategories();
  await loadProducts();
  renderCart();
  await loadNotifications();
  setupEventListeners();
  setInterval(loadNotifications, 15000);
}

function renderUserHeader() {
  const authContainer = document.getElementById('nav-auth-container');
  if (!authContainer) return;
  if (currentUser) {
    authContainer.innerHTML = `
      <span style="font-size:0.85rem; font-weight:700; color:var(--primary-dark);">👋 ${currentUser.full_name}</span>
      <button onclick="handleLogout()" class="nav-link" style="border:none; background:transparent; cursor:pointer;" data-i18n="navLogout">Logout</button>
    `;
  } else {
    authContainer.innerHTML = `
      <button onclick="openAuthModal('login')" class="nav-link" style="border:none; background:transparent; cursor:pointer;" data-i18n="navLogin">Login</button>
      <button onclick="openAuthModal('register')" class="nav-link" style="border:none; background:transparent; cursor:pointer;" data-i18n="navRegister">Register</button>
    `;
  }
  updatePageText();
}

async function handleLogout() {
  await fetch('/api/auth/logout', { method: 'POST' });
  currentUser = null;
  renderUserHeader();
  showToast("Logged out successfully.", "info");
}

// Load Categories
async function loadCategories() {
  try {
    const res = await fetch('/api/categories');
    const categories = await res.json();
    const bar = document.getElementById('categories-bar');
    if (!bar) return;

    let html = `<button class="cat-pill active" onclick="filterCategory('all', this)" data-i18n="allCategories">${t('allCategories')}</button>`;
    categories.forEach(c => {
      html += `<button class="cat-pill" onclick="filterCategory('${c}', this)">${c}</button>`;
    });
    bar.innerHTML = html;
  } catch (err) {
    console.error("Error loading categories:", err);
  }
}

// Load Products
async function loadProducts() {
  try {
    let url = '/api/products';
    const params = new URLSearchParams();
    if (currentCategory && currentCategory !== 'all') {
      params.append('category', currentCategory);
    }
    const searchVal = document.getElementById('search-input')?.value.trim();
    if (searchVal) {
      params.append('search', searchVal);
    }

    if (params.toString()) {
      url += '?' + params.toString();
    }

    const res = await fetch(url);
    allProducts = await res.json();
    renderProducts();
  } catch (err) {
    console.error("Error loading products:", err);
  }
}

function filterCategory(cat, btnEl) {
  currentCategory = cat;
  document.querySelectorAll('.cat-pill').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  loadProducts();
}

// Render Products Grid
function renderProducts() {
  const grid = document.getElementById('products-grid');
  if (!grid) return;

  if (allProducts.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-muted);">
        <h3>No products found.</h3>
        <p>Try searching for something else or browse all categories.</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = allProducts.map(p => {
    const isHindi = currentLang === 'hi';
    const title = isHindi ? p.name_hi : p.name_en;
    const subTitle = isHindi ? p.name_en : p.name_hi;
    const desc = isHindi ? (p.description_hi || p.description_en) : (p.description_en || p.description_hi);

    // Stock Status
    let stockBadge = '';
    if (p.stock <= 0) {
      stockBadge = `<span class="stock-tag stock-out" data-i18n="outOfStock">${t('outOfStock')}</span>`;
    } else if (p.stock <= 5) {
      stockBadge = `<span class="stock-tag stock-low">${t('lowStock', { n: p.stock + ' ' + p.base_unit })}</span>`;
    } else {
      stockBadge = `<span class="stock-tag stock-in" data-i18n="inStock">${t('inStock')}</span>`;
    }

    // Units dropdown
    const unitOptions = (p.units || []).map((u, idx) => {
      const uName = isHindi ? u.unit_name_hi : u.unit_name_en;
      return `<option value="${u.id}" data-price="${u.calculated_price}" data-mult="${u.multiplier}" ${idx === 0 ? 'selected' : ''}>
        ${uName} - ₹${u.calculated_price}
      </option>`;
    }).join('');

    const initialPrice = p.units && p.units.length > 0 ? p.units[0].calculated_price : p.base_price;
    const isOut = p.stock <= 0;

    return `
      <div class="product-card" id="product-${p.id}">
        <div class="product-img-wrapper">
          <img src="${p.image_url || '/static/images/default.svg'}" alt="${title}" class="product-img" loading="lazy" onerror="this.src='/static/images/default.svg'" />
          ${stockBadge}
        </div>
        <div class="product-category">${p.category}</div>
        <h3 class="product-title">${title}</h3>
        <div class="product-title-hi">${subTitle}</div>
        <p class="product-desc">${desc || ''}</p>

        <div class="product-footer">
          <div class="unit-select-wrap">
            <label class="unit-label" data-i18n="selectUnit">${t('selectUnit')}</label>
            <select class="unit-select" onchange="updateProductPriceDisplay(${p.id}, this)" ${isOut ? 'disabled' : ''}>
              ${unitOptions}
            </select>
          </div>

          <div class="price-action-row">
            <div class="price-display" id="price-display-${p.id}">₹${initialPrice}</div>
            <button class="add-btn" onclick="addToCart(${p.id})" ${isOut ? 'disabled' : ''} data-i18n="addToCart">
              ${isOut ? t('outOfStock') : '🛒 ' + t('addToCart')}
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function updateProductPriceDisplay(productId, selectEl) {
  const selectedOpt = selectEl.options[selectEl.selectedIndex];
  const price = selectedOpt.getAttribute('data-price');
  const priceDisplay = document.getElementById(`price-display-${productId}`);
  if (priceDisplay) {
    priceDisplay.textContent = `₹${price}`;
  }
}

// Cart Logic
function addToCart(productId) {
  const prod = allProducts.find(p => p.id === productId);
  if (!prod || prod.stock <= 0) {
    showToast(t('insufficientStock'), 'error');
    return;
  }

  const card = document.getElementById(`product-${productId}`);
  const unitSelect = card.querySelector('.unit-select');
  const unitId = parseInt(unitSelect.value);
  const selectedUnit = prod.units.find(u => u.id === unitId) || prod.units[0];

  const existingItemIndex = cart.findIndex(it => it.product_id === prod.id && it.unit_id === selectedUnit.id);

  const neededMultiplier = selectedUnit.multiplier;

  if (existingItemIndex > -1) {
    const currentQty = cart[existingItemIndex].quantity;
    const totalDeductionNeeded = (currentQty + 1) * neededMultiplier;
    if (totalDeductionNeeded > prod.stock) {
      showToast(t('stockWarning', { name: prod.name_en, stock: `${prod.stock} ${prod.base_unit}` }), 'error');
      return;
    }
    cart[existingItemIndex].quantity += 1;
  } else {
    if (neededMultiplier > prod.stock) {
      showToast(t('stockWarning', { name: prod.name_en, stock: `${prod.stock} ${prod.base_unit}` }), 'error');
      return;
    }
    cart.push({
      product_id: prod.id,
      unit_id: selectedUnit.id,
      product_name_en: prod.name_en,
      product_name_hi: prod.name_hi,
      unit_name_en: selectedUnit.unit_name_en,
      unit_name_hi: selectedUnit.unit_name_hi,
      unit_price: selectedUnit.calculated_price,
      multiplier: selectedUnit.multiplier,
      base_unit: prod.base_unit,
      stock: prod.stock,
      quantity: 1
    });
  }

  saveCart();
  renderCart();
  showToast(`Added ${prod.name_en} to cart!`, 'success');
}

function updateCartQty(index, delta) {
  if (!cart[index]) return;
  const item = cart[index];
  const newQty = item.quantity + delta;

  if (newQty <= 0) {
    cart.splice(index, 1);
  } else {
    if ((newQty * item.multiplier) > item.stock) {
      showToast(t('stockWarning', { name: item.product_name_en, stock: `${item.stock} ${item.base_unit}` }), 'error');
      return;
    }
    item.quantity = newQty;
  }

  saveCart();
  renderCart();
}

function saveCart() {
  localStorage.setItem('ygs_cart', JSON.stringify(cart));
}

function renderCart() {
  const cartBadge = document.getElementById('cart-badge');
  const cartTotalQty = cart.reduce((sum, it) => sum + it.quantity, 0);
  if (cartBadge) {
    cartBadge.textContent = cartTotalQty;
    cartBadge.style.display = cartTotalQty > 0 ? 'inline-block' : 'none';
  }

  const itemsContainer = document.getElementById('cart-items-container');
  const subtotalEl = document.getElementById('cart-subtotal');
  const deliveryFeeEl = document.getElementById('cart-delivery-fee');
  const grandTotalEl = document.getElementById('cart-grand-total');
  const freeDeliveryBanner = document.getElementById('free-delivery-banner');
  const checkoutBtn = document.getElementById('cart-checkout-btn');

  if (!itemsContainer) return;

  if (cart.length === 0) {
    itemsContainer.innerHTML = `
      <div style="text-align:center; padding: 2rem; color: var(--text-muted);">
        <p style="font-size:2rem; margin-bottom:0.5rem;">🛒</p>
        <p data-i18n="cartEmpty">${t('cartEmpty')}</p>
      </div>
    `;
    if (subtotalEl) subtotalEl.textContent = '₹0';
    if (deliveryFeeEl) deliveryFeeEl.textContent = '₹0';
    if (grandTotalEl) grandTotalEl.textContent = '₹0';
    if (freeDeliveryBanner) freeDeliveryBanner.style.display = 'none';
    if (checkoutBtn) checkoutBtn.disabled = true;
    return;
  }

  const isHindi = currentLang === 'hi';
  const subtotal = cart.reduce((sum, it) => sum + (it.unit_price * it.quantity), 0);

  itemsContainer.innerHTML = cart.map((it, idx) => {
    const name = isHindi ? it.product_name_hi : it.product_name_en;
    const unitName = isHindi ? it.unit_name_hi : it.unit_name_en;
    return `
      <div class="cart-item">
        <div class="cart-item-info">
          <div class="cart-item-name">${name}</div>
          <div class="cart-item-unit">${unitName} • ₹${it.unit_price}</div>
        </div>
        <div class="qty-control">
          <button class="qty-btn" onclick="updateCartQty(${idx}, -1)">−</button>
          <span class="qty-val">${it.quantity}</span>
          <button class="qty-btn" onclick="updateCartQty(${idx}, 1)">+</button>
        </div>
        <div style="font-weight:700; min-width:60px; text-align:right;">
          ₹${(it.unit_price * it.quantity).toFixed(2)}
        </div>
      </div>
    `;
  }).join('');

  // Delivery calculation for preview (assume Home Delivery by default)
  let estDelivery = 0;
  if (subtotal < storeSettings.free_delivery_threshold) {
    estDelivery = storeSettings.delivery_charge;
    if (freeDeliveryBanner) {
      const diff = storeSettings.free_delivery_threshold - subtotal;
      freeDeliveryBanner.textContent = t('freeDeliveryNote', { n: diff.toFixed(0) });
      freeDeliveryBanner.style.display = 'block';
    }
  } else {
    estDelivery = 0;
    if (freeDeliveryBanner) {
      freeDeliveryBanner.textContent = "🎉 You have qualified for FREE Delivery!";
      freeDeliveryBanner.style.display = 'block';
    }
  }

  if (subtotalEl) subtotalEl.textContent = `₹${subtotal.toFixed(2)}`;
  if (deliveryFeeEl) deliveryFeeEl.textContent = estDelivery === 0 ? t('freeDelivery') : `₹${estDelivery.toFixed(2)}`;
  if (grandTotalEl) grandTotalEl.textContent = `₹${(subtotal + estDelivery).toFixed(2)}`;

  if (checkoutBtn) {
    if (subtotal < storeSettings.min_order_amount) {
      checkoutBtn.disabled = true;
      checkoutBtn.textContent = t('minOrderNotice', { n: storeSettings.min_order_amount });
    } else {
      checkoutBtn.disabled = false;
      checkoutBtn.textContent = `${t('proceedCheckout')} (₹${(subtotal + estDelivery).toFixed(2)})`;
    }
  }
}

// Modal Handlers
function toggleCartModal(open = true) {
  const modal = document.getElementById('cart-modal');
  if (modal) {
    modal.classList.toggle('active', open);
    if (open) renderCart();
  }
}

function openCheckoutModal() {
  toggleCartModal(false);
  const checkoutModal = document.getElementById('checkout-modal');
  if (!checkoutModal) return;

  // Pre-fill user data if logged in
  if (currentUser) {
    const nameInp = document.getElementById('order-name');
    const phoneInp = document.getElementById('order-phone');
    const addrInp = document.getElementById('order-address');
    if (nameInp && !nameInp.value) nameInp.value = currentUser.full_name || '';
    if (phoneInp && !phoneInp.value) phoneInp.value = currentUser.phone || '';
    if (addrInp && !addrInp.value) addrInp.value = currentUser.address || '';
  }

  updateCheckoutSummary();
  checkoutModal.classList.add('active');
}

function closeCheckoutModal() {
  const checkoutModal = document.getElementById('checkout-modal');
  if (checkoutModal) checkoutModal.classList.remove('active');
}

function setDeliveryType(type) {
  document.querySelectorAll('.delivery-type-card').forEach(c => c.classList.remove('active'));
  const target = document.getElementById(`delivery-type-${type}`);
  if (target) target.classList.add('active');

  const addrGroup = document.getElementById('address-group');
  const payCodLabel = document.getElementById('label-cod-method');

  if (type === 'STORE_PICKUP') {
    if (addrGroup) addrGroup.style.display = 'none';
    if (payCodLabel) payCodLabel.textContent = t('payAtStore');
  } else {
    if (addrGroup) addrGroup.style.display = 'block';
    if (payCodLabel) payCodLabel.textContent = t('cod');
  }

  updateCheckoutSummary();
}

function updateCheckoutSummary() {
  const isPickup = document.getElementById('delivery-type-STORE_PICKUP')?.classList.contains('active');
  const subtotal = cart.reduce((sum, it) => sum + (it.unit_price * it.quantity), 0);

  let deliveryFee = 0;
  if (!isPickup) {
    deliveryFee = subtotal >= storeSettings.free_delivery_threshold ? 0 : storeSettings.delivery_charge;
  }

  const grandTotal = subtotal + deliveryFee;

  const summaryEl = document.getElementById('checkout-summary-box');
  if (summaryEl) {
    summaryEl.innerHTML = `
      <div class="bill-row"><span>${t('subtotal')}:</span><span>₹${subtotal.toFixed(2)}</span></div>
      <div class="bill-row"><span>${t('deliveryFee')}:</span><span>${deliveryFee === 0 ? t('freeDelivery') : '₹' + deliveryFee.toFixed(2)}</span></div>
      <div class="bill-row bill-total"><span>${t('totalAmount')}:</span><span>₹${grandTotal.toFixed(2)}</span></div>
    `;
  }
}

// Place Order Request
async function submitOrder(event) {
  event.preventDefault();

  if (cart.length === 0) {
    showToast(t('cartEmpty'), 'error');
    return;
  }

  const isPickup = document.getElementById('delivery-type-STORE_PICKUP')?.classList.contains('active');
  const delivery_type = isPickup ? 'STORE_PICKUP' : 'HOME_DELIVERY';

  const customer_name = document.getElementById('order-name')?.value.trim();
  const customer_phone = document.getElementById('order-phone')?.value.trim();
  const delivery_address = isPickup ? '' : document.getElementById('order-address')?.value.trim();
  const special_instructions = document.getElementById('order-instructions')?.value.trim();

  // Payment method
  const paymentMethodInput = document.querySelector('input[name="payment_method"]:checked');
  let payment_method = paymentMethodInput ? paymentMethodInput.value : 'ONLINE_UPI';

  if (isPickup && payment_method === 'COD') {
    payment_method = 'PAY_AT_STORE';
  }

  if (!customer_name || !customer_phone) {
    showToast("Please provide your name and phone number.", "error");
    return;
  }

  if (delivery_type === 'HOME_DELIVERY' && !delivery_address) {
    showToast("Please enter complete delivery address.", "error");
    return;
  }

  const payload = {
    items: cart.map(it => ({
      product_id: it.product_id,
      unit_id: it.unit_id,
      quantity: it.quantity
    })),
    customer_name,
    customer_phone,
    delivery_type,
    delivery_address,
    special_instructions,
    payment_method
  };

  const submitBtn = document.getElementById('place-order-submit-btn');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Placing Order...";
  }

  try {
    const res = await fetch('/api/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const result = await res.json();

    if (!res.ok) {
      showToast(result.error || "Failed to place order.", "error");
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = t('placeOrderBtn');
      }
      return;
    }

    // Success!
    cart = [];
    saveCart();
    renderCart();
    closeCheckoutModal();

    showToast("Order placed successfully!", "success");

    // Redirect to My Orders page
    setTimeout(() => {
      const redirectUrl = result.guest_token ? `/my-orders?token=${result.guest_token}` : '/my-orders';
      window.location.href = redirectUrl;
    }, 1000);

  } catch (err) {
    console.error("Order error:", err);
    showToast("Network error. Please try again.", "error");
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = t('placeOrderBtn');
    }
  }
}

// Authentication Modal
function openAuthModal(mode = 'login') {
  const modal = document.getElementById('auth-modal');
  if (!modal) return;
  const isLogin = mode === 'login';

  document.getElementById('auth-modal-title').textContent = isLogin ? 'Customer Login' : 'Customer Registration';
  document.getElementById('auth-name-group').style.display = isLogin ? 'none' : 'block';
  document.getElementById('auth-phone-group').style.display = isLogin ? 'none' : 'block';
  document.getElementById('auth-address-group').style.display = isLogin ? 'none' : 'block';
  document.getElementById('auth-submit-btn').textContent = isLogin ? 'Login' : 'Create Account';
  document.getElementById('auth-switch-text').innerHTML = isLogin
    ? `Don't have an account? <a href="#" onclick="openAuthModal('register'); return false;">Register here</a>`
    : `Already have an account? <a href="#" onclick="openAuthModal('login'); return false;">Login here</a>`;

  modal.setAttribute('data-mode', mode);
  modal.classList.add('active');
}

function closeAuthModal() {
  const modal = document.getElementById('auth-modal');
  if (modal) modal.classList.remove('active');
}

async function handleAuthSubmit(event) {
  event.preventDefault();
  const modal = document.getElementById('auth-modal');
  const mode = modal.getAttribute('data-mode') || 'login';

  const username = document.getElementById('auth-username').value.trim();
  const password = document.getElementById('auth-password').value.trim();

  const payload = { username, password };

  if (mode === 'register') {
    payload.full_name = document.getElementById('auth-name').value.trim();
    payload.phone = document.getElementById('auth-phone').value.trim();
    payload.address = document.getElementById('auth-address').value.trim();
  }

  const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/register';

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Authentication failed.", "error");
      return;
    }

    currentUser = data.user;
    renderUserHeader();
    closeAuthModal();
    showToast(data.message, "success");

  } catch (err) {
    showToast("Network error. Please try again.", "error");
  }
}

// Search debounce
let searchTimer = null;
function handleSearchInput() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    loadProducts();
  }, 300);
}

function setupEventListeners() {
  const searchInput = document.getElementById('search-input');
  if (searchInput) {
    searchInput.addEventListener('input', handleSearchInput);
  }
}

// ==========================================
// NOTIFICATIONS LOGIC
// ==========================================
let notificationsList = [];

async function loadNotifications() {
  try {
    const res = await fetch('/api/notifications');
    if (!res.ok) return;
    notificationsList = await res.json();
    renderNotifications();
  } catch (err) {
    console.error("Error loading notifications:", err);
  }
}

function renderNotifications() {
  const badge = document.getElementById('notif-badge');
  const container = document.getElementById('notif-list-container');
  if (!badge || !container) return;

  const unreadCount = notificationsList.filter(n => n.is_read === 0).length;
  if (unreadCount > 0) {
    badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
    badge.style.display = 'block';
  } else {
    badge.style.display = 'none';
  }

  if (notificationsList.length === 0) {
    container.innerHTML = `<p style="color:#64748b; font-size:0.9rem; text-align:center; padding:2rem 0;" data-i18n="noNotifications">${t('noNotifications')}</p>`;
    return;
  }

  const isHindi = (typeof currentLang !== 'undefined' && currentLang === 'hi');
  container.innerHTML = notificationsList.map(n => {
    const msg = isHindi ? (n.message_hi || n.message_en) : n.message_en;
    const timeStr = new Date(n.created_at).toLocaleString();
    const unreadCls = n.is_read === 0 ? 'unread' : '';
    return `
      <div class="notif-item ${unreadCls}">
        <div style="font-weight:600; color:#0f172a;">${msg}</div>
        <div class="notif-time">${timeStr}</div>
      </div>
    `;
  }).join('');
}

function toggleNotifDrawer(forceState) {
  const modal = document.getElementById('notif-drawer-modal');
  if (!modal) return;
  if (typeof forceState === 'boolean') {
    modal.style.display = forceState ? 'flex' : 'none';
  } else {
    modal.style.display = modal.style.display === 'flex' ? 'none' : 'flex';
  }
  if (modal.style.display === 'flex') {
    loadNotifications();
  }
}

async function markNotificationsAsRead() {
  try {
    const res = await fetch('/api/notifications/mark-read', { method: 'POST' });
    if (res.ok) {
      notificationsList = notificationsList.map(n => ({ ...n, is_read: 1 }));
      renderNotifications();
      showToast("All notifications marked as read.", "success");
    }
  } catch (err) {
    console.error("Error marking notifications read:", err);
  }
}

document.addEventListener('DOMContentLoaded', initApp);
