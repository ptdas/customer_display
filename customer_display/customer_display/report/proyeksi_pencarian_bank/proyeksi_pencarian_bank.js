// Copyright (c) 2026, DAS and contributors
// For license information, please see license.txt

frappe.query_reports["Proyeksi Pencarian Bank"] = {
    filters: [
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            reqd: 1
        }
    ],

    formatter: function (value, row, column, data, default_formatter) {

        if (data && data._spacer) {
            return "";
        }

        if (data && data._col_header) {
            if (!value) return "";
            return `<b>${value}</b>`;
        }

        if (data && (data.cv === "TOTAL" || data.cv === "GRAND TOTAL")) {
            value = default_formatter(value, row, column, data);
            return `<b>${value}</b>`;
        }

        if (["gross_bank", "mdr", "net_bank"].includes(column.fieldname)) {
            value = default_formatter(value, row, column, data);
            return `<div style="text-align: right;">${value}</div>`;
        }

        return default_formatter(value, row, column, data);
    }
};
