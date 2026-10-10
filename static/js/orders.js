// Yadav General Store - Customer Order Tracking & Payment Gating Logic
let myOrders = [];
let pollingInterval = null;

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

async function loadMyOrders() {
  try {
    const urlParams = new URLSearchParams(window.location.search);
    const guestToken = urlParams.get('token') || '';

    let url = '/api/my-orders';
    if (guestToken) {
      url += `?token=${encodeURIComponent(guestToken)}`;
    }

    const res = await fetch(url);
    if (!res.ok) {
      throw new Error("Failed to load orders");
    }

    myOrders = await res.json();
    renderOrdersList();
  } catch (err) {
    console.error("Error loading orders:", err);
  }
}

function renderOrdersList() {
  const container = document.getElementById('orders-container');
  if (!container) return;

  if (myOrders.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding: 4rem 1rem; background:white; border-radius:12px; border:1px solid #e2e8f0;">
        <p style="font-size:3rem; margin-bottom:0.5rem;">📦</p>
        <h3 data-i18n="noOrders">${t('noOrders')}</h3>
        <p style="color:#64748b; margin-top:0.5rem;">Browse our fresh products and place your first order!</p>
        <a href="/" class="add-btn" style="display:inline-block; margin-top:1rem; text-decoration:none; padding:0.6rem 1.2rem;">
          🛒 Start Shopping
        </a>
      </div>
    `;
    return;
  }

  const isHindi = currentLang === 'hi';

  container.innerHTML = myOrders.map(order => {
    const statusMap = {
      'PENDING_OWNER_APPROVAL': { text: t('orderStatusPending'), class: 'status-PENDING_OWNER_APPROVAL' },
      'ACCEPTED': { text: t('orderStatusAccepted'), class: 'status-ACCEPTED' },
      'PAYMENT_PENDING': { text: t('orderStatusPaymentPending'), class: 'status-PAYMENT_PENDING' },
      'PAYMENT_VERIFIED': { text: t('orderStatusPaymentVerified'), class: 'status-PAYMENT_VERIFIED' },
      'PROCESSING': { text: t('orderStatusProcessing'), class: 'status-PROCESSING' },
      'COMPLETED': { text: t('orderStatusCompleted'), class: 'status-COMPLETED' },
      'REJECTED': { text: t('orderStatusRejected'), class: 'status-REJECTED' },
      'CANCELLED': { text: t('orderStatusCancelled'), class: 'status-CANCELLED' }
    };

    const currentStatus = statusMap[order.status] || { text: order.status, class: '' };

    // Format items
    const itemsHtml = (order.items || []).map(item => {
      const pName = isHindi ? item.product_name_hi : item.product_name_en;
      const uName = isHindi ? item.unit_name_hi : item.unit_name_en;
      return `
        <div style="display:flex; justify-content:space-between; padding:0.35rem 0; border-bottom:1px dashed #f1f5f9; font-size:0.875rem;">
          <span>${pName} (${uName}) × ${item.quantity}</span>
          <span style="font-weight:700;">₹${item.item_total.toFixed(2)}</span>
        </div>
      `;
    }).join('');

    // Payment Section Render (Strict UPI Gating - Req 3 & 4)
    let paymentSectionHtml = '';

    if (order.payment_method === 'ONLINE_UPI') {
      if (order.status === 'PENDING_OWNER_APPROVAL') {
        paymentSectionHtml = `
          <div style="background:#fef3c7; border:1.5px dashed #f59e0b; border-radius:8px; padding:1rem; margin-top:1rem;">
            <div style="font-weight:700; color:#b45309; display:flex; align-items:center; gap:0.5rem;">
              ⏳ <span>${t('orderStatusPending')}</span>
            </div>
            <p style="font-size:0.85rem; color:#92400e; margin-top:0.4rem;">
              The store owner is reviewing stock and confirming your order.
              <strong>Online UPI details & QR code will unlock here immediately upon store approval.</strong>
            </p>
          </div>
        `;
      } else if (order.status === 'ACCEPTED' && order.upi_details) {
        // Unlocked UPI Gated Section!
        const upi = order.upi_details;
        const qrImgSrc = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(upi.pay_uri)}`;

        paymentSectionHtml = `
          <div style="background:#eff6ff; border:2px solid #3b82f6; border-radius:10px; padding:1.25rem; margin-top:1rem;">
            <div style="font-weight:800; color:#1d4ed8; font-size:1.05rem; margin-bottom:0.5rem; display:flex; align-items:center; gap:0.5rem;">
              🎉 <span>Order Accepted! Complete Your Payment</span>
            </div>
            <p style="font-size:0.875rem; color:#1e40af; margin-bottom:0.75rem;">
              ${isHindi ? (upi.upi_instructions_hi || upi.upi_instructions_en) : upi.upi_instructions_en}
            </p>

            <div style="display:grid; grid-template-columns:auto 1fr; gap:1.25rem; align-items:center; background:white; padding:1rem; border-radius:8px; border:1px solid #bfdbfe; margin-bottom:1rem;">
              <div style="text-align:center;">
                <img src="${qrImgSrc}" alt="UPI QR Code" style="width:140px; height:140px; border-radius:8px; border:1px solid #e2e8f0; display:block;" />
                <span style="font-size:0.75rem; color:#64748b; margin-top:0.3rem; display:block;">Scan with GPay/PhonePe</span>
              </div>
              <div>
                <div style="font-size:0.85rem; color:#64748b;">Payable Amount:</div>
                <div style="font-size:1.6rem; font-weight:800; color:#15803d; margin-bottom:0.4rem;">₹${order.total_amount.toFixed(2)}</div>
                
                <div style="font-size:0.85rem; color:#64748b;">Store UPI ID:</div>
                <div style="display:flex; align-items:center; gap:0.5rem; margin-top:0.2rem;">
                  <code style="background:#f1f5f9; padding:0.3rem 0.5rem; border-radius:6px; font-weight:700; color:#0f172a;">${upi.upi_id}</code>
                  <button onclick="copyToClipboard('${upi.upi_id}')" class="admin-btn admin-btn-outline" style="padding:0.25rem 0.6rem; font-size:0.75rem;">
                    📋 Copy
                  </button>
                </div>

                <a href="${upi.pay_uri}" class="admin-btn admin-btn-primary" style="display:inline-block; margin-top:0.75rem; text-decoration:none; padding:0.4rem 0.8rem; font-size:0.8rem;">
                  📱 Open UPI App to Pay
                </a>
              </div>
            </div>

            <!-- Screenshot Upload Form -->
            <form id="upload-form-${order.id}" onsubmit="handleScreenshotUpload(event, ${order.id})" style="background:white; padding:1rem; border-radius:8px; border:1px solid #bfdbfe;">
              <label style="display:block; font-weight:700; font-size:0.85rem; margin-bottom:0.3rem; color:#1e3a8a;">
                📤 ${t('uploadScreenshot')}
              </label>
              <p style="font-size:0.75rem; color:#64748b; margin-bottom:0.5rem;">Upload a screenshot of the successful payment transaction screen.</p>
              <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
                <input type="file" id="screenshot-file-${order.id}" accept="image/*" required style="font-size:0.85rem; padding:0.35rem; flex:1;" />
                <button type="submit" class="admin-btn admin-btn-success" id="upload-submit-btn-${order.id}">
                  ${t('uploadBtn')}
                </button>
              </div>
            </form>
          </div>
        `;
      } else if (order.status === 'PAYMENT_PENDING') {
        paymentSectionHtml = `
          <div style="background:#f5f3ff; border:1.5px solid #a855f7; border-radius:8px; padding:1rem; margin-top:1rem;">
            <div style="font-weight:700; color:#6b21a8; display:flex; align-items:center; gap:0.5rem;">
              ⏳ <span>Payment Proof Submitted</span>
            </div>
            <p style="font-size:0.85rem; color:#7e22ce; margin-top:0.4rem;">
              Your payment screenshot is under review by the store owner. Your order will be prepared as soon as it is confirmed.
            </p>
            ${order.payment_screenshot_url ? `
              <div style="margin-top:0.75rem;">
                <a href="/api/orders/${order.id}/payment-proof" target="_blank" style="font-size:0.8rem; color:#6b21a8; text-decoration:underline;">
                  🔍 View Submitted Screenshot
                </a>
              </div>
            ` : ''}
          </div>
        `;
      } else if (order.status === 'PAYMENT_VERIFIED' || order.status === 'PROCESSING' || order.status === 'COMPLETED') {
        paymentSectionHtml = `
          <div style="background:#dcfce7; border:1.5px solid #22c55e; border-radius:8px; padding:0.85rem; margin-top:1rem;">
            <div style="font-weight:700; color:#15803d; display:flex; align-items:center; gap:0.5rem;">
              ✅ <span>Online Payment Verified</span>
            </div>
            <p style="font-size:0.85rem; color:#166534; margin-top:0.25rem;">
              Payment of ₹${order.total_amount.toFixed(2)} received and confirmed.
            </p>
          </div>
        `;
      }
    } else {
      // COD or Store Pickup (Independent from UPI - Req 4)
      paymentSectionHtml = `
        <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:0.85rem; margin-top:1rem;">
          <div style="font-weight:700; color:#334155; font-size:0.9rem;">
            💵 Payment Mode: ${order.payment_method === 'COD' ? 'Cash on Delivery (Pay at Doorstep)' : 'Pay at Store upon Pickup'}
          </div>
          <p style="font-size:0.8rem; color:#64748b; margin-top:0.25rem;">
            Please keep exact cash ₹${order.total_amount.toFixed(2)} ready upon receiving your order.
          </p>
        </div>
      `;
    }

    if (order.status === 'REJECTED') {
      paymentSectionHtml = `
        <div style="background:#fee2e2; border:1.5px solid #ef4444; border-radius:8px; padding:1rem; margin-top:1rem;">
          <div style="font-weight:700; color:#b91c1c;">❌ ${t('orderStatusRejected')}</div>
          <p style="font-size:0.85rem; color:#991b1b; margin-top:0.25rem;">
            ${order.payment_notes || 'The store was unable to fulfill this order at this time. Stock has been preserved.'}
          </p>
        </div>
      `;
    }

    return `
      <div class="order-card-admin" id="order-card-${order.id}">
        <div class="order-card-header">
          <div>
            <div class="order-num-tag">${order.order_number}</div>
            <div class="order-date-tag">${new Date(order.created_at).toLocaleString()}</div>
          </div>
          <div>
            <span class="status-badge ${currentStatus.class}">${currentStatus.text}</span>
          </div>
        </div>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:0.75rem; font-size:0.875rem;">
          <div>
            <span style="color:#64748b;">Delivery Mode:</span>
            <strong style="color:#0f172a; display:block;">
              ${order.delivery_type === 'HOME_DELIVERY' ? '🚚 Home Delivery' : '🏬 Store Pickup'}
            </strong>
            ${order.delivery_address ? `
              <div style="margin-top:0.25rem; color:#475569; font-size:0.8rem;">
                📍 ${order.delivery_address}
              </div>
            ` : ''}
            ${order.special_instructions ? `
              <div style="margin-top:0.25rem; font-size:0.8rem; color:#d97706;">
                📝 Note: "${order.special_instructions}"
              </div>
            ` : ''}
          </div>
          <div>
            <span style="color:#64748b;">Customer:</span>
            <strong style="color:#0f172a; display:block;">${order.customer_name} (${order.customer_phone})</strong>
            <span style="color:#64748b; margin-top:0.25rem; display:block;">Total Amount:</span>
            <strong style="color:#15803d; font-size:1.15rem;">₹${order.total_amount.toFixed(2)}</strong>
          </div>
        </div>

        <div style="background:#f8fafc; padding:0.75rem; border-radius:8px; border:1px solid #e2e8f0; margin-bottom:0.5rem;">
          <div style="font-weight:700; font-size:0.85rem; color:#475569; margin-bottom:0.4rem;" data-i18n="itemsOrdered">
            ${t('itemsOrdered')}:
          </div>
          ${itemsHtml}
        </div>

        ${paymentSectionHtml}
      </div>
    `;
  }).join('');
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast("UPI ID copied to clipboard!", "success");
  }).catch(() => {
    showToast(`UPI ID: ${text}`, "info");
  });
}

async function handleScreenshotUpload(event, orderId) {
  event.preventDefault();
  const fileInput = document.getElementById(`screenshot-file-${orderId}`);
  if (!fileInput || !fileInput.files[0]) {
    showToast("Please choose a screenshot image.", "error");
    return;
  }

  const submitBtn = document.getElementById(`upload-submit-btn-${orderId}`);
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Uploading...";
  }

  const formData = new FormData();
  formData.append('screenshot', fileInput.files[0]);

  const urlParams = new URLSearchParams(window.location.search);
  const guestToken = urlParams.get('token') || '';
  if (guestToken) {
    formData.append('token', guestToken);
  }

  try {
    const res = await fetch(`/api/orders/${orderId}/upload-payment`, {
      method: 'POST',
      body: formData
    });

    const result = await res.json();
    if (!res.ok) {
      showToast(result.error || "Upload failed.", "error");
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = t('uploadBtn');
      }
      return;
    }

    showToast(t('uploadSuccess'), "success");
    await loadMyOrders();
  } catch (err) {
    console.error("Upload error:", err);
    showToast("Network error while uploading.", "error");
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = t('uploadBtn');
    }
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

document.addEventListener('DOMContentLoaded', () => {
  loadMyOrders();
  loadNotifications();
  // Auto-poll every 12 seconds for order updates & notifications
  pollingInterval = setInterval(() => {
    loadMyOrders();
    loadNotifications();
  }, 12000);
});

window.addEventListener('beforeunload', () => {
  if (pollingInterval) clearInterval(pollingInterval);
});
