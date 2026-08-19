// Copyright (c) 2026, DAS and contributors
// For license information, please see license.txt

frappe.query_reports["Pricing Rule Item Impact"] = {
    filters: [
        {
            fieldname: "pricing_rule",
            label: __("Pricing Rule"),
            fieldtype: "Link",
            options: "Pricing Rule",
            reqd: 1,
            on_change: function () {
                frappe.query_report.refresh();
            }
        },
        {
            fieldname: "include_disabled_items",
            label: __("Include Disabled Items"),
            fieldtype: "Check",
            default: 0
        }
    ],

    onload: function (report) {

        // Fokus otomatis ke field Pricing Rule
        report.page.fields_dict.pricing_rule.$input.focus();

        // Tombol Print PDF
        report.page.add_inner_button(__("Print PDF"), function () {

            const filters = report.get_values();

            if (!filters.pricing_rule) {
                frappe.msgprint(__("Please select Pricing Rule first"));
                return;
            }

            const url = frappe.urllib.get_full_url(
                "/api/method/customer_display.customer_display.report.pricing_rule_item_impact.pricing_rule_item_impact.print_pdf?pricing_rule="
                + encodeURIComponent(filters.pricing_rule)
            );

            // langsung buka tab baru
            window.open(url, "_blank");
        });

        // CSS khusus print
        const style = document.createElement("style");

        style.innerHTML = `
            @media print {
                .page-head,
                .page-title,
                .layout-main-section,
                .report-wrapper,
                .query-report,
                .report-summary,
                .report-message {
                    display: block !important;
                    visibility: visible !important;
                }

                .report-summary,
                .report-message {
                    margin-bottom: 12px !important;
                }

                .dt-scrollable,
                .datatable {
                    overflow: visible !important;
                }

                table {
                    width: 100% !important;
                    border-collapse: collapse !important;
                }

                .datatable table th,
                .datatable table td {
                    border: 1px solid #ddd !important;
                    padding: 6px !important;
                }
            }
        `;

        document.head.appendChild(style);
    }
};