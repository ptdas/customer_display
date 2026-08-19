# Copyright (c) 2026, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, fmt_money
from frappe.utils.pdf import get_pdf


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("pricing_rule"):
		return [], []

	report = PricingRuleImpact(filters)
	return report.columns(), report.rows(), report.message(), None, report.summary()


class PricingRuleImpact:
	"""Expands one Pricing Rule into the concrete list of Items it can hit.

	A rule stores its target as Item Code / Item Group / Brand. Item Group targets
	cascade down the nested set, and an Item Code target also covers the variants of
	a template, so the stored rows are never the real list of affected items.
	"""

	ITEM_FIELDS = ["name as item_code", "item_name", "item_group", "brand", "variant_of"]

	def __init__(self, filters):
		self.filters = filters
		self.rule = frappe.get_doc("Pricing Rule", filters.pricing_rule)
		self._group_tree = None

	# ---------------------------------------------------------------- output

	def columns(self):
		return [
			{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 180},
			{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
			# {"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 140},
			# {"label": _("Brand"), "fieldname": "brand", "fieldtype": "Link", "options": "Brand", "width": 110},
			{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
			# {"label": _("Role"), "fieldname": "role", "fieldtype": "Data", "width": 130},
			# {"label": _("Matched Via"), "fieldname": "matched_via", "fieldtype": "Data", "width": 200},
			# {"label": _("UOM (Rule)"), "fieldname": "rule_uom", "fieldtype": "Link", "options": "UOM", "width": 100},
			#{"label": _("Discount Type"), "fieldname": "discount_type", "fieldtype": "Data", "width": 150},
			# {"label": _("Discount"), "fieldname": "discount_display", "fieldtype": "Data", "width": 150},
			{"label": _("Discount %"), "fieldname": "discount_percentage", "fieldtype": "Percent", "width": 110},
			{"label": _("Discount Amount"), "fieldname": "discount_amount", "fieldtype": "Currency", "options": "currency", "width": 130},
			# {"label": _("Rate"), "fieldname": "rate", "fieldtype": "Currency", "options": "currency", "width": 110},
			# {"label": _("Margin"), "fieldname": "margin", "fieldtype": "Data", "width": 110},
			{
				"label": _("Price Before Discount"),
				"fieldname": "price_before_discount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 140,
			},
			{
				"label": _("Price After Discount"),
				"fieldname": "price_after_discount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 140,
			},
			# {"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 90},
		]

	def rows(self):
		# When "Apply Rule On Other" is set, the listed items are only the condition;
		# the discount lands on a different item.
		discount_is_elsewhere = bool(self.rule.apply_rule_on_other)

		rows = self._collect(
			self.rule.apply_on,
			self._condition_targets(),
			role=_("Trigger Only") if discount_is_elsewhere else _("Discounted"),
			discounted=not discount_is_elsewhere,
		)
		if discount_is_elsewhere:
			rows += self._collect(
				self.rule.apply_rule_on_other,
				self._other_targets(),
				role=_("Discounted"),
				discounted=True,
			)

		rows.sort(key=lambda row: (row["role"], row["item_code"]))
		return rows

	def summary(self):
		discounted = [row for row in self.rows() if row["discount_display"]]
		return [
			{"label": _("Affected Items"), "value": len(discounted), "datatype": "Int"},
			{"label": _("Discount"), "value": self.discount_label(), "datatype": "Data"},
			{
				"label": _("Status"),
				"value": _("Disabled") if self.rule.disable else _("Enabled"),
				"datatype": "Data",
				"indicator": "Red" if self.rule.disable else "Green",
			},
		]

	def message(self):
		rule = self.rule
		facts = [
			(_("Discount"), self.discount_label()),
			(_("Apply On"), rule.apply_on),
			(_("Applicable For"), self._applicable_for()),
			(_("Valid"), self._validity()),
			(_("Qty Range"), self._range(rule.min_qty, rule.max_qty)),
			(_("Amount Range"), self._range(rule.min_amt, rule.max_amt)),
			(_("Price List"), rule.get("for_price_list")),
			(_("Company"), rule.company),
			(_("Priority"), rule.priority),
		]
		notes = self._notes()

		body = "".join(
			f"<tr><td style='padding:2px 16px 2px 0;color:#6b7280;white-space:nowrap'>{label}</td>"
			f"<td style='padding:2px 0'><b>{value}</b></td></tr>"
			for label, value in facts
			if value not in (None, "", 0)
		)
		note_html = "".join(f"<div style='margin-top:6px;color:#8d5b00'>⚠ {note}</div>" for note in notes)
		# return f"<table style='font-size:13px'>{body}</table>{note_html}"
		return f"""
				<div class="report-message" style="margin-bottom:16px">
					<table style="font-size:13px">
						{body}
					</table>
					{note_html}
				</div>
				"""

	# ------------------------------------------------------------ targeting

	def _condition_targets(self):
		"""{target value: uom restriction} taken from the rule's child tables."""
		if self.rule.apply_on == "Item Code":
			return {row.item_code: row.uom for row in self.rule.items}
		if self.rule.apply_on == "Item Group":
			return {row.item_group: row.uom for row in self.rule.item_groups}
		if self.rule.apply_on == "Brand":
			return {row.brand: row.uom for row in self.rule.brands}
		return {}

	def _other_targets(self):
		field = {
			"Item Code": "other_item_code",
			"Item Group": "other_item_group",
			"Brand": "other_brand",
		}.get(self.rule.apply_rule_on_other)
		value = self.rule.get(field) if field else None
		return {value: None} if value else {}

	# def _collect(self, apply_on, targets, role, discounted):
	# 	if not targets:
	# 		return []

	# 	fetchers = {
	# 		"Item Code": self._items_by_code,
	# 		"Item Group": self._items_by_group,
	# 		"Brand": self._items_by_brand,
	# 	}
	# 	fetcher = fetchers.get(apply_on)
	# 	if not fetcher:
	# 		return []

	# 	discount = self._discount_fields() if discounted else {}
	# 	return [
	# 		{
	# 			"item_code": item.item_code,
	# 			"item_name": item.item_name,
	# 			"item_group": item.item_group,
	# 			"brand": item.brand,
	# 			"role": role,
	# 			"matched_via": f"{_(apply_on)}: {item.matched_value}",
	# 			"rule_uom": targets.get(item.matched_value),
	# 			"currency": self.rule.currency,
	# 			**discount,
	# 		}
	# 		for item in fetcher(list(targets))
	# 	]

	def _get_balance_qty_map(self, item_codes):
		if not item_codes:
			return {}

		data = frappe.db.sql(
			"""
			SELECT
				item_code,
				SUM(actual_qty) AS qty
			FROM `tabBin`
			WHERE item_code IN %(item_codes)s
			GROUP BY item_code
			""",
			{"item_codes": tuple(item_codes)},
			as_dict=True,
		)

		return {d.item_code: flt(d.qty) for d in data}

	def _collect(self, apply_on, targets, role, discounted):
		if not targets:
			return []

		fetchers = {
			"Item Code": self._items_by_code,
			"Item Group": self._items_by_group,
			"Brand": self._items_by_brand,
		}

		fetcher = fetchers.get(apply_on)
		if not fetcher:
			return []

		discount = self._discount_fields() if discounted else {}

		items = fetcher(list(targets))
		item_codes = [d.item_code for d in items]

		price_map = self._get_item_price_map(item_codes)
		qty_map = self._get_balance_qty_map(item_codes)

		rows = []

		for item in items:
			base_price = flt(price_map.get(item.item_code))
			after_price = self._calculate_discounted_price(base_price) if discounted else base_price

			# hitung nilai diskon aktual
			actual_discount_amount = max(base_price - after_price, 0)
			actual_discount_percentage = (
				(actual_discount_amount / base_price) * 100
				if base_price else 0
			)

			# tetap ambil field bawaan (termasuk discount_display)
			row_discount = dict(discount)
			row_discount["discount_percentage"] = actual_discount_percentage
			row_discount["discount_amount"] = actual_discount_amount

			rows.append({
				"item_code": item.item_code,
				"item_name": item.item_name,
				"item_group": item.item_group,
				"brand": item.brand,
				"qty": flt(qty_map.get(item.item_code)),
				"role": role,
				"matched_via": f"{_(apply_on)}: {item.matched_value}",
				"rule_uom": targets.get(item.matched_value),
				"price_before_discount": base_price,
				"price_after_discount": after_price,
				"currency": self.rule.currency,
				**row_discount,
			})

		return rows

	def _items_by_code(self, codes):
		items = frappe.get_all(
			"Item",
			fields=self.ITEM_FIELDS,
			filters=self._item_filters(),
			or_filters=[["name", "in", codes], ["variant_of", "in", codes]],
		)
		for item in items:
			item.matched_value = item.item_code if item.item_code in codes else item.variant_of
		return items

	def _items_by_group(self, groups):
		# Map every descendant group back to the group actually named on the rule.
		descendants = {}
		for group in groups:
			for child in self._descendant_groups(group):
				descendants.setdefault(child, group)

		items = frappe.get_all(
			"Item",
			fields=self.ITEM_FIELDS,
			filters=self._item_filters() + [["item_group", "in", list(descendants)]],
		)
		for item in items:
			item.matched_value = descendants.get(item.item_group)
		return items

	def _items_by_brand(self, brands):
		items = frappe.get_all(
			"Item",
			fields=self.ITEM_FIELDS,
			filters=self._item_filters() + [["brand", "in", brands]],
		)
		for item in items:
			item.matched_value = item.brand
		return items

	def _item_filters(self):
		# Templates never appear on a transaction line, so they are not "affected".
		filters = [["has_variants", "=", 0]]
		if not self.filters.get("include_disabled_items"):
			filters.append(["disabled", "=", 0])
		return filters

	def _descendant_groups(self, group):
		if self._group_tree is None:
			self._group_tree = frappe.get_all("Item Group", fields=["name", "lft", "rgt"])

		node = next((row for row in self._group_tree if row.name == group), None)
		if not node:
			return [group]
		return [row.name for row in self._group_tree if row.lft >= node.lft and row.rgt <= node.rgt]

	# ------------------------------------------------------------- discount

	def _discount_fields(self):
		rule = self.rule
		fields = {
			"discount_type": _(rule.rate_or_discount or ""),
			"discount_display": self.discount_label(),
			"margin": self._margin_label(),
		}
		if rule.price_or_product_discount == "Product":
			fields["discount_type"] = _("Free Item")
			return fields

		fields["discount_percentage"] = flt(rule.discount_percentage)
		fields["discount_amount"] = flt(rule.discount_amount)
		fields["rate"] = flt(rule.rate)
		return fields

	def discount_label(self):
		rule = self.rule
		if rule.price_or_product_discount == "Product":
			uom = f" {rule.free_item_uom}" if rule.free_item_uom else ""
			return _("Free {0}{1} x {2}").format(flt(rule.free_qty), uom, rule.free_item or "-")
		if rule.rate_or_discount == "Discount Percentage":
			return f"{flt(rule.discount_percentage)}%"
		if rule.rate_or_discount == "Discount Amount":
			return self._money(rule.discount_amount)
		if rule.rate_or_discount == "Rate":
			return _("Fixed Rate {0}").format(self._money(rule.rate))
		return self._margin_label() or "-"

	def _margin_label(self):
		if not self.rule.margin_type or not flt(self.rule.margin_rate_or_amount):
			return ""
		amount = flt(self.rule.margin_rate_or_amount)
		suffix = "%" if self.rule.margin_type == "Percentage" else ""
		return _("Margin {0}{1}").format(amount, suffix)

	def _money(self, value):
		return fmt_money(flt(value), currency=self.rule.currency)

	# ---------------------------------------------------------------- notes

	def _notes(self):
		rule = self.rule
		notes = []
		if rule.apply_on == "Transaction":
			notes.append(_("This rule applies to the whole transaction, so it targets no specific item."))
		if rule.mixed_conditions:
			notes.append(_("Mixed Conditions is on: the qty/amount limits are evaluated across all listed items together, not per item."))
		if rule.is_cumulative:
			notes.append(_("Is Cumulative is on: qty/amount is accumulated over the validity period."))
		if rule.apply_rule_on_other:
			notes.append(_("Apply Rule On Other is set: the listed items only trigger the rule, the discount goes to the other item."))
		if rule.disable:
			notes.append(_("This rule is disabled and currently has no effect."))
		return notes

	def _applicable_for(self):
		if not self.rule.applicable_for:
			return _("All")
		field = frappe.scrub(self.rule.applicable_for)
		values = self.rule.get(field)
		if isinstance(values, list):
			values = ", ".join(row.get(field) for row in values if row.get(field))
		return f"{self.rule.applicable_for}: {values or _('All')}"

	def _validity(self):
		if not (self.rule.valid_from or self.rule.valid_upto):
			return ""
		return f"{self.rule.valid_from or '-'} → {self.rule.valid_upto or '∞'}"

	def _range(self, minimum, maximum):
		if not (flt(minimum) or flt(maximum)):
			return ""
		return f"{flt(minimum)} → {flt(maximum) or '∞'}"

	def _get_item_price_map(self, item_codes):
		if not item_codes or not self.rule.for_price_list:
			return {}

		prices = frappe.get_all(
			"Item Price",
			filters={
				"price_list": self.rule.for_price_list,
				"item_code": ["in", item_codes],
			},
			fields=["item_code", "price_list_rate"],
		)

		return {p.item_code: flt(p.price_list_rate) for p in prices}

	def _calculate_discounted_price(self, base_price):
		rule = self.rule

		if not base_price:
			return 0

		# Diskon persen
		if rule.rate_or_discount == "Discount Percentage":
			return base_price - (base_price * flt(rule.discount_percentage) / 100)

		# Diskon nominal
		if rule.rate_or_discount == "Discount Amount":
			return base_price - flt(rule.discount_amount)

		# Harga tetap
		if rule.rate_or_discount == "Rate" and flt(rule.rate):
			return flt(rule.rate)

		# Free item / tidak ada perubahan harga
		return base_price



@frappe.whitelist()
def print_pdf(pricing_rule):

	filters = frappe._dict({
		"pricing_rule": pricing_rule
	})

	report = PricingRuleImpact(filters)
	rows = report.rows()
	rule = report.rule

	periode = f"{rule.valid_from or '-'} s.d {rule.valid_upto or '-'}"
	applicable_for = report._applicable_for()
	title = rule.title or "-"
	price_list = rule.for_price_list or "-"

	html = f"""
	<style>
	@page {{
		size: A4 landscape;
		margin: 12mm;
	}}

	body {{
		font-family: Arial, sans-serif;
		font-size: 11px;
	}}

	.header {{
		display: flex;
		justify-content: space-between;
		margin-bottom: 6px;
	}}

	.title {{
		text-align: center;
		font-size: 16px;
		font-weight: bold;
		margin-bottom: 6px;
	}}

	.info {{
		display: flex;
		justify-content: space-between;
		margin-bottom: 8px;
		font-weight: bold;
	}}

	table {{
		width: 100%;
		border-collapse: collapse;
	}}

	th, td {{
		border: 1px solid #000;
		padding: 4px 6px;
	}}

	th {{
		background: #f0f0f0;
		text-align: center;
	}}

	.num {{
		text-align: right;
	}}

	.center {{
		text-align: center;
	}}
	</style>

	<div class="header">
		<div>Dicetak Pada: {frappe.utils.format_datetime(frappe.utils.now_datetime(), "dd/MM/yyyy HH:mm:ss")}</div>
		<div>Halaman: 1</div>
	</div>

	<div class="title">Laporan Setting Promo Diskon</div>

	<div class="info">
		<div>
			<div style="font-size:12px;margin-bottom:2px;">{title}</div>
			<div style="font-size:13px;font-weight:bold;margin-bottom:2px;">{rule.name}</div>
			<div>{applicable_for}</div>
		</div>

		<div style="text-align:right;">
			<div style="margin-bottom:2px;">Price List: {price_list}</div>
			<div>Periode: {periode}</div>
		</div>
	</div>

	<table>
		<thead>
			<tr>
				<th width="40">No</th>
				<th width="140">Kode Barang</th>
				<th>Nama Barang</th>
				<th width="60">Qty</th>
				<th width="90">Hrg Jual</th>
				<th width="60">D%</th>
				<th width="90">Disc Rp</th>
				<th width="90">H.Netto</th>
			</tr>
		</thead>
		<tbody>
	"""

	for i, row in enumerate(rows, 1):

		base_price = row.get("price_before_discount", 0) or 0
		after_price = row.get("price_after_discount", 0) or 0
		disc_pct = row.get("discount_percentage", 0) or 0
		disc_amt = row.get("discount_amount", 0) or 0
		qty = row.get("qty", 0) or 0

		html += f"""
		<tr>
			<td class="center">{i}</td>
			<td>{row.get('item_code', '')}</td>
			<td>{row.get('item_name', '')}</td>
			<td class="center">{qty:,.0f}</td>
			<td class="num">{base_price:,.0f}</td>
			<td class="num">{disc_pct:,.0f}</td>
			<td class="num">{disc_amt:,.0f}</td>
			<td class="num">{after_price:,.0f}</td>
		</tr>
		"""

	html += "</tbody></table>"

	pdf = get_pdf(html)

	frappe.local.response.filename = f"Promo-{rule.name}.pdf"
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "pdf"