(() => {
  var __create = Object.create;
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __getProtoOf = Object.getPrototypeOf;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __commonJS = (cb, mod) => function __require() {
    return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
    isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
    mod
  ));

  // ../customer_display/customer_display/public/js/pos/pos_patch.js
  var require_pos_patch = __commonJS({
    "../customer_display/customer_display/public/js/pos/pos_patch.js"() {
      if (!location.pathname.startsWith("/app/point-of-sale")) {
        return;
      }
      function patchPOSUpdateCart() {
        var _a;
        const Controller = (_a = erpnext == null ? void 0 : erpnext.PointOfSale) == null ? void 0 : _a.Controller;
        if (typeof Controller !== "function") {
          return false;
        }
        if (Controller.prototype._customer_display_patched) {
          return true;
        }
        const original_update_cart_html = Controller.prototype.update_cart_html;
        Controller.prototype.update_cart_html = function() {
          original_update_cart_html.apply(this, arguments);
          const cart_items = this.frm.doc.items.map((item) => ({
            item_code: item.item_code,
            item_name: item.item_name,
            qty: item.qty,
            rate: item.rate
          }));
          frappe.call({
            method: "customer_display.api.update_customer_display",
            args: {
              pos_profile: this.frm.doc.pos_profile,
              items: cart_items
            },
            freeze: false
          });
        };
        Controller.prototype._customer_display_patched = true;
        return true;
      }
      function ensurePOSPatched(retries = 40) {
        if (!patchPOSUpdateCart() && retries > 0) {
          setTimeout(() => ensurePOSPatched(retries - 1), 500);
        }
      }
      frappe.router.on("change", () => {
        if (frappe.get_route()[0] === "pos") {
          ensurePOSPatched();
        }
      });
      ensurePOSPatched();
    }
  });

  // ../customer_display/customer_display/public/js/pos_patch.bundle.js
  var import_pos_patch = __toESM(require_pos_patch());

  // ../customer_display/customer_display/public/js/hide_moved_tab.js
  var HIDE_MOVED_TAB_ALLOWED_ROLE = null;
  async function get_hide_moved_tab_role() {
    if (HIDE_MOVED_TAB_ALLOWED_ROLE !== null) {
      return HIDE_MOVED_TAB_ALLOWED_ROLE;
    }
    let role = await frappe.db.get_single_value(
      "AXTRA Settings",
      "allowed_tab_moved"
    );
    HIDE_MOVED_TAB_ALLOWED_ROLE = role;
    return role;
  }
  function hide_moved_tab_dom(frm) {
    var _a;
    let tab_fieldname = "custom_moved";
    if (!frm)
      return;
    if ((_a = frm.fields_dict) == null ? void 0 : _a[tab_fieldname]) {
      frm.set_df_property(tab_fieldname, "hidden", 1);
    }
    let nav = frm.$wrapper.find(`.nav-link[data-fieldname="${tab_fieldname}"]`);
    nav.closest("li").hide();
    let content = frm.$wrapper.find(`#${frm.doctype.toLowerCase()}-${tab_fieldname}`);
    content.hide();
  }
  async function run_hide_logic(frm) {
    if (!frm)
      return;
    let allowed_role = await get_hide_moved_tab_role();
    if (!allowed_role)
      return;
    let can_see = (frappe.user_roles || []).includes(allowed_role);
    if (!can_see) {
      setTimeout(() => hide_moved_tab_dom(frm), 300);
      setTimeout(() => hide_moved_tab_dom(frm), 1e3);
      setTimeout(() => hide_moved_tab_dom(frm), 2e3);
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
})();
//# sourceMappingURL=pos_patch.bundle.AJUHEFVB.js.map
