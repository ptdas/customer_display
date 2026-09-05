// // Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// // License: GNU General Public License v3. See license.txt

// // render
// frappe.listview_settings["POS Invoice"] = {
// 	add_fields: [
// 		"customer",
// 		"customer_name",
// 		"base_grand_total",
// 		"outstanding_amount",
// 		"due_date",
// 		"company",
// 		"currency",
// 		"is_return",
// 	],
// 	get_indicator: function (doc) {
// 		var status_color = {
// 			Draft: "red",
// 			Unpaid: "orange",
// 			Paid: "green",
// 			Submitted: "blue",
// 			Consolidated: "green",
// 			Return: "darkgrey",
// 			"Unpaid and Discounted": "orange",
// 			"Overdue and Discounted": "red",
// 			Overdue: "red",
// 		};
// 		return [__(doc.status), status_color[doc.status], "status,=," + doc.status];
// 	},
// 	right_column: "grand_total",
// 	onload: function (me) {
// 		me.page.add_action_item("Make Merge Log", function () {
// 			const invoices = me.get_checked_items();
// 			frappe.call({
// 				method: "erpnext.accounts.doctype.pos_invoice.pos_invoice.make_merge_log",
// 				freeze: true,
// 				args: {
// 					invoices: invoices,
// 				},
// 				callback: function (r) {
// 					if (r.message) {
// 						var doc = frappe.model.sync(r.message)[0];
// 						frappe.set_route("Form", doc.doctype, doc.name);
// 					}
// 				},
// 			});
// 		});
// 	},
// };




frappe.listview_settings["POS Invoice"] = {
	add_fields: [
		"customer",
		"customer_name",
		"base_grand_total",
		"outstanding_amount",
		"due_date",
		"company",
		"currency",
		"is_return",
	],

	get_indicator: function (doc) {
		var status_color = {
			Draft: "red",
			Unpaid: "orange",
			Paid: "green",
			Submitted: "blue",
			Consolidated: "green",
			Return: "darkgrey",
			"Unpaid and Discounted": "orange",
			"Overdue and Discounted": "red",
			Overdue: "red",
		};

		return [
			__(doc.status),
			status_color[doc.status],
			"status,=," + doc.status
		];
	},

	right_column: "grand_total",

	onload: function (me) {
		// Existing action
		me.page.add_action_item("Make Merge Log", function () {
			const invoices = me.get_checked_items();

			frappe.call({
				method: "erpnext.accounts.doctype.pos_invoice.pos_invoice.make_merge_log",
				freeze: true,
				args: {
					invoices: invoices,
				},
				callback: function (r) {
					if (r.message) {
						var doc = frappe.model.sync(r.message)[0];
						frappe.set_route("Form", doc.doctype, doc.name);
					}
				},
			});
		});

		// Custom default filter
		const filters = me.get_filters_for_args();

		console.log("POS Invoice filters:", filters);

		if (!filters.length) {
			const today = frappe.datetime.get_today();

			console.log("Setting default POS Invoice filter:", {
				status: "Paid",
				posting_date: today,
			});

			frappe.route_options = {
				status: "Paid",
				posting_date: today,
			};

			frappe.set_route("List", "POS Invoice");
		}
	},
};