// Copyright (c) 2025, DAS and contributors
// For license information, please see license.txt


frappe.query_reports["Axtra Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: "Date From",
            fieldtype: "Date",
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: "Date To",
            fieldtype: "Date",
            reqd: 1
        },
        {
            fieldname: "customer_type",
            label: "Customer Type",
            fieldtype: "Select",
            options: "B2C\nB2B",
            default: "B2C"
        }
    ],

    formatter: function (value, row, column, data, default_formatter) {

        if (data && data._spacer) {
            return "";
        }

        if (data && data._col_header) {
            if (!value) {
                return "";
            }
            return `<b>${value}</b>`;
        }

        if (data && (data.cv === "TOTAL" || data.cv === "GRAND TOTAL")) {
            value = default_formatter(value, row, column, data);
            return `<b>${value}</b>`;
        }

        return default_formatter(value, row, column, data);
    }

};
