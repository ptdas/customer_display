// console.log("========== HIDE MOVED TAB LOADED ==========");

let HIDE_MOVED_TAB_ALLOWED_ROLE = null;

async function get_hide_moved_tab_role() {

    if (HIDE_MOVED_TAB_ALLOWED_ROLE !== null) {
        // console.log("[HideMovedTab] Using cached role:", HIDE_MOVED_TAB_ALLOWED_ROLE);
        return HIDE_MOVED_TAB_ALLOWED_ROLE;
    }

    let role = await frappe.db.get_single_value(
        "AXTRA Settings",
        "allowed_tab_moved"
    );

    // console.log("[HideMovedTab] Role from DB:", role);

    HIDE_MOVED_TAB_ALLOWED_ROLE = role;
    return role;
}

function hide_moved_tab_dom(frm) {

    let tab_fieldname = "custom_moved";

    // console.log("[HideMovedTab] Trying hide tab DOM");

    if (!frm) return;

    if (frm.fields_dict?.[tab_fieldname]) {
        frm.set_df_property(tab_fieldname, "hidden", 1);
    }

    let nav = frm.$wrapper.find(`.nav-link[data-fieldname="${tab_fieldname}"]`);
    nav.closest("li").hide();

    let content = frm.$wrapper.find(`#${frm.doctype.toLowerCase()}-${tab_fieldname}`);
    content.hide();
}

async function run_hide_logic(frm) {

    if (!frm) return;

    // console.log("========== HideMovedTab Router Trigger ==========");
    // console.log("[HideMovedTab] Doctype:", frm.doctype);

    let allowed_role = await get_hide_moved_tab_role();

    if (!allowed_role) return;

    let can_see = (frappe.user_roles || []).includes(allowed_role);

    // console.log("[HideMovedTab] Can see:", can_see);

    if (!can_see) {

        setTimeout(() => hide_moved_tab_dom(frm), 300);
        setTimeout(() => hide_moved_tab_dom(frm), 1000);
        setTimeout(() => hide_moved_tab_dom(frm), 2000);

    }
}

frappe.router.on("change", () => {

    setTimeout(() => {

        let frm = cur_frm;

        if (frm) {
            run_hide_logic(frm);
        }

    }, 300);

});
