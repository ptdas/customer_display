frappe.ui.form.on("POS Invoice", {
    refresh(frm) {
        if (frm.doc.is_return) {
            redistribute_return_payments(frm);
        }
    },

    grand_total(frm) {
        if (frm.doc.is_return) {
            redistribute_return_payments(frm);
        }
    },

    items_remove(frm) {
        if (frm.doc.is_return) {
            redistribute_return_payments(frm);
        }
    }
});

frappe.ui.form.on("POS Invoice Item", {
    qty(frm) {
        if (frm.doc.is_return) {
            redistribute_return_payments(frm);
        }
    },

    rate(frm) {
        if (frm.doc.is_return) {
            redistribute_return_payments(frm);
        }
    },

    discount_percentage(frm) {
        if (frm.doc.is_return) {
            redistribute_return_payments(frm);
        }
    },

    discount_amount(frm) {
        if (frm.doc.is_return) {
            redistribute_return_payments(frm);
        }
    }
});

async function redistribute_return_payments(frm) {
    if (!frm.doc.is_return || !frm.doc.return_against) return;

    const r = await frappe.call({
        method: "customer_display.customer_display.custom_standard.pos_invoice_custom.get_return_payment_distribution",
        args: {
            source_invoice: frm.doc.return_against,
            grand_total: Math.abs(frm.doc.grand_total || 0)
        }
    });

    const payments = r.message || [];

    frm.clear_table("payments");

    payments.forEach(p => {
        let row = frm.add_child("payments");
        row.mode_of_payment = p.mode_of_payment;
        row.amount = p.amount;
        row.base_amount = p.amount;
    });

    frm.refresh_field("payments");
}


