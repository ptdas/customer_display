// Copyright (c) 2025, DAS and contributors
// For license information, please see license.txt

frappe.query_reports["Financial Report - Income Statement"] = {
	"filters": [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
			width: "60px",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
			width: "60px",
		},
		{
			fieldname: "periodicity",
			label: __("Periodicity"),
			fieldtype: "Select",
			options: [
				{ value: "MONTHLY", label: __("Monthly") },
				{ value: "YEARLY", label: __("Yearly") }
			],
			default: "Yearly",
			reqd: 1,
		},
	]
};
