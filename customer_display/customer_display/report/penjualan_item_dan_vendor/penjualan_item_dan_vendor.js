// Copyright (c) 2026, DAS and contributors
// For license information, please see license.txt

frappe.query_reports["Penjualan Item dan Vendor"] = {
    "filters": [
        {
            "fieldname": "parent_company",
            "label": "Parent Company",
            "fieldtype": "Select",
            "options": "\nBJB\nBJM",
            "default": "BJB",
            "reqd": 1,
            "on_change": function () {
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "from_date",
            "label": "From Date",
            "fieldtype": "Date",
            "default": frappe.datetime.month_start(),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": "To Date",
            "fieldtype": "Date",
            "default": frappe.datetime.month_end(),
            "reqd": 1
        }
    ]
};
