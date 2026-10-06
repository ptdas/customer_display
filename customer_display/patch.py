
import frappe
from frappe.utils import flt


import os
import re
import barcode

from barcode.writer import ImageWriter

def update_all_item_last_vendor():

    frappe.db.auto_commit_on_many_writes = True
    print("== Update Item.custom_vendor berdasarkan dokumen terakhir ==")

    pi_rows = frappe.db.sql("""
        SELECT
            pii.item_code,
            pi.supplier,
            pi.modified,
            'PI' AS source
        FROM `tabPurchase Invoice Item` pii
        JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE pi.docstatus = 1
          AND pi.is_return = 0
          AND pii.item_code IS NOT NULL
    """, as_dict=True)

    pr_rows = frappe.db.sql("""
        SELECT
            pri.item_code,
            pr.supplier,
            pr.modified,
            'PR' AS source
        FROM `tabPurchase Receipt Item` pri
        JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
        WHERE pr.docstatus = 1
          AND pri.item_code IS NOT NULL
    """, as_dict=True)

    all_rows = pi_rows + pr_rows

    last_per_item = {}

    for row in all_rows:
        item_code = row["item_code"]
        modified = row["modified"]

        if item_code not in last_per_item:
            last_per_item[item_code] = row
        else:
            if modified > last_per_item[item_code]["modified"]:
                last_per_item[item_code] = row

    total_updated = 0
    for item_code, row in last_per_item.items():
        frappe.db.set_value(
            "Item",
            item_code,
            "custom_vendor",
            row["supplier"],
            update_modified=False
        )
        total_updated += 1

    print(f"== Total updated: {total_updated} item(s) ==")


def patch_purchase_invoice_custom_lcv_db():

    invoices = frappe.get_all("Purchase Invoice", filters={"docstatus": ["<", 2]}, fields=["name"])
    total = len(invoices)
    frappe.msgprint(f"Patching {total} Purchase Invoice...")

    for idx, inv in enumerate(invoices, start=1):
        items = frappe.get_all("Purchase Invoice Item", filters={"parent": inv.name}, fields=["name", "item_code", "rate", "net_rate"])
        lcv_rows = frappe.get_all("PINV LCV Item", filters={"parent": inv.name}, fields=["item_code", "applicable_charges", "amount"])
        taxes_and_charges_added = frappe.db.get_value("Purchase Invoice", inv.name, "taxes_and_charges_added") or 0

        for item in items:
            row_lcv = next((r for r in lcv_rows if r.item_code == item.item_code), None)
            if row_lcv:
                if item.rate == item.net_rate and taxes_and_charges_added > 0:
                    value = (row_lcv.applicable_charges + row_lcv.amount) + (item.rate * 11 / 100)
                else:
                    value = (row_lcv.applicable_charges + row_lcv.amount) + (item.rate - item.net_rate)

                frappe.db.set_value("Purchase Invoice Item", item.name, "custom_lcv_per_quantity", flt(value, 0))

        print(f"[{idx}/{total}] Patched {inv.name}")

    frappe.db.commit()
    print("Patch selesai!")
    
def set_all_users_timezone_wita():
    users = frappe.get_all(
        "User",
        pluck="name"
    )

    for user in users:
        frappe.db.set_value(
            "User",
            user,
            "time_zone",
            "Asia/Makassar",
            update_modified=False
        )

    frappe.db.commit()


def patch_barcode_item():
    site_path = frappe.get_site_path()
    public_path = os.path.join(site_path, "public", "files", "barcodes")

    os.makedirs(public_path, exist_ok=True)

    rows = frappe.get_all(
        "Item Barcode",
        filters={
            "custom_item_barcode_image_file": ["in", ["", None]],
            "barcode": ["!=", ""]
        },
        fields=["name", "parent", "barcode"]
    )

    print(f"Barcode yang perlu diproses : {len(rows)}")

    processed_items = set()

    for row in rows:
        print(f"Generate {row.barcode}")

        safe_barcode = re.sub(r"[^\w\-_]", "_", row.barcode)
        filename = f"barcode_{safe_barcode}"
        filepath = os.path.join(public_path, filename)

        code128 = barcode.get(
            "code128",
            row.barcode,
            writer=ImageWriter()
        )

        code128.save(filepath)

        frappe.db.set_value(
            "Item Barcode",
            row.name,
            "custom_item_barcode_image_file",
            f"/files/barcodes/{filename}.png",
            update_modified=False
        )

        processed_items.add(row.parent)

    frappe.db.commit()

    print("========================")
    print(f"Barcode diproses : {len(rows)}")
    print(f"Item terdampak   : {len(processed_items)}")
    print("========================")



def update_item_price_from_item():
    frappe.db.sql("""
        UPDATE `tabItem Price` ip
        INNER JOIN `tabItem` i
            ON i.name = ip.item_code
        SET
            ip.item_name = i.item_name,
            ip.item_description = i.description
    """)

    frappe.db.commit()

    print("Item Price item_name dan item_description berhasil di-update")