frappe.ui.form.on("POS Invoice", {
    onload_post_render(frm) {
        enforce_grosir_once(frm);
    }
});

function enforce_grosir_once(frm) {
    // console.log("testus");
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
