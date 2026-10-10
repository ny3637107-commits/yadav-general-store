// Yadav General Store - Owner Management Console Logic
let adminOrders = [];
let adminProducts = [];
let adminSettings = {};
let currentStatusFilter = 'ALL';
let pollInterval = null;

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

// Tab Switcher
function switchTab(tabName) {
  document.querySelectorAll('.d-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content-panel').forEach(p => p.style.display = 'none');

  const tabBtn = document.getElementById(`tab-btn-${tabName}`);
  const panel = document.getElementById(`panel-${tabName}`);

  if (tabBtn) tabBtn.classList.add('active');
  if (panel) panel.style.display = 'block';

  if (tabName === 'orders') loadOwnerOrders();
  if (tabName === 'products') loadOwnerProducts();
  if (tabName === 'settings') loadOwnerSettings();
}

// Load Orders
async function loadOwnerOrders() {
  try {
    let url = '/api/owner/orders';
    if (currentStatusFilter && currentStatusFilter !== 'ALL') {
      url += `?status=${encodeURIComponent(currentStatusFilter)}`;
    }
    const res = await fetch(url);
    if (res.status === 401 || res.status === 403) {
      window.location.href = '/owner/login';
      return;
    }
    adminOrders = await res.json();
    renderStats();
    renderOrders();
  } catch (err) {
    console.error("Error loading orders:", err);
  }
}

function filterOrdersByStatus(status, btnEl) {
  currentStatusFilter = status;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');
  loadOwnerOrders();
}

function renderStats() {
  const pendingCount = adminOrders.filter(o => o.status === 'PENDING_OWNER_APPROVAL').length;
  const paymentPendingCount = adminOrders.filter(o => o.status === 'PAYMENT_PENDING').length;
  const completedOrders = adminOrders.filter(o => o.status === 'COMPLETED');
  const totalRevenue = completedOrders.reduce((sum, o) => sum + o.total_amount, 0);

  document.getElementById('stat-total-orders').textContent = adminOrders.length;
  document.getElementById('stat-pending-orders').textContent = pendingCount;
  document.getElementById('stat-payment-pending').textContent = paymentPendingCount;
  document.getElementById('stat-revenue').textContent = `₹${totalRevenue.toFixed(0)}`;
}

function renderOrders() {
  const container = document.getElementById('admin-orders-container');
  if (!container) return;

  if (adminOrders.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding: 3rem; background:white; border-radius:8px; border:1px solid #cbd5e1; color:#64748b;">
        <h3>No orders found for selected filter.</h3>
      </div>
    `;
    return;
  }

  container.innerHTML = adminOrders.map(order => {
    const itemsRows = (order.items || []).map(it => `
      <tr>
        <td><strong>${it.product_name_en}</strong><br><small style="color:#64748b;">${it.product_name_hi}</small></td>
        <td>${it.unit_name_en}</td>
        <td>${it.quantity}</td>
        <td>₹${it.item_total.toFixed(2)}</td>
        <td><span style="font-size:0.75rem; color:#475569;">${it.base_deduction_qty} base units</span></td>
      </tr>
    `).join('');

    // Action buttons depending on order status
    let actionButtons = '';

    if (order.status === 'PENDING_OWNER_APPROVAL') {
      actionButtons = `
        <button class="admin-btn admin-btn-success" onclick="acceptOrder(${order.id})">
          ✅ Accept Order (Deduct Stock)
        </button>
        <button class="admin-btn admin-btn-danger" onclick="openRejectModal(${order.id})">
          ❌ Reject Order
        </button>
      `;
    } else if (order.status === 'ACCEPTED' && order.payment_method === 'ONLINE_UPI') {
      actionButtons = `
        <span style="color:#b45309; font-weight:700; font-size:0.85rem; margin-right:auto;">
          ⏳ Awaiting Customer UPI Screenshot...
        </span>
        <button class="admin-btn admin-btn-danger" onclick="openRejectModal(${order.id})">
          Cancel / Reject
        </button>
      `;
    } else if (order.status === 'PAYMENT_PENDING') {
      actionButtons = `
        <button class="admin-btn admin-btn-primary" onclick="openPaymentVerifyModal(${order.id})">
          🔍 Inspect & Verify Payment Screenshot
        </button>
      `;
    } else if (order.status === 'ACCEPTED' || order.status === 'PAYMENT_VERIFIED' || order.status === 'PROCESSING') {
      actionButtons = `
        <button class="admin-btn admin-btn-outline" onclick="updateOrderStatus(${order.id}, 'PROCESSING')">
          📦 Mark In Packing
        </button>
        <button class="admin-btn admin-btn-success" onclick="updateOrderStatus(${order.id}, 'COMPLETED')">
          🎉 Mark Delivered / Completed
        </button>
      `;
    }

    return `
      <div class="order-card-admin" id="admin-order-${order.id}">
        <div class="order-card-header">
          <div>
            <span class="order-num-tag">${order.order_number}</span>
            <span style="color:#64748b; font-size:0.85rem; margin-left:0.5rem;">${new Date(order.created_at).toLocaleString()}</span>
          </div>
          <div>
            <span class="status-badge status-${order.status}">${order.status.replace(/_/g, ' ')}</span>
          </div>
        </div>

        <div class="order-grid-details">
          <div class="order-customer-box">
            <div style="font-weight:700; color:#0f172a; margin-bottom:0.3rem;">
              👤 Customer: ${order.customer_name}
            </div>
            <div style="color:#334155;">📞 Phone: <strong>${order.customer_phone}</strong></div>
            <div style="color:#334155; margin-top:0.3rem;">
              🚚 Mode: <strong>${order.delivery_type === 'HOME_DELIVERY' ? 'Home Delivery' : 'Store Pickup'}</strong>
            </div>
            ${order.delivery_address ? `
              <div style="color:#475569; margin-top:0.3rem; font-size:0.85rem;">
                📍 Address: <strong>${order.delivery_address}</strong>
              </div>
            ` : ''}
            ${order.special_instructions ? `
              <div style="background:#fef3c7; color:#92400e; padding:0.35rem 0.5rem; border-radius:6px; margin-top:0.4rem; font-size:0.85rem;">
                📝 Instructions: "${order.special_instructions}"
              </div>
            ` : ''}
          </div>

          <div>
            <div style="font-weight:700; margin-bottom:0.3rem;">
              💳 Payment: <strong>${order.payment_method.replace(/_/g, ' ')}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:0.2rem;">
              <span>Subtotal:</span>
              <span>₹${order.subtotal.toFixed(2)}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:0.2rem;">
              <span>Delivery Fee:</span>
              <span>₹${order.delivery_charge.toFixed(2)}</span>
            </div>
            <div style="display:flex; justify-content:space-between; font-weight:800; font-size:1.1rem; color:#15803d; border-top:1px dashed #cbd5e1; padding-top:0.3rem;">
              <span>Total Amount:</span>
              <span>₹${order.total_amount.toFixed(2)}</span>
            </div>
            ${order.payment_screenshot_url ? `
              <div style="margin-top:0.5rem;">
                <button class="admin-btn admin-btn-outline" onclick="openPaymentVerifyModal(${order.id})" style="font-size:0.75rem; padding:0.25rem 0.5rem;">
                  🖼️ View Screenshot
                </button>
              </div>
            ` : ''}
          </div>
        </div>

        <div class="order-items-box" style="margin-bottom:0.75rem;">
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>Pack/Unit</th>
                <th>Qty</th>
                <th>Price</th>
                <th>Stock Impact</th>
              </tr>
            </thead>
            <tbody>
              ${itemsRows}
            </tbody>
          </table>
        </div>

        <div class="order-actions-bar">
          ${actionButtons}
        </div>
      </div>
    `;
  }).join('');
}

// Accept Order (Strict Stock Deduction with Error Handling)
async function acceptOrder(orderId) {
  if (!confirm("Are you sure you want to ACCEPT this order? Stock will be safely deducted in the database.")) return;

  try {
    const res = await fetch(`/api/owner/orders/${orderId}/accept`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await res.json();
    if (!res.ok) {
      alert("Cannot Accept Order:\n" + (data.error || "Failed to accept order."));
      return;
    }

    showToast("Order accepted & stock safely deducted!", "success");
    loadOwnerOrders();
  } catch (err) {
    showToast("Network error. Could not accept order.", "error");
  }
}

// Reject Order Modal Handlers
let currentRejectOrderId = null;
function openRejectModal(orderId) {
  currentRejectOrderId = orderId;
  const modal = document.getElementById('reject-modal');
  if (modal) {
    document.getElementById('reject-reason').value = '';
    modal.classList.add('active');
  }
}

function closeRejectModal() {
  const modal = document.getElementById('reject-modal');
  if (modal) modal.classList.remove('active');
  currentRejectOrderId = null;
}

async function confirmRejectOrder() {
  if (!currentRejectOrderId) return;
  const reason = document.getElementById('reject-reason').value.trim() || 'Store owner cancelled order.';

  try {
    const res = await fetch(`/api/owner/orders/${currentRejectOrderId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason })
    });

    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Failed to reject order.", "error");
      return;
    }

    showToast("Order rejected. Stock preserved/restored.", "info");
    closeRejectModal();
    loadOwnerOrders();
  } catch (err) {
    showToast("Network error.", "error");
  }
}

// Payment Verification Modal
let currentVerifyOrderId = null;
function openPaymentVerifyModal(orderId) {
  const order = adminOrders.find(o => o.id === orderId);
  if (!order || !order.payment_screenshot_url) {
    showToast("No screenshot found for this order.", "error");
    return;
  }
  currentVerifyOrderId = orderId;
  document.getElementById('payment-verify-img').src = `/api/orders/${order.id}/payment-proof`;
  document.getElementById('payment-verify-amount').textContent = `₹${order.total_amount.toFixed(2)}`;
  document.getElementById('payment-verify-customer').textContent = `${order.customer_name} (${order.customer_phone})`;
  document.getElementById('payment-verify-notes').value = '';

  const modal = document.getElementById('payment-verify-modal');
  if (modal) modal.classList.add('active');
}

function closePaymentVerifyModal() {
  const modal = document.getElementById('payment-verify-modal');
  if (modal) modal.classList.remove('active');
  currentVerifyOrderId = null;
}

async function handlePaymentDecision(decision) {
  if (!currentVerifyOrderId) return;
  const notes = document.getElementById('payment-verify-notes').value.trim();

  try {
    const res = await fetch(`/api/owner/orders/${currentVerifyOrderId}/verify-payment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision, notes })
    });

    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Payment verification failed.", "error");
      return;
    }

    showToast(`Payment ${decision.toLowerCase()}d!`, "success");
    closePaymentVerifyModal();
    loadOwnerOrders();
  } catch (err) {
    showToast("Network error.", "error");
  }
}

// Status Updates
async function updateOrderStatus(orderId, status) {
  try {
    const res = await fetch(`/api/owner/orders/${orderId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });

    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Failed to update status.", "error");
      return;
    }

    showToast(`Order marked as ${status}!`, "success");
    loadOwnerOrders();
  } catch (err) {
    showToast("Network error.", "error");
  }
}

// PRODUCT CATALOG MANAGEMENT
async function loadOwnerProducts() {
  try {
    const res = await fetch('/api/owner/products');
    adminProducts = await res.json();
    renderProductsTable();
  } catch (err) {
    console.error("Error loading products:", err);
  }
}

function renderProductsTable() {
  const tbody = document.getElementById('admin-products-tbody');
  if (!tbody) return;

  tbody.innerHTML = adminProducts.map(p => {
    let stockClass = 'stock-pill-good';
    if (p.stock <= 0) stockClass = 'stock-pill-zero';
    else if (p.stock <= 5) stockClass = 'stock-pill-low';

    const unitsList = (p.units || []).map(u => `${u.unit_name_en} (×${u.multiplier})`).join(', ');

    return `
      <tr>
        <td>
          <img src="${p.image_url || '/static/images/default.svg'}" style="width:36px; height:36px; object-fit:contain; border-radius:4px; vertical-align:middle; margin-right:0.5rem;" onerror="this.src='/static/images/default.svg'" />
          <strong>${p.name_en}</strong><br>
          <small style="color:#64748b;">${p.name_hi}</small>
        </td>
        <td>${p.category}</td>
        <td><strong>₹${p.base_price}</strong> / ${p.base_unit}</td>
        <td>
          <span class="stock-pill ${stockClass}">
            ${p.stock} ${p.base_unit}
          </span>
        </td>
        <td>
          <span style="font-size:0.75rem; color:#475569;">${unitsList}</span>
        </td>
        <td>
          <span style="color:${p.is_active ? '#15803d' : '#991b1b'}; font-weight:700;">
            ${p.is_active ? 'Active' : 'Inactive'}
          </span>
        </td>
        <td>
          <div style="display:flex; gap:0.3rem;">
            <button class="admin-btn admin-btn-outline" style="padding:0.25rem 0.5rem; font-size:0.75rem;" onclick="openRestockModal(${p.id})">
              ➕ Restock
            </button>
            <button class="admin-btn admin-btn-outline" style="padding:0.25rem 0.5rem; font-size:0.75rem;" onclick="openEditProductModal(${p.id})">
              ✏️ Edit
            </button>
            <button class="admin-btn admin-btn-outline" style="padding:0.25rem 0.5rem; font-size:0.75rem;" onclick="toggleProductActive(${p.id})">
              ${p.is_active ? '⏸️ Hide' : '▶️ Activate'}
            </button>
            <button class="admin-btn admin-btn-danger" style="padding:0.25rem 0.5rem; font-size:0.75rem;" onclick="deleteProduct(${p.id})">
              🗑️ Delete
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

// Delete Product
async function deleteProduct(prodId) {
  if (!confirm("Are you sure you want to permanently delete this product?")) return;
  try {
    const res = await fetch(`/api/owner/products/${prodId}`, { method: 'DELETE' });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || "Product deleted successfully!", "success");
      loadOwnerProducts();
    } else {
      showToast(data.error || "Failed to delete product.", "error");
    }
  } catch (err) {
    showToast("Network error.", "error");
  }
}

// Toggle Product Active
async function toggleProductActive(prodId) {
  try {
    const res = await fetch(`/api/owner/products/${prodId}/toggle-active`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, "success");
      loadOwnerProducts();
    }
  } catch (err) {
    showToast("Error updating product status.", "error");
  }
}

// Restock Modal Handlers
let currentRestockProdId = null;
function openRestockModal(prodId) {
  const prod = adminProducts.find(p => p.id === prodId);
  if (!prod) return;
  currentRestockProdId = prodId;
  document.getElementById('restock-prod-name').textContent = `${prod.name_en} (Current Stock: ${prod.stock} ${prod.base_unit})`;
  document.getElementById('restock-qty').value = '';
  document.getElementById('restock-modal').classList.add('active');
}

function closeRestockModal() {
  document.getElementById('restock-modal').classList.remove('active');
  currentRestockProdId = null;
}

async function submitRestock() {
  if (!currentRestockProdId) return;
  const qty = parseFloat(document.getElementById('restock-qty').value);
  if (!qty || qty <= 0) {
    showToast("Enter a positive quantity to restock.", "error");
    return;
  }

  try {
    const res = await fetch(`/api/owner/products/${currentRestockProdId}/restock`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quantity: qty })
    });
    const data = await res.json();
    if (res.ok) {
      showToast("Restocked successfully!", "success");
      closeRestockModal();
      loadOwnerProducts();
    } else {
      showToast(data.error || "Restock failed.", "error");
    }
  } catch (err) {
    showToast("Network error.", "error");
  }
}

// Product Add / Edit Modal
let editingProductId = null;

function openAddProductModal() {
  editingProductId = null;
  document.getElementById('product-modal-title').textContent = "Add New Grocery Product";
  document.getElementById('prod-form-name-en').value = '';
  document.getElementById('prod-form-name-hi').value = '';
  document.getElementById('prod-form-cat').value = 'Atta, Rice & Dals';
  document.getElementById('prod-form-price').value = '';
  document.getElementById('prod-form-unit').value = 'kg';
  document.getElementById('prod-form-stock').value = '20';
  document.getElementById('prod-form-img').value = '';
  document.getElementById('prod-form-desc-en').value = '';
  document.getElementById('prod-form-desc-hi').value = '';

  const fileInput = document.getElementById('prod-form-file');
  if (fileInput) fileInput.value = '';
  const previewContainer = document.getElementById('prod-img-preview-container');
  if (previewContainer) previewContainer.style.display = 'none';

  // Default units template for kg
  renderUnitRows([
    { name_en: '500g', name_hi: '५०० ग्राम', multiplier: 0.5 },
    { name_en: '1 kg', name_hi: '१ किलो', multiplier: 1.0 }
  ]);

  document.getElementById('product-modal').classList.add('active');
}

function openEditProductModal(prodId) {
  const prod = adminProducts.find(p => p.id === prodId);
  if (!prod) return;
  editingProductId = prodId;

  document.getElementById('product-modal-title').textContent = `Edit Product: ${prod.name_en}`;
  document.getElementById('prod-form-name-en').value = prod.name_en;
  document.getElementById('prod-form-name-hi').value = prod.name_hi;
  document.getElementById('prod-form-cat').value = prod.category;
  document.getElementById('prod-form-price').value = prod.base_price;
  document.getElementById('prod-form-unit').value = prod.base_unit;
  document.getElementById('prod-form-stock').value = prod.stock;
  document.getElementById('prod-form-img').value = prod.image_url || '';
  document.getElementById('prod-form-desc-en').value = prod.description_en || '';
  document.getElementById('prod-form-desc-hi').value = prod.description_hi || '';

  const fileInput = document.getElementById('prod-form-file');
  if (fileInput) fileInput.value = '';
  const preview = document.getElementById('prod-img-preview');
  const previewContainer = document.getElementById('prod-img-preview-container');
  if (preview && previewContainer) {
    if (prod.image_url) {
      preview.src = prod.image_url;
      previewContainer.style.display = 'block';
    } else {
      previewContainer.style.display = 'none';
    }
  }

  renderUnitRows(prod.units.map(u => ({
    name_en: u.unit_name_en,
    name_hi: u.unit_name_hi,
    multiplier: u.multiplier
  })));

  document.getElementById('product-modal').classList.add('active');
}

function closeProductModal() {
  document.getElementById('product-modal').classList.remove('active');
  editingProductId = null;
}

function renderUnitRows(units) {
  const container = document.getElementById('prod-units-container');
  if (!container) return;

  container.innerHTML = units.map((u, i) => `
    <div class="unit-edit-row" style="display:flex; gap:0.4rem; margin-bottom:0.4rem;">
      <input type="text" placeholder="Unit EN (e.g. 500g)" value="${u.name_en}" class="form-input unit-row-en" style="flex:2;" required />
      <input type="text" placeholder="Unit HI (e.g. ५०० ग्राम)" value="${u.name_hi}" class="form-input unit-row-hi" style="flex:2;" required />
      <input type="number" step="0.01" placeholder="Mult (e.g. 0.5)" value="${u.multiplier}" class="form-input unit-row-mult" style="flex:1;" required />
      <button type="button" onclick="this.parentElement.remove()" class="admin-btn admin-btn-danger" style="padding:0.2rem 0.6rem;">×</button>
    </div>
  `).join('');
}

function addUnitRow() {
  const container = document.getElementById('prod-units-container');
  const div = document.createElement('div');
  div.className = 'unit-edit-row';
  div.style.cssText = 'display:flex; gap:0.4rem; margin-bottom:0.4rem;';
  div.innerHTML = `
    <input type="text" placeholder="Unit EN (e.g. 1 kg)" class="form-input unit-row-en" style="flex:2;" required />
    <input type="text" placeholder="Unit HI (e.g. १ किलो)" class="form-input unit-row-hi" style="flex:2;" required />
    <input type="number" step="0.01" placeholder="Mult" value="1.0" class="form-input unit-row-mult" style="flex:1;" required />
    <button type="button" onclick="this.parentElement.remove()" class="admin-btn admin-btn-danger" style="padding:0.2rem 0.6rem;">×</button>
  `;
  container.appendChild(div);
}

async function saveProduct(event) {
  event.preventDefault();

  const name_en = document.getElementById('prod-form-name-en').value.trim();
  const name_hi = document.getElementById('prod-form-name-hi').value.trim();
  const category = document.getElementById('prod-form-cat').value.trim();
  const base_price = parseFloat(document.getElementById('prod-form-price').value);
  const base_unit = document.getElementById('prod-form-unit').value.trim();
  const stock = parseFloat(document.getElementById('prod-form-stock').value);
  const image_url = document.getElementById('prod-form-img').value.trim();
  const description_en = document.getElementById('prod-form-desc-en').value.trim();
  const description_hi = document.getElementById('prod-form-desc-hi').value.trim();

  // Collect units
  const unitRows = document.querySelectorAll('.unit-edit-row');
  const units = [];
  unitRows.forEach(row => {
    const en = row.querySelector('.unit-row-en').value.trim();
    const hi = row.querySelector('.unit-row-hi').value.trim();
    const mult = parseFloat(row.querySelector('.unit-row-mult').value);
    if (en && mult > 0) {
      units.push({ unit_name_en: en, unit_name_hi: hi || en, multiplier: mult });
    }
  });

  const payload = {
    name_en, name_hi, category, base_price, base_unit,
    stock, image_url, description_en, description_hi, units
  };

  const endpoint = editingProductId ? `/api/owner/products/${editingProductId}` : '/api/owner/products';
  const method = editingProductId ? 'PUT' : 'POST';

  try {
    const res = await fetch(endpoint, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (res.ok) {
      showToast(data.message, "success");
      closeProductModal();
      loadOwnerProducts();
    } else {
      showToast(data.error || "Failed to save product.", "error");
    }
  } catch (err) {
    showToast("Network error.", "error");
  }
}

// STORE SETTINGS
async function loadOwnerSettings() {
  try {
    const res = await fetch('/api/owner/settings');
    adminSettings = await res.json();

    document.getElementById('setting-delivery-charge').value = adminSettings.delivery_charge;
    document.getElementById('setting-min-order').value = adminSettings.min_order_amount;
    document.getElementById('setting-free-thresh').value = adminSettings.free_delivery_threshold;
    document.getElementById('setting-enable-home').checked = adminSettings.home_delivery_enabled === 1;
    document.getElementById('setting-enable-pickup').checked = adminSettings.store_pickup_enabled === 1;
    document.getElementById('setting-upi-id').value = adminSettings.upi_id;
    document.getElementById('setting-upi-instructions-en').value = adminSettings.upi_instructions_en || '';
    document.getElementById('setting-upi-instructions-hi').value = adminSettings.upi_instructions_hi || '';

    const qrUrl = adminSettings.upi_qr_url || '';
    const qrInput = document.getElementById('setting-upi-qr-url');
    if (qrInput) qrInput.value = qrUrl;
    const qrPreview = document.getElementById('qr-preview-img');
    const qrContainer = document.getElementById('qr-preview-container');
    if (qrPreview && qrContainer) {
      if (qrUrl) {
        qrPreview.src = qrUrl;
        qrContainer.style.display = 'block';
      } else {
        qrContainer.style.display = 'none';
      }
    }
  } catch (err) {
    console.error("Error loading settings:", err);
  }
}

async function saveOwnerSettings(event) {
  event.preventDefault();

  const qrInput = document.getElementById('setting-upi-qr-url');
  const upi_qr_url = qrInput ? qrInput.value.trim() : '';

  const payload = {
    delivery_charge: parseFloat(document.getElementById('setting-delivery-charge').value),
    min_order_amount: parseFloat(document.getElementById('setting-min-order').value),
    free_delivery_threshold: parseFloat(document.getElementById('setting-free-thresh').value),
    home_delivery_enabled: document.getElementById('setting-enable-home').checked,
    store_pickup_enabled: document.getElementById('setting-enable-pickup').checked,
    upi_id: document.getElementById('setting-upi-id').value.trim(),
    upi_qr_url: upi_qr_url,
    upi_instructions_en: document.getElementById('setting-upi-instructions-en').value.trim(),
    upi_instructions_hi: document.getElementById('setting-upi-instructions-hi').value.trim()
  };

  try {
    const res = await fetch('/api/owner/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (res.ok) {
      showToast(data.message, "success");
    } else {
      showToast(data.error || "Failed to update settings.", "error");
    }
  } catch (err) {
    showToast("Network error.", "error");
  }
}

// Direct Product Image Upload
async function handleProductImageUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  try {
    showToast("Uploading product image...", "info");
    const res = await fetch('/api/owner/upload', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (res.ok) {
      document.getElementById('prod-form-img').value = data.url;
      const preview = document.getElementById('prod-img-preview');
      const container = document.getElementById('prod-img-preview-container');
      if (preview && container) {
        preview.src = data.url;
        container.style.display = 'block';
      }
      showToast("Product image uploaded successfully!", "success");
    } else {
      showToast(data.error || "Failed to upload image.", "error");
    }
  } catch (err) {
    showToast("Error uploading product image.", "error");
  }
}

// Direct Store UPI QR Code Upload
async function handleQrCodeUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  try {
    showToast("Uploading QR code...", "info");
    const res = await fetch('/api/owner/upload', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (res.ok) {
      document.getElementById('setting-upi-qr-url').value = data.url;
      const preview = document.getElementById('qr-preview-img');
      const container = document.getElementById('qr-preview-container');
      if (preview && container) {
        preview.src = data.url;
        container.style.display = 'block';
      }
      showToast("QR code uploaded! Click 'Save Settings' to apply.", "success");
    } else {
      showToast(data.error || "Failed to upload QR code.", "error");
    }
  } catch (err) {
    showToast("Error uploading QR code.", "error");
  }
}

// Owner Password Change Handler
async function handleOwnerPasswordChange(event) {
  event.preventDefault();
  const current_password = document.getElementById('owner-curr-password').value.trim();
  const new_password = document.getElementById('owner-new-password').value.trim();
  const confirm_password = document.getElementById('owner-confirm-password').value.trim();

  if (!current_password || !new_password || !confirm_password) {
    showToast("All password fields are required.", "error");
    return;
  }

  if (new_password !== confirm_password) {
    showToast("New passwords do not match.", "error");
    return;
  }

  try {
    const res = await fetch('/api/owner/change-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password, new_password, confirm_password })
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || "Master password updated successfully!", "success");
      document.getElementById('owner-curr-password').value = '';
      document.getElementById('owner-new-password').value = '';
      document.getElementById('owner-confirm-password').value = '';
    } else {
      showToast(data.error || "Failed to update password.", "error");
    }
  } catch (err) {
    showToast("Network error changing password.", "error");
  }
}

async function handleOwnerLogout() {
  await fetch('/api/auth/logout', { method: 'POST' });
  window.location.href = '/owner/login';
}

document.addEventListener('DOMContentLoaded', () => {
  loadOwnerOrders();
  // Auto-refresh orders every 12 seconds
  pollInterval = setInterval(loadOwnerOrders, 12000);
});

window.addEventListener('beforeunload', () => {
  if (pollInterval) clearInterval(pollInterval);
});
