// Copyright (c) 2026, DAS and contributors
// For license information, please see license.txt

frappe.query_reports["Kas Akhir Per Kasir"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": "From Date",
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": "To Date",
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "parent_company",
            "label": "Cabang",
            "fieldtype": "Select",
            "options": "\nBJB\nBJM"
        }
    ]
};


