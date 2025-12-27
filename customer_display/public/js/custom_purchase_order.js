frappe.ui.form.on('Purchase Order Item', {
  
  item_code: async function(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row.item_code) return;

    // now await is allowed
    const item = await frappe.db.get_doc('Item', row.item_code);
    const vendor = item.custom_vendor;
    if (!vendor) return;

    const supplier_doc = await frappe.db.get_doc('Supplier', vendor);
    const vendor_company = supplier_doc.custom_vendor_company;

    await frm.set_value('supplier', vendor);
    await frm.set_value('company', vendor_company);
  }

});

frappe.ui.form.on('Purchase Order', {
  supplier: async function(frm) {
    const supplier = frm.doc.supplier;
    if (!supplier) return;

    const supplier_doc = await frappe.db.get_doc('Supplier', supplier);
    const vendor_company = supplier_doc.custom_vendor_company;

    if (vendor_company) {
      await frm.set_value('company', vendor_company);
    }
  },

  items_remove: function(frm) {
    if (!frm.doc.items || frm.doc.items.length === 0) {
      frm.set_value('supplier', null);
      frm.set_value('company', null);
    }
  },

  refresh: function(frm){
    hide_perm(frm);
  }

});

function hide_perm(frm) {

    let max_perm_level = frappe.boot.max_perm_level

    if(max_perm_level < 8 && frappe.session.user != "Administrator"){
        setTimeout(() => {
            frm.remove_custom_button(__("Payment"), __("Create"));
            frm.remove_custom_button(__("Payment Request"), __("Create"));
        }, 300);
    }

    if(max_perm_level < 7 && frappe.session.user != "Administrator"){
        frm.set_df_property('naming_series', 'read_only', true);
        frm.set_df_property('transaction_date', 'read_only', true);
        frm.set_df_property('cost_center', 'read_only', true);
        frm.set_df_property('project', 'read_only', true);
    }

}