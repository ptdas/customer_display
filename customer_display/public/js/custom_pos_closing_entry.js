frappe.ui.form.on("POS Closing Entry", {
	onload(frm) {
		frm.set_query("pos_opening_entry", () => {
			const user = frappe.session.user;
			const roles = frappe.user_roles || [];

			// If user has bypass role, return no filter
			if (roles.includes("99_ByPass Open POS")) {
				return {}; // No filter, show all
			}

			// Otherwise, filter by current user
			return {
				filters: {
					user: user
				}
			};
		});
	}
});