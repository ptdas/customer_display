


frappe.ui.form.on('Pricing Rule', {
    setup(frm) {
        set_item_query(frm);

        // Company hanya BJB dan BJM
        frm.set_query('company', function () {
            return {
                filters: [
                    ['Company', 'name', 'in', ['BJB', 'BJM']]
                ]
            };
        });

        // Warehouse mengikuti company
        frm.set_query('warehouse', function () {
            if (!frm.doc.company) {
                return {
                    filters: [
                        ['Warehouse', 'company', 'in', ['BJB', 'BJM']]
                    ]
                };
            }

            return {
                filters: {
                    company: frm.doc.company
                }
            };
        });
    },

    custom_item_supplier(frm) {
        set_item_query(frm);
    },

    custom_item_brand(frm) {
        set_item_query(frm);
    },

    scan_item_code(frm) {
        tambah_item_hasil_scan(frm);
    },
    custom_get_item(frm) {
        console.log("===== CUSTOM GET ITEM TRIGGERED =====");
        console.log("Time:", new Date().toISOString());
        console.log("Scan value:", frm.doc.scan_item_code);
        console.log("Current items:", (frm.doc.items || []).map(d => d.item_code));
        get_filtered_items(frm);
    },
    warehouse(frm) {
        if (frm.doc.warehouse) {
            frappe.db.get_value('Warehouse', frm.doc.warehouse, 'company')
                .then(r => {
                    if (r.message && r.message.company) {
                        frm.set_value('company', r.message.company);
                    }
                });
        }
    },
    refresh(frm) {
        set_item_query(frm);

        // Add Multiple di bawah child table Items
        const items_field = frm.fields_dict.items;

        if (items_field && items_field.grid) {
            const grid = items_field.grid;

            if (!grid.__add_multiple_added) {
                grid.add_custom_button(
                    __("Add Multiple"),
                    function () {
                        open_item_selector(frm);
                    }
                );

                grid.__add_multiple_added = true;
            }
        }

        if (!frm.doc.name || frm.is_new()) return;

        frm.add_custom_button(__("Report Item Impact"), function () {
            const url = `/app/query-report/Pricing%20Rule%20Item%20Impact?pricing_rule=${encodeURIComponent(frm.doc.name)}`;

            window.open(url, "_blank");
        });
    }
});

function open_item_selector(frm) {
    let page = 0;
    const page_length = 20;

    const d = new frappe.ui.Dialog({
        title: __('Select Item'),
        fields: [
            {
                fieldname: 'txt',
                fieldtype: 'Data',
                label: __('Beginning with'),
                description: __('You can use wildcard %')
            },
            {
                fieldname: 'results',
                fieldtype: 'HTML'
            },
            {
                fieldname: 'more',
                fieldtype: 'Button',
                label: __('More')
            }
        ],
        primary_action_label: __('Search'),
        primary_action() {
            page = 0;
            search_items();
        }
    });

    d.show();

    d.fields_dict.more.$wrapper.hide();

    d.fields_dict.more.$input.on('click', function () {
        page++;
        search_items(true);
    });

    function search_items(append = false) {
        const txt = d.get_value('txt') || '';

        frappe.call({
            method: 'customer_display.custom_standard.pricing_rule_custom.search_items_for_pricing_rule',
            args: {
                txt: txt,
                start: page * page_length,
                page_length: page_length,
                supplier: frm.doc.custom_item_supplier,
                brand: frm.doc.custom_item_brand
            },
            freeze: true,
            freeze_message: __('Searching Items...'),
            callback(r) {
                const items = r.message || [];

                if (!append) {
                    d.fields_dict.results.$wrapper.html('');
                }

                if (!items.length && !append) {
                    d.fields_dict.results.$wrapper.html(`
                        <div class="text-muted text-center" style="padding: 20px;">
                            ${__('No items found')}
                        </div>
                    `);

                    d.fields_dict.more.$wrapper.hide();
                    return;
                }

                items.forEach(item => {
                    const row = $(`
                        <div class="row link-select-row"
                            data-item-name="${frappe.utils.escape_html(item.item_name || '')}"
                            data-uom="${frappe.utils.escape_html(item.stock_uom || '')}"
                            style="cursor:pointer; padding:8px 5px;">
                            <div class="col-xs-4">
                                <b>
                                    <a href="#" data-value="${frappe.utils.escape_html(item.name)}">
                                        ${frappe.utils.escape_html(item.name)}
                                    </a>
                                </b>
                            </div>

                            <div class="col-xs-8">
                                <span class="text-muted">
                                    ${frappe.utils.escape_html(
                                        [
                                            item.item_name,
                                            item.item_group,
                                            item.brand,
                                            item.name
                                        ].filter(Boolean).join(', ')
                                    )}
                                </span>
                            </div>
                        </div>
                    `);

                    row.on('click', function (e) {
                        e.preventDefault();

                        const item_code = $(this)
                            .find('a')
                            .attr('data-value');

                        const item_name = $(this).attr('data-item-name');
                        const uom = $(this).attr('data-uom');

                        open_qty_dialog(frm, item_code, item_name, uom);
                    });

                    d.fields_dict.results.$wrapper.append(row);
                });

                if (items.length >= page_length) {
                    d.fields_dict.more.$wrapper.show();
                } else {
                    d.fields_dict.more.$wrapper.hide();
                }
            }
        });
    }

    // langsung tampilkan item seperti Select Item Sales Order
    search_items();
}

function open_qty_dialog(frm, item_code, item_name, uom) {
    frappe.confirm(
        __('Add item <b>{0}</b> - {1} to the Items table?', [
            item_code,
            item_name || ''
        ]),
        function () {
            const existing = (frm.doc.items || []).find(
                row => row.item_code === item_code
            );

            if (existing) {
                frappe.show_alert({
                    message: __('{0} is already in the Items table', [item_code]),
                    indicator: 'orange'
                });
                return;
            }

            const row = frm.add_child('items');

            row.item_code = item_code;
            row.custom_item_name = item_name || '';
            row.uom = uom || '';

            frm.refresh_field('items');
            frm.dirty();

            frappe.show_alert({
                message: __('{0} added', [item_code]),
                indicator: 'green'
            });
        }
    );
}


function set_item_query(frm) {
    frm.fields_dict.items.grid.get_field('item_code').get_query = function () {
        let filters = {
            disabled: 0,
            has_variants: 0
        };

        if (frm.doc.custom_item_supplier) {
            filters.custom_vendor = frm.doc.custom_item_supplier;
        }

        if (frm.doc.custom_item_brand) {
            filters.brand = frm.doc.custom_item_brand;
        }

        return { filters };
    };
}

function get_filtered_items(frm) {
    console.log("===== GET ITEMS START =====");
    console.log("Before clear:", (frm.doc.items || []).map(d => d.item_code));

    frappe.call({
        method: 'customer_display.custom_standard.pricing_rule_custom.get_filtered_items',
        args: {
            supplier: frm.doc.custom_item_supplier,
            brand: frm.doc.custom_item_brand
        },
        freeze: true,
        freeze_message: __('Getting items...'),
        callback(r) {
            if (!r.message) return;

            // aku matikan karna kadang fungsi ini ikut ke triger waktu scan barcode
            // frm.clear_table('items');

            r.message.forEach(item => {
                let row = frm.add_child('items');
                row.item_code = item.name;
            });

            frm.refresh_field('items');

            frappe.show_alert({
                message: __('{0} items added', [r.message.length]),
                indicator: 'green'
            });
        }
    });
}

function tambah_item_hasil_scan(frm) {
    const scan_value = (frm.doc.scan_item_code || '').trim();
    if (!scan_value) return;

    frappe.call({
        method: 'customer_display.custom_standard.pricing_rule_custom.get_item_from_scan',
        args: { scan_value },
        callback(r) {
            // Dikosongkan lebih dulu supaya scan berikutnya bisa langsung masuk
            kosongkan_scan_field(frm);

            const item_code = r.message;

            if (!item_code) {
                frappe.show_alert({
                    message: __('Item untuk {0} tidak ketemu', [scan_value]),
                    indicator: 'red'
                });
                return;
            }

            if ((frm.doc.items || []).some(d => d.item_code === item_code)) {
                frappe.show_alert({
                    message: __('{0} sudah ada di tabel', [item_code]),
                    indicator: 'orange'
                });
                return;
            }

            let row = frm.add_child('items');
            row.item_code = item_code;

            frm.refresh_field('items');
            frm.dirty();

            frappe.show_alert({
                message: __('{0} ditambahkan', [item_code]),
                indicator: 'green'
            });
        }
    });
}

function kosongkan_scan_field(frm) {
    frm.set_value('scan_item_code', '');

    // Kursor dikembalikan ke kolom scan supaya scanner tidak perlu diklik lagi
    const field = frm.fields_dict.scan_item_code;
    if (field && field.$input) {
        field.$input.focus();
    }
}
