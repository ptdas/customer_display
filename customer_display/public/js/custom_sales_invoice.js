frappe.ui.form.on('Sales Invoice', {
	onload(frm) {
		if (frm.is_new() && frm.doc.is_return && frm.doc.return_against) {
			frm.set_value('is_pos', 0);
		}
	}
});
