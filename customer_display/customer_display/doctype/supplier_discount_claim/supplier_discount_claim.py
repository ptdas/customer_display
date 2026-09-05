import frappe
from frappe.model.document import Document
from frappe.utils import flt


class SupplierDiscountClaim(Document):

	@frappe.whitelist()
	def get_data(self):

		if self.docstatus == 1:
			frappe.throw(
				"Document sudah Submit, tidak bisa Get Data lagi."
			)

		if not self.from_date or not self.to_date:
			frappe.throw(
				"From Date dan To Date wajib diisi."
			)

		if self.from_date > self.to_date:
			frappe.throw(
				"From Date tidak boleh lebih besar dari To Date."
			)

		if not self.supplier:
			frappe.throw(
				"Supplier wajib diisi."
			)

		pricing_rules = self.get_supplier_pricing_rules()

		if not pricing_rules:
			return []

		claimed = frappe.db.sql("""
			SELECT
				child.no_nota,
				child.sales_invoice_item,
				child.pricing_rule
			FROM `tabSupplier Discount Claim Item` child
			INNER JOIN `tabSupplier Discount Claim` parent
				ON parent.name = child.parent
			WHERE parent.docstatus = 1
		""", as_dict=True)

		claimed_map = {
			(
				row.no_nota,
				row.sales_invoice_item,
				row.pricing_rule
			)
			for row in claimed
		}

		result = []

		for rule in pricing_rules:

			item_codes = self.get_pricing_rule_items(rule)

			if not item_codes:
				continue

			conditions = [
				"si.docstatus = 1",
				"si.posting_date BETWEEN %(from_date)s AND %(to_date)s",
				"sii.item_code IN %(item_codes)s",
				"si.is_return = 0",
			]

			values = {
				"from_date": self.from_date,
				"to_date": self.to_date,
				"item_codes": tuple(item_codes),
				"supplier": self.supplier,
			}

			if self.brand:
				conditions.append(
					"item.brand = %(brand)s"
				)
				values["brand"] = self.brand

			data = frappe.db.sql(
				f"""
				SELECT
					si.name AS no_nota,
					si.posting_date AS tanggal,
					si.customer,
					si.owner AS nama_creator,
					si.pos_profile,
					sii.name AS sales_invoice_item,
					sii.item_code,
					sii.item_name,
					sii.qty,
					sii.price_list_rate AS harga_jual,
					item.brand
				FROM `tabSales Invoice` si
				INNER JOIN `tabSales Invoice Item` sii
					ON sii.parent = si.name
				INNER JOIN `tabItem` item
					ON item.name = sii.item_code
				WHERE
					{" AND ".join(conditions)}
				ORDER BY
					si.posting_date,
					si.name,
					sii.idx
				""",
				values,
				as_dict=True
			)

			for row in data:

				claim_key = (
					row.no_nota,
					row.sales_invoice_item,
					rule.name
				)

				if claim_key in claimed_map:
					continue

				harga_jual = flt(row.harga_jual)

				diskon = self.calculate_discount(
					rule,
					harga_jual
				)

				harga_setelah_diskon = max(
					harga_jual - diskon,
					0
				)

				discount_percentage = (
					(diskon / harga_jual) * 100
					if harga_jual
					else 0
				)

				jumlah = (
					flt(row.qty)
					* flt(diskon)
				)

				nama_customer = frappe.db.get_value(
					"Customer",
					row.customer,
					"customer_name"
				) or ""

				nama_user_penjual = ""

				if row.pos_profile:

					user_row = frappe.get_all(
						"POS Profile User",
						filters={
							"parent": row.pos_profile,
							"parenttype": "POS Profile",
						},
						fields=["user"],
						order_by="idx asc",
						limit=1,
					)

					if user_row and user_row[0].user:
						nama_user_penjual = frappe.db.get_value(
							"User",
							user_row[0].user,
							"full_name"
						) or user_row[0].user

				result.append({
					"no_nota": row.no_nota,
					"tanggal": row.tanggal,
					"pricing_rule": rule.name,
					"customer": row.customer,
					"brand": row.brand,
					"item_code": row.item_code,
					"item_name": row.item_name,
					"qty": flt(row.qty),
					"harga_jual": harga_jual,
					"harga_setelah_diskon": flt(
						harga_setelah_diskon
					),
					"price_list": rule.for_price_list,
					"diskon": flt(diskon),
					"discount_percentage": flt(
						discount_percentage
					),
					"jumlah": flt(jumlah),
					"sales_invoice_item": row.sales_invoice_item,
					"nama_customer": nama_customer,
					"nama_user_penjual": nama_user_penjual,
					"nama_creator": row.nama_creator,
				})

		return result

	def get_company_from_supplier(self):
		"""
		Menentukan company berdasarkan cabang user.

		Prioritas:
		1. BJM -> Supplier.custom_vendor_company_bjm
		2. BJB -> Supplier.custom_vendor_company
		"""

		if not self.supplier:
			frappe.throw(
				"Supplier wajib diisi."
			)

		# Ambil company dari Supplier
		supplier = frappe.db.get_value(
			"Supplier",
			self.supplier,
			[
				"custom_vendor_company",
				"custom_vendor_company_bjm",
			],
			as_dict=True,
		)

		if not supplier:
			frappe.throw(
				f"Supplier {self.supplier} tidak ditemukan."
			)

		user = frappe.get_doc(
			"User",
			frappe.session.user
		)

		user_companies = [
			row.company
			for row in user.get("cabang_user") or []
			if row.company
		]

		if "BJM" in user_companies:

			company = supplier.custom_vendor_company_bjm

			if not company:
				frappe.throw(
					f"Supplier {self.supplier} belum memiliki "
					"Custom Vendor Company BJM."
				)

			return company

		if "BJB" in user_companies:

			company = supplier.custom_vendor_company

			if not company:
				frappe.throw(
					f"Supplier {self.supplier} belum memiliki "
					"Custom Vendor Company."
				)

			return company

		frappe.throw(
			"User tidak memiliki cabang BJM atau BJB."
		)

	def on_submit(self):

		company = self.get_company_from_supplier()

		if self.company != company:
			self.db_set("company", company)
			self.company = company

		self.create_journal_entry(company)

	def create_journal_entry(self, company):

		if self.get("journal_entry"):
			existing_je = frappe.db.get_value(
				"Journal Entry",
				self.journal_entry,
				"docstatus"
			)

			if existing_je in (0, 1):
				return self.journal_entry

		total_amount = 0

		for row in self.get("claim_items") or []:
			total_amount += flt(row.jumlah)

		total_amount = flt(total_amount)

		if total_amount <= 0:
			frappe.throw(
				"Total diskon tidak boleh 0."
			)

		discount_account = frappe.db.get_single_value(
			"AXTRA Settings",
			"discount_pembelian"
		)

		if not discount_account:
			frappe.throw(
				"Field Discount Pembelian belum diset di AXTRA Settings."
			)

		company_abbr = frappe.db.get_value(
			"Company",
			company,
			"abbr"
		)

		if not company_abbr:
			frappe.throw(
				f"Abbreviation belum diset untuk company {company}."
			)

		parts = discount_account.rsplit(" - ", 1)

		if len(parts) == 2:
			debit_account_name = f"{parts[0]} - {company_abbr}"
		else:
			debit_account_name = discount_account

		debit_account = frappe.db.get_value(
			"Account",
			{
				"name": debit_account_name,
				"company": company,
				"is_group": 0,
			},
			"name"
		)

		if not debit_account:
			frappe.throw(
				f"Account debit '{debit_account_name}' "
				f"tidak ditemukan untuk company {company}."
			)

		credit_account = frappe.db.get_value(
			"Company",
			company,
			"default_payable_account"
		)

		if not credit_account:
			frappe.throw(
				f"Default Payable Account belum diset "
				f"untuk company {company}."
			)

		je = frappe.new_doc("Journal Entry")

		je.voucher_type = "Journal Entry"
		je.company = company
		je.posting_date = self.to_date

		je.user_remark = (
			f"Supplier Discount Claim {self.name}"
		)

		je.append(
			"accounts",
			{
				"account": debit_account,
				"debit_in_account_currency": total_amount,
				"credit_in_account_currency": 0,
			}
		)

		je.append(
			"accounts",
			{
				"account": credit_account,
				"party_type": "Supplier",
				"party": self.supplier,
				"debit_in_account_currency": 0,
				"credit_in_account_currency": total_amount,
			}
		)

		je.insert(
			ignore_permissions=True
		)

		je.submit()

		self.db_set(
			"journal_entry",
			je.name
		)

		return je.name

	def on_cancel(self):

		journal_entry = self.get("journal_entry")

		if not journal_entry:
			return

		if not frappe.db.exists(
			"Journal Entry",
			journal_entry
		):
			return

		je = frappe.get_doc(
			"Journal Entry",
			journal_entry
		)

		if je.docstatus == 1:
			je.cancel()

	def get_supplier_pricing_rules(self):

		return frappe.get_all(
			"Pricing Rule",
			filters=[
				["disable", "=", 0],
				[
					"custom_sumber_pricing_rule",
					"=",
					"Supplier"
				],
				[
					"valid_from",
					"<=",
					self.to_date
				],
			],
			or_filters=[
				[
					"valid_upto",
					"is",
					"not set"
				],
				[
					"valid_upto",
					">=",
					self.from_date
				]
			],
			fields=[
				"name",
				"disable",
				"custom_sumber_pricing_rule",
				"valid_from",
				"valid_upto",
				"apply_on",
				"for_price_list",
				"price_or_product_discount",
				"rate_or_discount",
				"discount_percentage",
				"discount_amount",
				"rate",
				"currency",
			],
			order_by="valid_from asc, name asc"
		)

	def get_item_price(self, price_list, item_code):

		if not price_list or not item_code:
			return 0

		price = frappe.db.get_value(
			"Item Price",
			{
				"price_list": price_list,
				"item_code": item_code,
			},
			"price_list_rate"
		)

		return flt(price)

	def calculate_discount(self, rule, base_price):

		base_price = flt(base_price)

		if not base_price:
			return 0

		if rule.rate_or_discount == "Discount Percentage":
			return max(
				base_price
				* flt(rule.discount_percentage)
				/ 100,
				0
			)

		if rule.rate_or_discount == "Discount Amount":
			return max(
				flt(rule.discount_amount),
				0
			)

		if rule.rate_or_discount == "Rate":
			rate = flt(rule.rate)

			if rate:
				return max(
					base_price - rate,
					0
				)

		return 0

	def get_pricing_rule_items(self, rule):

		item_codes = set()

		pricing_rule = frappe.get_doc(
			"Pricing Rule",
			rule.name
		)

		if pricing_rule.apply_on == "Item Code":

			codes = [
				row.item_code
				for row in pricing_rule.get("items") or []
				if row.item_code
			]

			if codes:

				items = frappe.get_all(
					"Item",
					fields=[
						"name",
						"variant_of",
					],
					filters=[
						["has_variants", "=", 0],
						["disabled", "=", 0],
					],
					or_filters=[
						["name", "in", codes],
						["variant_of", "in", codes],
					],
				)

				item_codes.update(
					item.name
					for item in items
				)

		elif pricing_rule.apply_on == "Item Group":

			groups = [
				row.item_group
				for row in pricing_rule.get("item_groups") or []
				if row.item_group
			]

			if groups:

				group_data = frappe.get_all(
					"Item Group",
					fields=[
						"name",
						"lft",
						"rgt",
					]
				)

				for target_group in groups:

					target = next(
						(
							d
							for d in group_data
							if d.name == target_group
						),
						None
					)

					if not target:
						continue

					descendant_groups = [
						d.name
						for d in group_data
						if d.lft >= target.lft
						and d.rgt <= target.rgt
					]

					if not descendant_groups:
						continue

					items = frappe.get_all(
						"Item",
						filters=[
							["has_variants", "=", 0],
							["disabled", "=", 0],
							[
								"item_group",
								"in",
								descendant_groups,
							],
						],
						pluck="name",
					)

					item_codes.update(items)

		elif pricing_rule.apply_on == "Brand":

			brands = [
				row.brand
				for row in pricing_rule.get("brands") or []
				if row.brand
			]

			if brands:

				items = frappe.get_all(
					"Item",
					filters=[
						["has_variants", "=", 0],
						["disabled", "=", 0],
						["brand", "in", brands],
					],
					pluck="name",
				)

				item_codes.update(items)

		return list(item_codes)