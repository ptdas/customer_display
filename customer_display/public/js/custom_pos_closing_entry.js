frappe.ui.form.on("POS Closing Entry", {
	onload(frm) {
		frm.set_query("pos_opening_entry", () => {
			const user = frappe.session.user;
			const roles = frappe.user_roles || [];

			let filters = {
				status: "Open"
			};

			// Kalau tidak punya bypass role → filter user juga
			if (!roles.includes("99_ByPass Open POS")) {
				filters.user = user;
			}

			return { filters };
		});

	},
});