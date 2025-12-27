
frappe.ui.form.on('Supplier', {
	refresh(frm) {
        hide_perm(frm)
	},
	onload(frm) {
		if (!frappe.user.has_role('Tax Strategic')) {
		 	frm.set_df_property('custom_vendor_company', 'read_only', true);
		}
	},
	custom_pkp_type(frm){
		set_vendor_company(frm)
	}
});


function set_vendor_company(frm) {
	const can_edit = frappe.user.has_role('Tax Strategic');
	frm.toggle_enable('custom_vendor_company', can_edit);

	let settings_field = null;
	if (frm.doc.custom_pkp_type === 'PKP') {
		settings_field = 'default_target_pkp_company';
	} else if (frm.doc.custom_pkp_type === 'Non') {
		settings_field = 'default_target_pitza_company';
	}

	if (settings_field) {
		frappe.db
			.get_single_value('AXTRA Settings', settings_field)
			.then(value => {
				if (value) {
					frm.set_value('custom_vendor_company', value);
				}
			})
			.catch(() => {

			});
	}
}


function hide_perm(frm) {

	let max_perm_level = frappe.boot.max_perm_level
	if(max_perm_level < 8 && frappe.session.user != "Administrator"){
		$('.form-tabs .nav-link:contains("Dashboard")').parent().hide();
		$('.form-tabs .nav-link:contains("Tax")').parent().hide();
		$('.form-tabs .nav-link:contains("Settings")').parent().hide();
		$('.form-tabs .nav-link:contains("Portal Users")').parent().hide();
	}
	if(max_perm_level < 7){
		frm.set_df_property('payment_terms', 'read_only', true);
		frm.set_df_property('accounts', 'read_only', true);
	}
}

