frappe.query_reports["Bantuan Pencarian Barang"] = {
    filters: [
        {
            fieldname: "keyword",
            label: "Barcode / Item",
            fieldtype: "Data",
            placeholder: "Scan barcode / ketik item code / item name",

            on_change: function () {
                const keyword = frappe.query_report.get_filter_value("keyword");

                frappe.query_report.set_filter_value("page", 1);

                if (keyword) {
                    frappe.query_report.refresh();
                }
            },

            onkeydown: function (e) {
                if (e.key === "Enter") {
                    const keyword = frappe.query_report.get_filter_value("keyword");

                    frappe.query_report.set_filter_value("page", 1);

                    if (keyword) {
                        frappe.query_report.refresh();
                    }
                }
            }
        },

        {
            fieldname: "company",
            label: "Company",
            fieldtype: "Link",
            options: "Company",

            onchange: function () {
                frappe.query_report.set_filter_value("page", 1);
                frappe.query_report.refresh();
            },

            get_query: function () {
                return {
                    filters: {
                        name: ["in", ["BJM", "BJB"]]
                    }
                };
            }
        },

        {
            fieldname: "page",
            fieldtype: "Int",
            default: 1,
            hidden: 1
        }
    ],

    onload: function (report) {

    report.refresh = function () {
        const keyword = report.get_filter_value("keyword");

        if (!keyword) {
            report.data = [];
            report.render();
            update_pagination_buttons(report);
            return;
        }

        frappe.query_report.__proto__.refresh.call(report);
    };

    report.page.add_inner_button("‹ Previous", function () {
        const page = cint(
            report.get_filter_value("page")
        ) || 1;

        if (page <= 1) {
            return;
        }

        report.set_filter_value("page", page - 1);
        report.refresh();
    });

    report.page.add_inner_button("Next ›", function () {
        const data = report.data || [];
        const page = cint(
            report.get_filter_value("page")
        ) || 1;

        if (data.length < 100) {
            frappe.show_alert({
                message: "Sudah di halaman terakhir",
                indicator: "orange"
            });

            return;
        }

        report.set_filter_value("page", page + 1);
        report.refresh();
    });

    update_pagination_buttons(report);
},

    after_datatable_render: function (report) {
        update_pagination_label(report);
    },

    formatter: function (
        value,
        row,
        column,
        data,
        default_formatter
    ) {
        value = default_formatter(
            value,
            row,
            column,
            data
        );

        if (
            ["item_code", "item_name"].includes(
                column.fieldname
            ) &&
            data?.item_code
        ) {
            value = `
                <div style="text-align:left">
                    <a href="/app/item/${data.item_code}" target="_blank">
                        ${data[column.fieldname]}
                    </a>
                </div>
            `;
        }

        if (
            [
                "qty_toko",
                "qty_gudang",
                "qty_waralaba"
            ].includes(column.fieldname) &&
            (data[column.fieldname] || 0) <= 0
        ) {
            value = `<span style="color:red">${value}</span>`;
        }

        return value;
    }
};


function update_pagination_label(report) {
    const page = cint(
        report.get_filter_value("page")
    ) || 1;

    const data = report.data || [];

    const page_length = 100;
    const start = ((page - 1) * page_length) + 1;
    const end = ((page - 1) * page_length) + data.length;

    setTimeout(() => {

        const $container = report.page.wrapper.find(
            ".bantuan-pagination-info"
        );

        if ($container.length) {
            $container.remove();
        }

        if (!data.length) {
            return;
        }

        const $info = $(`
            <div
                class="bantuan-pagination-info"
                style="
                    text-align:center;
                    font-weight:500;
                    margin:8px 0 12px;
                    font-size:13px;
                "
            >
                Page ${page}
                &nbsp;&nbsp;•&nbsp;&nbsp;
                Menampilkan ${start} - ${end}
            </div>
        `);

        report.page.wrapper
            .find(".datatable")
            .first()
            .before($info);

    }, 100);
}