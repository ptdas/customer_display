import frappe
from datetime import timedelta
def debug():
	get_tutup_kasir("POS-CLO-2025-00034")

def get_tutup_kasir(name):
	doc = frappe.get_doc("POS Closing Entry", name)

	online_partai = online = total_online = kas_awal = jual_cash = jual_card = voucher = jumlah_jual = retur_cash = retur_card = discount_item = discount_nota = total_jual = kas_akhir = point_jual = point_retur = total_point = member_free = member_non_free = biaya_member = total_kas_akhir = pinjaman = total = uang_charge_kredit = total_tutup = 0
	try:
		if len(doc.taxes)>0:
			uang_charge_kredit = doc.taxes[0].amount
	except:
		pass

	for row in doc.payment_reconciliation:
		kas_awal = kas_awal + row.opening_amount

	for satu_pos in doc.pos_transactions:
		pos_doc = frappe.get_doc("POS Invoice", satu_pos.pos_invoice)
		for row in pos_doc.payments:
			mop_doc = frappe.get_doc("Mode of Payment",row.mode_of_payment)
			if satu_pos.is_return == 0:
				if mop_doc.custom_mop_type == "Cash":
					jual_cash = jual_cash + row.base_amount
				elif mop_doc.custom_mop_type == "Bank":
					jual_card = jual_card + row.base_amount
				elif mop_doc.custom_mop_type == "Online Partai" :
					online_partai = online_partai + row.base_amount
				elif mop_doc.custom_mop_type == "Online" :
					online = online + row.base_amount

	total_online = online_partai + online
	jumlah_jual = jual_cash  + jual_card - uang_charge_kredit

	customer_array = []

	total_change = 0 

	for row in doc.pos_transactions:
		
		pos_invoice = frappe.get_doc("POS Invoice",row.pos_invoice)
		so_id = pos_invoice.get("custom_si_pos_id")
		so_no = pos_invoice.get("custom_si_pos_no")

		total_change += pos_invoice.change_amount 

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

		if row.is_return == 1:
			retur_doc = frappe.get_doc("POS Invoice", row.pos_invoice)
			asli_doc = frappe.get_doc("POS Invoice", retur_doc.return_against)
			for satu_payment in asli_doc.get("payments"):
				if satu_payment.base_amount:
					if satu_payment.mode_of_payment == "Cash":
						retur_cash = retur_cash + (row.grand_total * -1)
					else:
						retur_card = retur_card + (row.grand_total * -1)

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
			# if sales_invoice.get("payments"):
			# 	if sales_invoice.get("payments")[0].mode_of_payment == "Cash":
			# 		retur_cash = retur_cash + total_return_amount
			# 	else:
			# 		retur_card = retur_card + total_return_amount

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
	jual_cash = jual_cash - total_change
	kas_akhir = kas_awal + jual_cash - retur_cash
	
	total_point = point_jual - point_retur
	#member_free = len(customer_array)
	member_free = 0
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
	print(str([kas_awal, online_partai, online, total_online, jual_cash, jual_card, voucher, jumlah_jual, retur_cash, retur_card, discount_item, discount_nota, total_jual, kas_akhir, point_jual, point_retur, total_point, member_free, member_non_free, biaya_member, total_kas_akhir, pinjaman, total, uang_charge_kredit, total_tutup]))
	return [kas_awal, online_partai, online, total_online, jual_cash, jual_card, voucher, jumlah_jual, retur_cash, retur_card, discount_item, discount_nota, total_jual, kas_akhir, point_jual, point_retur, total_point, member_free, member_non_free, biaya_member, total_kas_akhir, pinjaman, total, uang_charge_kredit, total_tutup, total_change]
