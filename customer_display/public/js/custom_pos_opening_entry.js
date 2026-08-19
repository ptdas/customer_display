
frappe.ui.form.on("POS Opening Entry", {
    setup(frm) {
        frm.set_query("company", function () {
            return {
                filters: {
                    name: ["in", ["BJB", "BJM"]]
                }
            };
        });
    },

    async pos_profile(frm) {
        if (!frm.doc.pos_profile) return;

        const r = await frappe.db.get_value(
            "POS Profile",
            frm.doc.pos_profile,
            "company"
        );

        if (r.message && r.message.company) {
            frm.set_value("company", r.message.company);
        }
    }
});


