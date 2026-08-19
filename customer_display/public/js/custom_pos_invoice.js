frappe.ui.form.on("POS Invoice", {
    onload_post_render(frm) {
        enforce_grosir_once(frm);
    },

    refresh(frm) {
        // if (frm.doc.is_return) {
        //     redistribute_return_payments(frm);
        // }
    },

    grand_total(frm) {
        if (frm.doc.is_return && frm.is_new()) {
            trigger_redistribute(frm);
        }
    },
    async validate(frm) {

        // Redistribute hanya saat save pertama retur
        if (frm.doc.is_return && frm.is_new()) {
            clearTimeout(return_payment_timer);
            await redistribute_return_payments(frm);
        }

        // Selalu cegah amount/base_amount menjadi null
        (frm.doc.payments || []).forEach(row => {
            row.amount = flt(row.amount || 0);
            row.base_amount = flt(row.base_amount || row.amount || 0);
        });

        frm.refresh_field("payments");
    }
});


function enforce_grosir_once(frm) {
    if (frm.doc.docstatus !== 0) return;

    if (frm.doc.custom_is_grosir_mode !== 1) return;

    if (frm.__grosir_enforced) return;
    frm.__grosir_enforced = true;

    setTimeout(() => {
        if (frm.doc.selling_price_list !== "Grosir") {
            frm.set_value("selling_price_list", "Grosir");
            console.log("Pricelist Grosir dikunci saat load");
        }
    }, 500);
}

// debounce timer
let return_payment_timer = null;

function trigger_redistribute(frm) {
    // hanya untuk return yang belum pernah disimpan
    if (!frm.doc.is_return || !frm.is_new()) return;

    clearTimeout(return_payment_timer);

    return_payment_timer = setTimeout(() => {
        redistribute_return_payments(frm);
    }, 250);
}



frappe.ui.form.on("POS Invoice Item", {
    items_add(frm) {
        trigger_redistribute(frm);
    },

    items_remove(frm) {
        trigger_redistribute(frm);
    },

    qty(frm) {
        trigger_redistribute(frm);
    },

    rate(frm) {
        trigger_redistribute(frm);
    },

    discount_percentage(frm) {
        trigger_redistribute(frm);
    },

    discount_amount(frm) {
        trigger_redistribute(frm);
    }
});


async function redistribute_return_payments(frm) {
    if (!frm.doc.is_return || !frm.doc.return_against || !frm.is_new()) {
        return;
    }

    const r = await frappe.call({
        method: "customer_display.custom_standard.pos_invoice_custom.get_return_payment_distribution",
        args: {
            source_invoice: frm.doc.return_against,
            grand_total: Math.abs(frm.doc.grand_total || 0)
        }
    });

    const payments = r.message || [];

    frm.clear_table("payments");

    payments.forEach(p => {
        let row = frm.add_child("payments");

        let amount = flt(p.amount || 0);

        row.mode_of_payment = p.mode_of_payment;
        row.amount = amount;
        row.base_amount = amount;
    });

    frm.refresh_field("payments");
}

