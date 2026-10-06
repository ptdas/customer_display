import json

import frappe
from frappe.utils import cint

from erpnext.stock.get_item_details import (
    get_item_details as erpnext_get_item_details,
    get_price_list_currency_and_exchange_rate,
    get_price_list_rate,
    process_args,
    get_pricing_rule_for_item,
)


def _is_pos(args):
    if isinstance(args, str):
        args = json.loads(args)

    return (
        cint(args.get("is_pos")) == 1
        or args.get("doctype") == "POS Invoice"
    )


def _is_pricing_rule_conflict(exception):
    return exception.__class__.__name__ == "MultiplePricingRuleConflict"


@frappe.whitelist()
def get_item_details(args, doc=None, for_validate=False, overwrite_warehouse=True):
    """
    Override ERPNext get_item_details.

    POS:
        - Item dengan custom_manual_discount = 1
          tidak boleh menerapkan Pricing Rule.
        - Pricing Rule normal tetap digunakan.
        - MultiplePricingRuleConflict fallback ke Price List.

    Non-POS:
        - Behavior ERPNext tetap normal.
    """

    if isinstance(args, str):
        args = json.loads(args)

    # =========================================================
    # POS + MANUAL DISCOUNT
    # =========================================================
    #
    # ERPNext akan dipanggil oleh set_missing_item_details()
    # saat POS Invoice di-save/validate.
    #
    # Pada saat itu args sudah berisi:
    # custom_manual_discount = 1
    #
    # Paksa ignore_pricing_rule hanya untuk item tersebut.
    #
    if (
        _is_pos(args)
        and cint(args.get("custom_manual_discount")) == 1
    ):
        retry_args = dict(args)
        retry_args["ignore_pricing_rule"] = 1

        result = erpnext_get_item_details(
            args=retry_args,
            doc=doc,
            for_validate=for_validate,
            overwrite_warehouse=overwrite_warehouse,
        )

        # Pastikan hasil tidak membawa Pricing Rule lama.
        result["pricing_rules"] = ""
        result["has_pricing_rule"] = 0

        return result

    # =========================================================
    # NORMAL ERPNext
    # =========================================================

    try:
        return erpnext_get_item_details(
            args=args,
            doc=doc,
            for_validate=for_validate,
            overwrite_warehouse=overwrite_warehouse,
        )

    except Exception as e:
        if not _is_pricing_rule_conflict(e):
            raise

        if not _is_pos(args):
            raise

        retry_args = dict(args)
        retry_args["ignore_pricing_rule"] = 1

        result = erpnext_get_item_details(
            args=retry_args,
            doc=doc,
            for_validate=for_validate,
            overwrite_warehouse=overwrite_warehouse,
        )

        result["pricing_rule_conflict"] = 1
        result["pricing_rule_conflict_message"] = str(e)

        return result


@frappe.whitelist()
def apply_price_list(args, as_doc=False, doc=None):
    """
    Override ERPNext apply_price_list.

    Untuk POS:
        Jika item sudah memiliki pricing_rules kosong,
        jangan jalankan get_pricing_rule_for_item() lagi.

        Ini mencegah Pricing Rule conflict dilempar ulang
        oleh apply_price_list setelah get_item_details()
        sebelumnya sudah fallback ke Price List.

    Pricing Rule normal tetap dijalankan apabila
    item memiliki pricing_rules.

    Non-POS tetap menggunakan behavior ERPNext.
    """

    args = process_args(args)

    parent = get_price_list_currency_and_exchange_rate(args)
    args.update(parent)

    children = []

    if "items" in args:
        item_list = args.get("items")

        for item in item_list:
            args_copy = frappe._dict(args.copy())
            args_copy.update(item)

            item_details = _apply_price_list_on_item(
                args_copy,
                doc=doc,
            )

            children.append(item_details)

    if as_doc:
        args.price_list_currency = (parent.price_list_currency,)
        args.plc_conversion_rate = parent.plc_conversion_rate

        if args.get("items"):
            for i, item in enumerate(args.get("items")):
                for fieldname in children[i]:
                    if fieldname in item and fieldname not in ("name", "doctype"):
                        item[fieldname] = children[i][fieldname]

        return args

    return {
        "parent": parent,
        "children": children,
    }


def _apply_price_list_on_item(args, doc=None):
    item_doc = frappe.db.get_value(
        "Item",
        args.item_code,
        ["name", "variant_of"],
        as_dict=1,
    )

    # =========================================================
    # MANUAL DISCOUNT
    # =========================================================
    if _is_pos(args) and cint(args.get("custom_manual_discount")) == 1:
        # Pastikan pricing rule lama dari payload dibuang
        args["pricing_rules"] = ""

        item_details = get_price_list_rate(
            args,
            item_doc,
        )

        # Jangan pernah kembalikan pricing rule
        item_details["pricing_rules"] = ""

        return item_details

    # =========================================================
    # NORMAL
    # =========================================================

    item_details = get_price_list_rate(
        args,
        item_doc,
    )

    try:
        pricing_rule_details = get_pricing_rule_for_item(
            args,
            doc=doc,
        )

        item_details.update(pricing_rule_details)

    except Exception as e:
        if not _is_pricing_rule_conflict(e):
            raise

        if not _is_pos(args):
            raise

        item_details["pricing_rules"] = ""
        item_details["discount_percentage"] = 0
        item_details["discount_amount"] = 0

    return item_details