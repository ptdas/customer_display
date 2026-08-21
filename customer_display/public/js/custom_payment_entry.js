frappe.ui.form.on('Payment Entry', {
    refresh:function(frm){
        hide_perm(frm);
    },
    async party(frm) {
        await auto_set_company_from_supplier_by_user(frm);
    },

    async party_type(frm) {
        await auto_set_company_from_supplier_by_user(frm);
    }
});

async function auto_set_company_from_supplier_by_user(frm) {

    if (frm.doc.party_type !== "Supplier") {
        // console.log("Skip: party_type bukan Supplier →", frm.doc.party_type);
        return;
    }

    if (!frm.doc.party) {
        // console.log("Skip: Supplier kosong");
        return;
    }

    try {

        let user = frappe.session.user;
        // console.log("Current User:", user);

        let emp_res = await frappe.db.get_list("Employee", {
            filters: {
                user_id: user,
                status: "Active"
            },
            fields: ["name", "branch"],
            limit: 1
        });

        // console.log("Employee Query Result:", emp_res);

        if (!emp_res.length) {
            // console.log("Employee tidak ditemukan");
            return;
        }

        let emp_branch = emp_res[0].branch;
        // console.log("Employee Branch:", emp_branch);

        if (!emp_branch) {
            // console.log("Branch kosong");
            return;
        }

        let company_group = null;

        // if (emp_branch.toUpperCase().includes("BANJARMASIN")) {
        //     company_group = "BJB";
        // }
        // else if (emp_branch.toUpperCase().includes("BANJARBARU")) {
        //     company_group = "BJM";
        // }

        if (emp_branch.toUpperCase().includes("BANJARMASIN")) {
            company_group = "BJM";
        }
        else if (emp_branch.toUpperCase().includes("BANJARBARU")) {
            company_group = "BJB";
        }

        // console.log("Mapped Company Group:", company_group);

        if (!company_group) {
            // console.log("Branch tidak termasuk mapping");
            return;
        }

        let supplier = await frappe.db.get_doc("Supplier", frm.doc.party);
        // console.log("Supplier Doc:", supplier);

        let company_to_set = null;

        // Site hasil pecah cuma punya satu grup dan menyimpannya di
        // custom_vendor_company; field _bjm sudah tidak ada di sana, jadi
        // doc-nya pun tidak membawa propertinya. Site gabungan tetap memilih
        // per sisi seperti biasa.
        if (!("custom_vendor_company_bjm" in supplier)) {
            company_to_set = supplier.custom_vendor_company;
        }
        else if (company_group === "BJB") {
            company_to_set = supplier.custom_vendor_company;
        }
        else if (company_group === "BJM") {
            company_to_set = supplier.custom_vendor_company_bjm;
        }

        console.log("Company To Set:", company_to_set);

        if (company_to_set) {
            await frm.set_value("company", company_to_set);
            // console.log("Company berhasil di set:", company_to_set);
        } else {
            // console.log("Supplier tidak punya mapping company");
        }

    } catch (e) {
        console.error("Auto company error:", e);
    }

}

function hide_perm(frm) {

    let max_perm_level = frappe.boot.max_perm_level
    
    if(max_perm_level < 7 && frappe.session.user != "Administrator"){
        frm.set_df_property('naming_series', 'read_only', true);
        frm.set_df_property('party_type', 'read_only', true);
        frm.set_df_property('party', 'read_only', true);
        frm.set_df_property('party_name', 'read_only', true);
        frm.set_df_property('bank_account', 'read_only', true);
        frm.set_df_property('party_bank_account', 'read_only', true);
        frm.set_df_property('contact_person', 'read_only', true);

        frm.set_df_property('party_balance', 'read_only', true);
        frm.set_df_property('paid_from', 'read_only', true);
        frm.set_df_property('paid_from_account_currency', 'read_only', true);
        frm.set_df_property('paid_from_account_balance', 'read_only', true);
        frm.set_df_property('paid_to', 'read_only', true);
        frm.set_df_property('paid_to_account_currency', 'read_only', true);
        frm.set_df_property('paid_to_account_balance', 'read_only', true);

        frm.set_df_property('total_allocated_amount', 'read_only', true);
        frm.set_df_property('unallocated_amount', 'read_only', true);
        frm.set_df_property('difference_amount', 'read_only', true);
    }
}

