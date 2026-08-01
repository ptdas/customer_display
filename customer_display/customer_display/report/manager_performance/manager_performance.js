// Copyright (c) 2026, DAS and contributors
// For license information, please see license.txt

frappe.query_reports["Manager Performance"] = {
    filters: [
        {
            fieldname: "manager",
            label: __("Manager"),
            fieldtype: "Link",
            options: "Employee"
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
            description: __("Kosongkan untuk melihat semua termasuk tanpa department")
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_start(),
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_end(),
            reqd: 1
        }
    ]
};
