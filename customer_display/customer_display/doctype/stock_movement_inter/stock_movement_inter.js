frappe.ui.form.on("Stock Movement Inter", {
	onload(frm) {
		frm.set_query("source_company", () => ({
			filters: { parent_company: ["is", "not set"] }
		}));

		frm.set_query("target_company", () => ({
			filters: { parent_company: ["is", "not set"] }
		}));

		frm.set_query("from_warehouse", () => ({
			filters: { company: frm.doc.source_company || "" }
		}));

		frm.set_query("to_warehouse", () => ({
			filters: { company: frm.doc.target_company || "" }
		}));
	},

    source_company(frm) {
        frm.set_value("from_warehouse", null);

        if (frm.doc.items && frm.doc.items.length) {
            frm.doc.items.forEach(row => {
                if (row.item_code) {
                    handle_item_code(frm, row.doctype, row.name, "source");
                }
            });
        }
    },

    target_company(frm) {
        frm.set_value("to_warehouse", null);

        if (frm.doc.items && frm.doc.items.length) {
            frm.doc.items.forEach(row => {
                if (row.item_code) {
                    handle_item_code(frm, row.doctype, row.name, "target");
                }
            });
        }
    },

    from_warehouse(frm){
        if (frm.doc.items && frm.doc.items.length) {
            frm.doc.items.forEach(row => {
                if (row.item_code) {
                    handle_item_code(frm, row.doctype, row.name, "source");
                }
            });
        }
    },
    to_warehouse(frm){
        if (frm.doc.items && frm.doc.items.length) {
            frm.doc.items.forEach(row => {
                if (row.item_code) {
                    handle_item_code(frm, row.doctype, row.name, "target");
                }
            });
        }
    }

});

frappe.ui.form.on("Stock Movement Inter Detail", {
	item_code(frm, cdt, cdn) {
		handle_item_code(frm, cdt, cdn);
	}
});

function handle_item_code(frm, cdt, cdn, direction) {
    let row = locals[cdt][cdn];
    if (!row.item_code) return;

    if (!direction || direction === "source") {
        if (frm.doc.source_company) {
            frappe.call({
                method: "customer_display.customer_display.doctype.stock_movement_inter.stock_movement_inter.get_vendor_company_and_default_warehouse",
                args: { item_code: row.item_code, parent_company: frm.doc.source_company, input_warehouse: frm.doc.from_warehouse },
                callback(r) {
                    console.log(r.message);
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, "from_company", r.message.company);
                        frappe.model.set_value(cdt, cdn, "s_warehouse", r.message.warehouse);
                        frappe.model.set_value(cdt, cdn, "rate", r.message.rate);
                        frm.refresh_field("items"); 
                    }
                }
            });
        }
    }

    if (!direction || direction === "target") {
        if (frm.doc.target_company) {
            frappe.call({
                method: "customer_display.customer_display.doctype.stock_movement_inter.stock_movement_inter.get_vendor_company_and_default_warehouse",
                args: { item_code: row.item_code, parent_company: frm.doc.target_company, input_warehouse: frm.doc.to_warehouse },
                callback(r) {
                    console.log(r.message);
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, "to_company", r.message.company);
                        frappe.model.set_value(cdt, cdn, "t_warehouse", r.message.warehouse);
                        frappe.model.set_value(cdt, cdn, "rate", r.message.rate);
                        frm.refresh_field("items"); 
                    }
                }
            });
        }
    }
}

