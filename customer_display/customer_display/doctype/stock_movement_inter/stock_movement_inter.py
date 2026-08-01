# Copyright (c) 2026, DAS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today
import json

class StockMovementInter(Document):

    def on_submit(self):
        self.create_purchase_and_sales_invoice()

    def on_cancel(self):
        self.cancel_linked_invoices()

    def cancel_linked_invoices(self):
        sales_invoices = frappe.get_all(
            "Sales Invoice",
            filters={
                "custom_stock_movement_inter": self.name,
                "docstatus": 1
            },
            pluck="name"
        )

        for si_name in sales_invoices:
            si = frappe.get_doc("Sales Invoice", si_name)
            si.cancel()

        purchase_invoices = frappe.get_all(
            "Purchase Invoice",
            filters={
                "custom_stock_movement_inter": self.name,
                "docstatus": 1
            },
            pluck="name"
        )

        for pi_name in purchase_invoices:
            pi = frappe.get_doc("Purchase Invoice", pi_name)
            pi.cancel()

    def create_purchase_and_sales_invoice(self):
        settings = frappe.get_single("AXTRA Settings")

        mapping = {}
        for row in settings.stock_movement_inter_settings:
            mapping[(row.dikirim_dari, row.dikirim_ke)] = {
                "customer": row.customer_pos,
                "supplier": row.supplier_pinv,
            }

        for row in self.items:
            key = (row.from_company, row.to_company)
            map_row = mapping.get(key)

            if not map_row:
                frappe.throw(
                    f"Mapping {row.from_company} → {row.to_company} tidak ditemukan."
                )

            # bin_rate = frappe.db.get_value(
            #     "Bin",
            #     {"item_code": row.item_code, "warehouse": row.t_warehouse},
            #     "valuation_rate"
            # ) or 0  

            pi = frappe.get_doc({
                "doctype": "Purchase Invoice",
                "company": row.to_company,
                "supplier": map_row["supplier"],
                "update_stock": 1,
                "posting_date": self.posting_date,
                "custom_stock_movement_inter": self.name,
                "due_date": self.posting_date,
                "bill_date": self.posting_date,
                "items": [{
                    "item_code": row.item_code,
                    "qty": row.qty,
                    "rate": row.rate,          
                    "warehouse": row.t_warehouse
                }]
            })

            # frappe.throw(json.dumps({
            #     "posting_date": pi.posting_date,
            #     "bill_date": pi.bill_date,
            #     "due_date": pi.due_date,
            #     "items": [d.as_dict() for d in pi.items]
            # }, indent=2, default=str))

            pi.insert(ignore_mandatory=True)
            pi.submit()
            row.purchase_invoice_no = pi.name

            si = frappe.get_doc({
                "doctype": "Sales Invoice",
                "company": row.from_company,
                "customer": map_row["customer"],
                "update_stock": 1,
                "posting_date": self.posting_date,
                "custom_stock_movement_inter": self.name,
                "items": [{
                    "item_code": row.item_code,
                    "qty": row.qty,
                    "rate": row.rate,          
                    "warehouse": row.s_warehouse
                }]
            })

            si.insert()
            si.submit()
            row.sales_invoice_no = si.name

    def validate(self):
        self.validate_items()
        self.validate_company_mapping()

    def validate_company_mapping(self):
        if not self.items:
            return

        settings = frappe.get_single("AXTRA Settings")

        if not settings.stock_movement_inter_settings:
            frappe.throw(
                "Stock Movement Inter Settings belum diisi di AXTRA Settings."
            )

        mapping = {}
        for row in settings.stock_movement_inter_settings:
            if row.dikirim_dari and row.dikirim_ke:
                mapping[(row.dikirim_dari, row.dikirim_ke)] = {
                    "customer": row.customer_pos,
                    "supplier": row.supplier_pinv,
                }

        for row in self.items:
            if not row.from_company or not row.to_company:
                continue

            key = (row.from_company, row.to_company)

            if key not in mapping:
                frappe.throw(
                    f"Tidak ditemukan mapping Supplier/Customer "
                    f"dari <b>{row.from_company}</b> ke <b>{row.to_company}</b> "
                    f"di AXTRA Settings (baris item ke-{row.idx})."
                )

            customer = mapping[key].get("customer")
            supplier = mapping[key].get("supplier")

            if not customer or not supplier:
                frappe.throw(
                    f"Mapping <b>{row.from_company}</b> → <b>{row.to_company}</b> "
                    f"di AXTRA Settings belum lengkap.<br>"
                    f"Customer POS / Supplier PINV wajib diisi "
                    f"(baris item ke-{row.idx})."
                )

    def validate_items(self):
        if not self.items:
            frappe.throw("Item table tidak boleh kosong.")

        for row in self.items:
            if not row.item_code:
                frappe.throw(f"Item Code di baris {row.idx} tidak boleh kosong.")

            source_data = None
            target_data = None

            if self.source_company:
                source_data = get_vendor_company_and_default_warehouse(
                    item_code=row.item_code,
                    parent_company=self.source_company,
                    input_warehouse=self.from_warehouse
                )

            if self.target_company:
                target_data = get_vendor_company_and_default_warehouse(
                    item_code=row.item_code,
                    parent_company=self.target_company,
                    input_warehouse=self.to_warehouse
                )

            if source_data:
                row.from_company = source_data.get("company")
                row.s_warehouse = source_data.get("warehouse")
                row.rate = source_data.get("rate")

            if target_data:
                row.to_company = target_data.get("company")
                row.t_warehouse = target_data.get("warehouse")

            if not row.s_warehouse:
                frappe.throw(f"Warehouse di baris {row.idx} tidak valid atau tidak ditemukan.")
            if not row.t_warehouse:
                frappe.throw(f"Warehouse di baris {row.idx} tidak valid atau tidak ditemukan.")

@frappe.whitelist()
def get_vendor_company_and_default_warehouse(item_code, parent_company, input_warehouse=None):
    if not item_code or not parent_company:
        return {}

    vendor = frappe.db.get_value("Item", item_code, "custom_vendor")
    if not vendor:
        return {}

    company = None
    if parent_company == "BJB":
        company = frappe.db.get_value("Supplier", vendor, "custom_vendor_company")
    elif parent_company == "BJM":
        company = frappe.db.get_value("Supplier", vendor, "custom_vendor_company_bjm")

    if not company:
        return {}

    warehouse = None
    if input_warehouse:
        parts = input_warehouse.split(" - ")
        base_name = parts[0].strip()
        company_abbr = frappe.db.get_value("Company", company, "abbr") or ""
        warehouse = f"{base_name} - {company_abbr}"
        bin_warehouse = frappe.db.get_value("Warehouse", {"name": input_warehouse}, "name")
    else:
        warehouse = frappe.db.get_value(
            "Item Default",
            {"parent": item_code, "company": company},
            "default_warehouse"
        )
        if not warehouse:
            warehouse = frappe.db.get_value(
                "Warehouse",
                {"company": company, "is_group": 0, "disabled": 0},
                "name",
                order_by="creation asc"
            )
        bin_warehouse = warehouse

    rate = None
    if bin_warehouse:
        rate = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": bin_warehouse}, "valuation_rate")

        if not rate or rate == 0:
            last_pi_item = frappe.get_all(
                "Purchase Invoice Item",
                filters={"item_code": item_code},
                fields=["valuation_rate"],
                order_by="creation desc",
                limit_page_length=1
            )
            if last_pi_item:
                rate = last_pi_item[0].valuation_rate or 0

    return {
        "company": company,
        "warehouse": warehouse,
        "rate": rate
    }
