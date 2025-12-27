// Only run if we're on the POS page
if (!location.pathname.startsWith("/app/point-of-sale")) {
  return;
}



function clearCustomerDisplayCart() {
  frappe.call({
    method: "customer_display.api.clear_customer_display",
    freeze: false
  });
}

function patchPOSUpdateCart() {
  const Controller = erpnext?.PointOfSale?.Controller;

  if (typeof Controller !== "function") {
    return false;
  }

  if (Controller.prototype._customer_display_patched) {
    return true;
  }

  const original_update_cart_html = Controller.prototype.update_cart_html;

  Controller.prototype.update_cart_html = function () {
    
    original_update_cart_html.apply(this, arguments);

    const cart_items = this.frm.doc.items.map(item => ({
      item_code: item.item_code,
      item_name: item.item_name,
      qty: item.qty,
      rate: item.rate
    }));

    frappe.call({
      method: "customer_display.api.update_customer_display",
      args: { 
        pos_profile: this.frm.doc.pos_profile,
        items: cart_items 
      },
      freeze: false
    });
  };

  Controller.prototype._customer_display_patched = true;

  // 👇 Clear display on POS init
  // clearCustomerDisplayCart();

  return true;
}

function ensurePOSPatched(retries = 40) {
  if (!patchPOSUpdateCart() && retries > 0) {
    setTimeout(() => ensurePOSPatched(retries - 1), 500);
  }
}

frappe.router.on('change', () => {
  if (frappe.get_route()[0] === "pos") {
    ensurePOSPatched();
  }
});

// Initial check in case POS was already loaded
ensurePOSPatched();
