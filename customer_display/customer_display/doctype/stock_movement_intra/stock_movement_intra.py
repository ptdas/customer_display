# Copyright (c) 2026, DAS and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from collections import defaultdict

from frappe import _
import frappe

class StockMovementIntra(Document):

    def validate(self):
        self.validate_warehouse()

    def validate_warehouse(self):
        if not self.parent_company:
            return

        for row in self.items:
            custom_vendor = frappe.db.get_value(
                "Item",
                row.item_code,
                "custom_vendor"
            )

            if not custom_vendor:
                frappe.throw(
                    f"Row {row.idx}: Item <b>{row.item_code}</b> belum punya Vendor",
                    title="Vendor Tidak Ditemukan"
                )

            supplier = frappe.db.get_value(
                "Supplier",
                custom_vendor,
                ["custom_vendor_company", "custom_vendor_company_bjm"],
                as_dict=True
            )

            if not supplier:
                frappe.throw(
                    f"Row {row.idx}: Supplier <b>{custom_vendor}</b> tidak ditemukan",
                    title="Supplier Tidak Valid"
                )

            if self.parent_company == "BJB":
                row.child_company = supplier.custom_vendor_company
            elif self.parent_company == "BJM":
                row.child_company = supplier.custom_vendor_company_bjm

            if not row.child_company:
                frappe.throw(
                    f"Row {row.idx}: Company vendor belum diset untuk {self.parent_company}",
                    title="Company Vendor Kosong"
                )

            child_abbr = frappe.db.get_value(
                "Company",
                row.child_company,
                "abbr"
            )

            if not child_abbr:
                frappe.throw(
                    f"Row {row.idx}: Abbr company <b>{row.child_company}</b> belum diisi",
                    title="Company Abbr Kosong"
                )

            if row.s_warehouse:
                base_wh = row.s_warehouse.rsplit(" - ", 1)[0]
                row.s_warehouse = f"{base_wh} - {child_abbr}"

            if row.t_warehouse:
                base_wh = row.t_warehouse.rsplit(" - ", 1)[0]
                row.t_warehouse = f"{base_wh} - {child_abbr}"

            if self.from_warehouse:
                base_wh = self.from_warehouse.rsplit(" - ", 1)[0]
                row.s_warehouse = f"{base_wh} - {child_abbr}"

            if self.to_warehouse:
                base_wh = self.to_warehouse.rsplit(" - ", 1)[0]
                row.t_warehouse = f"{base_wh} - {child_abbr}"

    def on_submit(self):
        process_material_transfer(self)

    def on_cancel(self):
        stock_entries = frappe.get_all(
            "Stock Entry",
            filters={"custom_stock_movement_intra": self.name, "docstatus": 1},
            pluck="name"
        )

        for se_name in stock_entries:
            try:
                se = frappe.get_doc("Stock Entry", se_name)
                se.cancel()
            except Exception as e:
                frappe.log_error(e, f"Gagal cancel Stock Entry {se_name} terkait {self.name}")



#################### custom

def get_stock_qty(item_code, warehouse):
    return frappe.db.get_value(
        "Bin",
        {
            "item_code": item_code,
            "warehouse": warehouse
        },
        "actual_qty"
    ) or 0

def get_item_company(item_code, company_mode):
    item = frappe.get_cached_doc("Item", item_code)

    if not item.custom_vendor:
        frappe.throw(f"Item {item_code} tidak memiliki Vendor")

    supplier = frappe.get_cached_doc("Supplier", item.custom_vendor)

    if company_mode == "BJB":
        company = supplier.custom_vendor_company
    elif company_mode == "BJM":
        company = supplier.custom_vendor_company_bjm
    else:
        frappe.throw("Company Mode tidak valid")

    if not company:
        frappe.throw(
            f"Company untuk item {item_code} tidak ditemukan "
            f"(mode {company_mode})"
        )

    return company

# def group_items_by_company(doc):
#     grouped = defaultdict(list)

#     for row in doc.items:
#         company = get_item_company(row.item_code, doc.parent_company)
#         grouped[company].append(row)

#     return grouped

def group_items_by_company(doc):
    if doc.stock_entry_type == "Repack":
        first_company = get_item_company(doc.items[0].item_code, doc.parent_company)
        
        for row in doc.items:
            row_company = get_item_company(row.item_code, doc.parent_company)
            if row_company != first_company:
                frappe.throw(
                    f"Item {row.item_code} memiliki company {row_company} "
                    f"yang berbeda dari item pertama {first_company}. "
                    "Semua item untuk Repack harus dari company yang sama."
                )
        return {first_company: doc.items}
    
    grouped = defaultdict(list)
    for row in doc.items:
        company = get_item_company(row.item_code, doc.parent_company)
        grouped[company].append(row)
    return grouped


def validate_stock(grouped_items):
    for company, items in grouped_items.items():
        for row in items:
            available_qty = get_stock_qty(row.item_code, row.s_warehouse)

            if available_qty < row.qty:
                frappe.throw(
                    title="Stock Tidak Cukup",
                    msg=(
                        f"Item <b>{row.item_code}</b> tidak mencukupi untuk Intra!\n"
                        f"- Warehouse Sumber: <b>{row.s_warehouse}</b>\n"
                        f"- Stock Tersedia: <b>{available_qty}</b>\n"
                        f"- Qty Diminta: <b>{row.qty}</b>\n"
                        f"Silakan hubungi SYSTEM SUPPORT."
                    )
                )

def process_material_transfer(doc):
    validate_material_transfer(doc)

    grouped_items = group_items_by_company(doc)

    if doc.stock_entry_type in ["Material Transfer", "Material Issue"]:
        validate_stock(grouped_items)

    stock_entries = create_stock_entries(doc, grouped_items)

    submit_stock_entries(stock_entries)



def validate_material_transfer(doc):
    allowed_types = [
        "Material Transfer",
        "Material Issue",
        "Material Receipt",
        "Repack"
    ]

    if doc.stock_entry_type not in allowed_types:
        frappe.throw(
            _("Stock Entry Type tidak didukung: {0}")
            .format(doc.stock_entry_type)
        )

    if not doc.items:
        frappe.throw("Item tidak boleh kosong")

    for row in doc.items:
        if not row.item_code:
            frappe.throw("Terdapat baris item tanpa Item Code")

        if row.qty <= 0:
            frappe.throw(
                f"Qty harus lebih dari 0 untuk item {row.item_code}"
            )

        if doc.stock_entry_type in ["Material Transfer", "Material Issue"]:
            if not row.s_warehouse:
                frappe.throw(
                    f"Warehouse sumber wajib diisi "
                    f"untuk item {row.item_code}"
                )

        if doc.stock_entry_type in ["Material Transfer", "Material Receipt"]:
            if not row.t_warehouse:
                frappe.throw(
                    f"Warehouse tujuan wajib diisi "
                    f"untuk item {row.item_code}"
                )

        if (
            doc.stock_entry_type == "Material Transfer"
            and row.s_warehouse == row.t_warehouse
        ):
            frappe.throw(
                f"Warehouse sumber dan tujuan tidak boleh sama "
                f"untuk item {row.item_code}"
            )

def create_stock_entries(doc, grouped_items):
    created = []

    for company, items in grouped_items.items():
        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = doc.stock_entry_type
        se.company = company
        se.custom_stock_movement_intra = doc.name

        for row in items:
            item_doc = frappe.get_cached_doc("Item", row.item_code)

            item_data = {
                "item_code": row.item_code,
                "qty": row.qty,
                "uom": item_doc.stock_uom,
                "stock_uom": item_doc.stock_uom,
                "conversion_factor": 1,
            }

            if doc.stock_entry_type in ["Material Transfer", "Material Issue", "Repack"]:
                item_data["s_warehouse"] = row.s_warehouse

            if doc.stock_entry_type in ["Material Transfer", "Material Receipt", "Repack"]:
                item_data["t_warehouse"] = row.t_warehouse

            se.append("items", item_data)

        se.insert()
        created.append(se)

        for row in items:
            row.stock_entry = se.name

    doc.save(ignore_permissions=True)
    return created


def submit_stock_entries(entries):
    for se in entries:
        se.submit()

@frappe.whitelist()
def get_warehouses_by_parent(company):
    
	companies = frappe.get_all("Company", filters={"parent_company": company}, pluck="name")
	companies.append(company)

	warehouses = frappe.get_all("Warehouse", filters={"company": ["in", companies]}, pluck="name")
	return warehouses
