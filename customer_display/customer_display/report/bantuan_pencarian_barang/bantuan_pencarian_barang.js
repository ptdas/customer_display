frappe.query_reports["Bantuan Pencarian Barang"] = {
    filters: [
        {
            fieldname: "keyword",
            label: "Barcode / Item",
            fieldtype: "Data",
            placeholder: "Scan barcode / ketik item code / item name",
            on_change: function () {
                const keyword = frappe.query_report.get_filter_value("keyword");
                if (keyword) {
                    frappe.query_report.refresh();
                }
            },
            
            onkeydown: function (e) {
                if (e.key === "Enter") {
                    const keyword = frappe.query_report.get_filter_value("keyword");
                    if (keyword) {
                        frappe.query_report.refresh();
                    }
                }
            },
        },
        {
            fieldname: "company",
            label: "Company",
            fieldtype: "Link",
            options: "Company",
            onchange: function () {
                frappe.query_report.refresh();
            },
            get_query: function () {
                return {
                    filters: {
                        name: ["in", ["BJM", "BJB"]]
                    }
                };
            }
        }
    ],

    onload: function (report) {
        report.refresh = function () {
            const keyword = report.get_filter_value("keyword");
            if (!keyword) {
                report.data = [];
                report.render();
                return;
            }
            frappe.query_report.__proto__.refresh.call(report);
        };
    },

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (["item_code", "item_name"].includes(column.fieldname) && data?.item_code) {
            value = `
                <div style="text-align:left">
                    <a href="/app/item/${data.item_code}" target="_blank">
                        ${data[column.fieldname]}
                    </a>
                </div>
            `;
        }

        if (
            ["qty_toko", "qty_gudang"].includes(column.fieldname) &&
            (data[column.fieldname] || 0) <= 0
        ) {
            value = `<span style="color:red">${value}</span>`;
        }

        return value;
    }

};
