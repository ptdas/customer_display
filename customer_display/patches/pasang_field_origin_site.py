# Copyright (c) 2026, DAS and contributors
# For license information, please see license.txt

"""Pasang `Purchase Invoice.custom_origin_site`.

Sesudah split, PI di site penerima menandai kiriman dengan pasangan (site
asal, nama dokumen asal). Tanpa site asal, nomor dokumen dari BJB dan BJM
bisa bertabrakan dan kunci idempotensinya tidak lagi unik.

`custom_stock_movement_inter` sendiri sudah ada di produksi sebagai Custom
Field bertipe Data - itu dibuat lewat UI dulu, tidak pernah masuk app. Patch
ini memastikan minimal yang baru terpasang lewat kode, bukan lewat tangan.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields(
        {
            "Purchase Invoice": [
                {
                    "fieldname": "custom_origin_site",
                    "label": "Site Asal Kiriman",
                    "fieldtype": "Data",
                    "insert_after": "custom_stock_movement_inter",
                    "read_only": 1,
                    "no_copy": 1,
                    "search_index": 1,
                    "description": "Diisi otomatis oleh Stock Movement Inter dari site seberang",
                }
            ]
        },
        ignore_validate=True,
    )

    frappe.db.commit()
