// Copyright (c) 2025, DAS and contributors
// For license information, please see license.txt

frappe.query_reports["POS Ongoing"] = {
	"filters": [
		{
			"fieldname": "date",
			"label": __("Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		}
	]
};
