const translations = {
  en: {
    storeName: "Yadav General Store",
    storeTagline: "Fresh Groceries & Daily Needs Delivered to Your Doorstep",
    navHome: "Store",
    navOrders: "My Orders",
    navCart: "Cart",
    navLogin: "Login",
    navRegister: "Register",
    navLogout: "Logout",
    navOwner: "Store Owner",
    searchPlaceholder: "Search groceries (Atta, Rice, Dal, Spices, Oil...)",
    allCategories: "All Items",
    catAtta: "Atta, Rice & Dals",
    catSpices: "Spices & Masalas",
    catOils: "Oils & Ghee",
    catDairy: "Dairy & Bakery",
    catSnacks: "Snacks & Biscuits",
    catBeverages: "Beverages & Tea",
    inStock: "In Stock",
    outOfStock: "Out of Stock",
    lowStock: "Only {n} left",
    selectUnit: "Choose Pack/Weight",
    addToCart: "Add to Cart",
    cartTitle: "Your Shopping Cart",
    cartEmpty: "Your cart is empty.",
    itemsCount: "{n} items",
    subtotal: "Subtotal",
    deliveryFee: "Delivery Charge",
    freeDelivery: "FREE Delivery",
    freeDeliveryNote: "Add ₹{n} more for FREE delivery!",
    totalAmount: "Total Payable",
    proceedCheckout: "Proceed to Checkout",
    checkoutTitle: "Complete Your Order",
    deliveryMode: "Delivery Mode",
    homeDelivery: "Home Delivery",
    storePickup: "Store Pickup",
    fullName: "Full Name",
    phone: "Mobile Number",
    address: "Delivery Address (Flat, Street, Landmark)",
    addressPlaceholder: "e.g., House #12, Gali No. 3, Near Temple",
    specialInstructions: "Special Instructions (Optional)",
    instructionsPlaceholder: "e.g., Deliver before 6 PM, call upon arrival...",
    paymentMethod: "Payment Method",
    onlineUpi: "Pay via Online UPI (GPay / PhonePe / Paytm)",
    cod: "Cash on Delivery (COD)",
    payAtStore: "Pay at Store on Pickup",
    placeOrderBtn: "Confirm & Place Order",
    minOrderNotice: "Minimum order amount is ₹{n}",
    orderStatusPending: "Pending Owner Approval",
    orderStatusAccepted: "Accepted by Store",
    orderStatusPaymentPending: "Payment Screenshot Uploaded",
    orderStatusPaymentVerified: "Payment Verified",
    orderStatusProcessing: "Preparing Order",
    orderStatusCompleted: "Completed & Delivered",
    orderStatusRejected: "Order Rejected",
    orderStatusCancelled: "Cancelled",
    upiPaymentTitle: "Online UPI Payment Instructions",
    upiCopyBtn: "Copy UPI ID",
    upiScanQr: "Scan QR Code to Pay",
    upiExactAmount: "Pay Exact Amount: ₹{amount}",
    uploadScreenshot: "Upload Payment Screenshot",
    uploadBtn: "Submit Payment Proof",
    uploadSuccess: "Payment screenshot submitted! Owner will verify shortly.",
    statusTimeline: "Order Tracking",
    orderNum: "Order ID: {num}",
    placedOn: "Placed on: {date}",
    itemsOrdered: "Items Ordered",
    noOrders: "No orders placed yet.",
    trackOrderBtn: "View Status",
    guestNotice: "Ordering as Guest. Save this link or register to access orders anytime.",
    stockWarning: "Only {stock} available for {name}.",
    insufficientStock: "Sorry, this product is currently out of stock.",
    notificationsTitle: "Notifications",
    markAllRead: "Mark All Read",
    noNotifications: "No notifications yet"
  },
  hi: {
    storeName: "यादव जनरल स्टोर",
    storeTagline: "ताज़ा किराना और दैनिक ज़रूरत का सामान आपके दरवाज़े तक",
    navHome: "दुकान",
    navOrders: "मेरे ऑर्डर",
    navCart: "थैला (कार्ट)",
    navLogin: "लॉग इन",
    navRegister: "पंजीकरण",
    navLogout: "लॉग आउट",
    navOwner: "दुकानदार पोर्टल",
    searchPlaceholder: "किराना खोजें (आटा, चावल, दाल, मसाले, तेल...)",
    allCategories: "सभी सामान",
    catAtta: "अनाज और दालें",
    catSpices: "मसाले",
    catOils: "तेल और घी",
    catDairy: "डेयरी",
    catSnacks: "नमकीन और बिस्कुट",
    catBeverages: "चाय और पेय",
    inStock: "उपलब्ध है",
    outOfStock: "स्टॉक समाप्त",
    lowStock: "केवल {n} बचा है",
    selectUnit: "पैकेट/वजन चुनें",
    addToCart: "थैले में जोड़ें",
    cartTitle: "आपका किराना थैला",
    cartEmpty: "आपका थैला खाली है।",
    itemsCount: "{n} सामान",
    subtotal: "सामान का मूल्य",
    deliveryFee: "डिलीवरी शुल्क",
    freeDelivery: "मुफ्त डिलीवरी",
    freeDeliveryNote: "मुफ्त डिलीवरी के लिए ₹{n} का सामान और जोड़ें!",
    totalAmount: "कुल देय राशि",
    proceedCheckout: "ऑर्डर करने के लिए आगे बढ़ें",
    checkoutTitle: "ऑर्डर विवरण भरें",
    deliveryMode: "डिलीवरी का प्रकार",
    homeDelivery: "घर पर डिलीवरी",
    storePickup: "दुकान से खुद लें",
    fullName: "पूरा नाम",
    phone: "मोबाइल नंबर",
    address: "डिलीवरी का पूरा पता (मकान नं., गली, लैंडमार्क)",
    addressPlaceholder: "उदा. मकान नं. १२, गली नं. ३, मंदिर के पास",
    specialInstructions: "विशेष निर्देश (वैकल्पिक)",
    instructionsPlaceholder: "उदा. शाम ६ बजे से पहले लाएं, फोन करके आएं...",
    paymentMethod: "भुगतान का तरीका",
    onlineUpi: "ऑनलाइन यूपीआई (GPay / PhonePe / Paytm)",
    cod: "कैश ऑन डिलीवरी (सामान मिलने पर नकद)",
    payAtStore: "दुकान पर भुगतान (पिकअप के समय)",
    placeOrderBtn: "ऑर्डर पक्का करें",
    minOrderNotice: "न्यूनतम ऑर्डर राशि ₹{n} है",
    orderStatusPending: "दुकानदार की स्वीकृति की प्रतीक्षा",
    orderStatusAccepted: "दुकानदार द्वारा स्वीकृत",
    orderStatusPaymentPending: "भुगतान स्क्रीनशॉट भेजा गया",
    orderStatusPaymentVerified: "भुगतान सत्यापित",
    orderStatusProcessing: "सामान पैक हो रहा है",
    orderStatusCompleted: "डिलीवर / प्राप्त हुआ",
    orderStatusRejected: "ऑर्डर निरस्त",
    orderStatusCancelled: "रद्द",
    upiPaymentTitle: "ऑनलाइन यूपीआई भुगतान निर्देश",
    upiCopyBtn: "यूपीआई आईडी कॉपी करें",
    upiScanQr: "क्यूआर कोड स्कैन करके भुगतान करें",
    upiExactAmount: "सटीक राशि भेजें: ₹{amount}",
    uploadScreenshot: "भुगतान का स्क्रीनशॉट अपलोड करें",
    uploadBtn: "प्रमाण जमा करें",
    uploadSuccess: "भुगतान स्क्रीनशॉट जमा हो गया! दुकानदार जल्द सत्यापित करेंगे।",
    statusTimeline: "ऑर्डर स्थिति",
    orderNum: "ऑर्डर संख्या: {num}",
    placedOn: "ऑर्डर दिनांक: {date}",
    itemsOrdered: "मंगवाया गया सामान",
    noOrders: "अभी तक कोई ऑर्डर नहीं मिला।",
    trackOrderBtn: "स्थिति देखें",
    guestNotice: "आप अतिथि के रूप में ऑर्डर कर रहे हैं। ऑर्डर कभी भी देखने के लिए यह लिंक सुरक्षित रखें।",
    stockWarning: "{name} के लिए केवल {stock} उपलब्ध है।",
    insufficientStock: "माफ़ करें, यह सामान अभी स्टॉक में नहीं है।",
    notificationsTitle: "सूचनाएं",
    markAllRead: "सभी पढ़ी गईं",
    noNotifications: "कोई नई सूचना नहीं है"
  }
};

let currentLang = localStorage.getItem("ygs_lang") || "en";

function setLanguage(lang) {
  currentLang = lang;
  localStorage.setItem("ygs_lang", lang);
  document.documentElement.lang = lang;
  updatePageText();
  if (typeof renderProducts === "function") renderProducts();
  if (typeof renderCart === "function") renderCart();
  if (typeof renderOrdersList === "function") renderOrdersList();
  if (typeof updateLangButtonUI === "function") updateLangButtonUI();
}

function t(key, params = {}) {
  let str = (translations[currentLang] && translations[currentLang][key]) || (translations["en"] && translations["en"][key]) || key;
  for (const [k, v] of Object.entries(params)) {
    str = str.replace(new RegExp(`\\{${k}\\}`, "g"), v);
  }
  return str;
}

function updatePageText() {
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    el.textContent = t(key);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    const key = el.getAttribute("data-i18n-placeholder");
    el.placeholder = t(key);
  });
}

function updateLangButtonUI() {
  const btnEn = document.getElementById("lang-en-btn");
  const btnHi = document.getElementById("lang-hi-btn");
  if (btnEn && btnHi) {
    if (currentLang === "hi") {
      btnHi.classList.add("active-lang");
      btnEn.classList.remove("active-lang");
    } else {
      btnEn.classList.add("active-lang");
      btnHi.classList.remove("active-lang");
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  updatePageText();
  updateLangButtonUI();
});
