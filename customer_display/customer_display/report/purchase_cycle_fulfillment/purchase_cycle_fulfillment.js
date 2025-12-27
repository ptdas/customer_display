// Copyright (c) 2025, DAS and contributors
// For license information, please see license.txt

frappe.query_reports["Purchase Cycle Fulfillment"] = {
	onload: function (report) {
		const today = frappe.datetime.get_today();
		const from_date = frappe.datetime.add_days(today, -90);

		report.set_filter_value("to_date", today);
		report.set_filter_value("from_date", from_date);
	},
	"filters": [
	    {
	        "fieldname": "from_date",
	        "label": "From Date",
	        "fieldtype": "Date"
	    },
	    {
	        "fieldname": "to_date",
	        "label": "To Date",
	        "fieldtype": "Date"
	    },
	    {
	        "fieldname": "supplier",
	        "label": "Supplier",
	        "fieldtype": "Link",
	        "options": "Supplier"
	    }
	]
};
