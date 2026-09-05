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
    refresh: function(frm){
        frm.set_df_property(
			"additional_discount_percentage",
			"hidden",
			1
		);

		frm.set_df_property(
			"discount_amount",
			"hidden",
			1
		);

		setup_discount_input(frm);
    },
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




function setup_discount_input(frm) {
	setup_single_discount_input(
		frm,
		"custom_additional_discount_percentage_data",
		"additional_discount_percentage"
	);

	setup_single_discount_input(
		frm,
		"custom_additional_discount_amount_data",
		"discount_amount"
	);
}


function setup_single_discount_input(
	frm,
	custom_field,
	original_field
) {
	const field = frm.fields_dict[custom_field];

	if (!field || !field.$wrapper) {
		return;
	}

	const input = field.$wrapper.find("input");

	if (!input.length) {
		return;
	}

	input.off(".discount_input");

	input.on("input.discount_input", function () {
		let value = this.value;

		value = value.replace(/[^0-9.]/g, "");

		const first_dot = value.indexOf(".");

		if (first_dot !== -1) {
			value =
				value.substring(0, first_dot + 1) +
				value.substring(first_dot + 1).replace(/\./g, "");
		}

		if (this.value !== value) {
			this.value = value;
		}

		frm.doc[custom_field] = value;

		const number_value =
			value === ""
				? 0
				: parseFloat(value);

		frm.set_value(
			original_field,
			number_value
		);

		setTimeout(() => {
			sync_other_custom_field(
				frm,
				custom_field
			);
		}, 300);
	});
}


function sync_other_custom_field(
	frm,
	changed_custom_field
) {
	if (
		changed_custom_field ===
		"custom_additional_discount_percentage_data"
	) {
		const amount = frm.doc.discount_amount;

		set_custom_input_value(
			frm,
			"custom_additional_discount_amount_data",
			amount
		);

		return;
	}


	if (
		changed_custom_field ===
		"custom_additional_discount_amount_data"
	) {
		const percentage =
			frm.doc.additional_discount_percentage;

		set_custom_input_value(
			frm,
			"custom_additional_discount_percentage_data",
			percentage
		);
	}
}


function set_custom_input_value(
	frm,
	fieldname,
	value
) {
	const field = frm.fields_dict[fieldname];

	if (!field || !field.$wrapper) {
		return;
	}

	const input = field.$wrapper.find("input");

	if (!input.length) {
		return;
	}

	let display_value = "";

	if (
		value !== undefined &&
		value !== null &&
		value !== 0
	) {
		display_value = String(value);
	}

	input.val(display_value);

	frm.doc[fieldname] = display_value;
}