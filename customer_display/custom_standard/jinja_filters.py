import frappe
from datetime import timedelta
def debug():
	get_tutup_kasir("POS-CLO-2025-00005")

def get_tutup_kasir(name):
	doc = frappe.get_doc("POS Closing Entry", name)

	online_partai = online = total_online = kas_awal = jual_cash = jual_card = voucher = jumlah_jual = retur_cash = retur_card = discount_item = discount_nota = total_jual = kas_akhir = point_jual = point_retur = total_point = member_free = member_non_free = biaya_member = total_kas_akhir = pinjaman = total = uang_charge_kredit = total_tutup = 0
	
	for row in doc.payment_reconciliation:
		kas_awal = kas_awal + row.opening_amount
		if row.mode_of_payment == "Cash":
			jual_cash = jual_cash + (row.closing_amount - row.opening_amount)
		elif "Debit" in row.mode_of_payment or "Credit" in row.mode_of_payment:
			jual_card = jual_card + (row.closing_amount - row.opening_amount)
		elif "Online Partai" in row.mode_of_payment :
			online_partai = online_partai + (row.closing_amount - row.opening_amount)
		elif "Online" in row.mode_of_payment :
			online = online + (row.closing_amount - row.opening_amount)

	total_online = online_partai + online
	jumlah_jual = jual_cash  + jual_card

	customer_array = []

	for row in doc.pos_transactions:
		
		pos_invoice = frappe.get_doc("POS Invoice",row.pos_invoice)
		so_id = pos_invoice.get("custom_si_pos_id")
		so_no = pos_invoice.get("custom_si_pos_no")

		if pos_invoice.customer not in customer_array :
			customer_array.append(pos_invoice.customer)

		sales_invoice = frappe.db.get_value(
			"Sales Invoice",
			{
				"custom_si_pos_id": so_id,
				"custom_si_pos_no": so_no
			},
			["name"],
			as_dict=True
		)

		if sales_invoice:
			sales_invoice_name = sales_invoice.name
			sales_invoice_doc = frappe.get_doc("Sales Invoice", sales_invoice_name)
			total_return_amount = frappe.db.get_value(
				"Sales Invoice",
				{
					"is_return": 1,
					"return_against": sales_invoice_name
				},
				"SUM(grand_total)"
			)
			if sales_invoice.get("payments"):
				if sales_invoice.get("payments")[0].mode_of_payment == "Cash":
					retur_cash = retur_cash + total_return_amount
				else:
					retur_card = retur_card + total_return_amount

			for row_si in sales_invoice_doc.items:
				discount_item = discount_item + row_si.get("discount_amount") or 0

			discount_nota = discount_nota + sales_invoice_doc.get("discount_amount") or 0

			points = frappe.get_all(
				"Loyalty Point Entry",
				filters={
					"invoice": sales_invoice_name,
					"redeem_against": "",
					"loyalty_points": [">", 0]
				},
				pluck="loyalty_points"
			)
			total_poin_jual = sum(points) if points else 0

			point_jual = point_jual + total_poin_jual

	total_jual = jumlah_jual - retur_cash - retur_card
	kas_akhir = kas_awal + jual_cash - retur_cash
	
	total_point = point_jual - point_retur
	member_free = len(customer_array)

	start_date = doc.period_start_date.date() - timedelta(days=1)
	end_date = doc.period_end_date.date() + timedelta(days=1)

	pinjaman = frappe.db.sql("""
		SELECT SUM(jumlah_pinjaman)
		FROM `tabPinjaman`
		WHERE posting_date BETWEEN %s AND %s
		  AND pos_profile = %s
		  AND docstatus = 1
	""", (start_date, end_date, doc.pos_profile))[0][0] or 0

	total_kas_akhir = kas_akhir

	total = kas_akhir - pinjaman

	total_tutup = total - uang_charge_kredit	

	return [kas_awal, online_partai, online, total_online, jual_cash, jual_card, voucher, jumlah_jual, retur_cash, retur_card, discount_item, discount_nota, total_jual, kas_akhir, point_jual, point_retur, total_point, member_free, member_non_free, biaya_member, total_kas_akhir, pinjaman, total, uang_charge_kredit, total_tutup]