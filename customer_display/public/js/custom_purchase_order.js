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