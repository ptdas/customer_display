// frappe.ui.form.on('Purchase Receipt Item', {
//     item_code: async function(frm, cdt, cdn) {
//         // const row = locals[cdt][cdn];
//         // if (!row.item_code) return;

//         // // Get item's custom_vendor
//         // const item = await frappe.db.get_doc('Item', row.item_code);
//         // const vendor = item.custom_vendor;
//         // if (!vendor) return;

//         // // Get vendor's custom_vendor_company
//         // const supplier_doc = await frappe.db.get_doc('Supplier', vendor);
//         // const vendor_company = supplier_doc.custom_vendor_company;

//         // const current_supplier = frm.doc.supplier?.trim?.() || null;
//         // const current_company = frm.doc.company?.trim?.() || null;

//         // const total_items = (frm.doc.items || []).length;

//         // // Case 1: First item, allow override
//         // if (total_items === 1) {
//         //     await frm.set_value('supplier', vendor);
//         //     await frm.set_value('company', vendor_company);
//         // } 
//         // // Case 2: Enforce consistency
//         // else {
//         //     if (current_supplier && current_supplier !== vendor) {
//         //         frappe.throw(`Item ${row.item_code} is linked to supplier ${vendor}, but the invoice supplier is ${current_supplier}`);
//         //     }
//         //     if (current_company && current_company !== vendor_company) {
//         //         frappe.throw(`Item ${row.item_code} is linked to company ${vendor_company}, but the invoice company is ${current_company}`);
//         //     }
//         // }
//     }
// });

// frappe.ui.form.on('Purchase Receipt', {
//     items_remove: function(frm) {
//         if (!frm.doc.items || frm.doc.items.length === 0) {
//             frm.set_value('supplier', null);
//             frm.set_value('company', null);
//         }
//     }
// });


frappe.ui.form.on("Purchase Receipt", {
    validate: async function(frm) {
        if (!frm.__po_qty_confirmed) {
            let check_over_qty = [];

            for (let item of frm.doc.items || []) {
                if (item.purchase_order_item) {
                    const r = await frappe.call({
                        method: "customer_display.custom_standard.purchase_receipt_custom.get_po_item_qty",
                        args: { po_detail: item.purchase_order_item }
                    });

                    const po_qty = r.message;
                    if (item.qty > po_qty) {
                        check_over_qty.push(item.item_code);
                    }
                }
            }

            if (check_over_qty.length > 0) {
                frappe.confirm(
                    __("Qty diterima berbeda dengan PO sehingga akan jalan approval, apakah dilanjutkan?"),
                    function () {
                        frm.set_value("custom_po_qty_beda", 1);
                        frm.__po_qty_confirmed = true;
                        frm.save();
                    },
                    function () {
                        frappe.validated = false;
                    }
                );
                frappe.validated = false;
            }
        }
    }
});