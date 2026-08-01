


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

    refresh(frm) {
        set_item_query(frm);
    },
    custom_get_item(frm) {
        get_items(frm);
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
    }
});

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

function get_items(frm) {
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

            frm.clear_table('items');

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
