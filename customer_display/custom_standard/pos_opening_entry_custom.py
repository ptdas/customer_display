import frappe
from frappe.utils import nowdate
from frappe.utils import flt, get_datetime, getdate
from frappe import _
from datetime import datetime, time

# from customer_display.custom_standard.jinja_filters import get_tutup_kasir
from datetime import timedelta

def validate_get_tutup_kasir(self, method):

	data = get_tutup_kasir(self)

	if not data:
		return

	self.custom_kas_awal = data[0]
	self.custom_online_partai = data[1]
	self.custom_online = data[2]
	self.custom_total_online = data[3]
	self.custom_jual_cash = data[4]
	self.custom_jual_card = data[5]
	self.custom_voucher = data[6]
	self.custom_jumlah_jual = data[7]
	self.custom_retur_cash = data[8]
	self.custom_retur_card = data[9]
	self.custom_discount_item = data[10]
	self.custom_discount_nota = data[11]
	self.custom_total_jual = data[12]
	self.custom_kas_akhir = data[13]

	self.custom_member_free = data[17]
	self.custom_member_non_free = data[18]
	self.custom_biaya_member = data[19]
	self.custom_total_kas_akhir = data[20]
	self.custom_pinjaman = data[21]
	self.custom_total = data[22]
	self.custom_uang_charge_kredit = data[23]
	self.custom_total_tutup = data[24]

def get_tutup_kasir(self):
	doc = self

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

	jumlah_jual = jumlah_jual - total_change
	total_jual = jumlah_jual - retur_cash - retur_card
	jual_cash = jual_cash - total_change
	kas_akhir = kas_awal + jual_cash - retur_cash
	
	total_point = point_jual - point_retur
	#member_free = len(customer_array)
	member_free = 0
	# start_date = doc.period_start_date.date() - timedelta(days=1)
	# end_date = doc.period_end_date.date() + timedelta(days=1)

	start_date = get_datetime(doc.period_start_date).date() - timedelta(days=1)
	end_date = get_datetime(doc.period_end_date).date() + timedelta(days=1)


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


def check_double(self,method):
	user = frappe.session.user

	if "99_ByPass Open POS" in frappe.get_roles(user):
		return 

	existing = frappe.db.exists("POS Opening Entry", {
		"user": self.user,
		"posting_date": self.posting_date,
		"docstatus": ("!=", 2),
		"name": ("!=", self.name)
	})

	if existing:
		frappe.throw(f"User '{self.user}' already has a POS Opening Entry for today.")

@frappe.whitelist()
def ambil_closing_kalau_kosong(self,method):
	if not self.pos_transactions:
		# coba ambil lagi 
		hasil = get_pos_invoices(self.period_start_date, self.period_end_date, self.pos_profile, self.user)

		for row in hasil:
			# insert new row in pos.transaction
			baris_baru = self.append("pos_transactions")
			baris_baru.pos_invoice = row.name
			baris_baru.posting_date = row.posting_date
			baris_baru.grand_total = row.grand_total
			baris_baru.customer = row.customer

@frappe.whitelist()
def ambil_return_usage(self,method):

	self.custom_pos_closing_retur_usage = []
	grouped_data = {}

	if self.pos_transactions:
		for row in self.pos_transactions:
			pos_invoice = frappe.get_doc("POS Invoice", row.pos_invoice)
			for row in pos_invoice.custom_pos_return_usage:
				invoice_return = row.pos_invoice_return
				
				if invoice_return not in grouped_data:
					grouped_data[invoice_return] = {
						'total_amount': 0
					}
				
				grouped_data[invoice_return]['total_amount'] += row.amount or 0
	
	for invoice_return, data in grouped_data.items():
		try:
			pos_invoice = frappe.get_doc("POS Invoice", invoice_return)
			grand_total = pos_invoice.grand_total * -1 or 0
			amount_used = data['total_amount']
			amount_left = grand_total - amount_used
			
			print(invoice_return)
			self.append('custom_pos_closing_retur_usage', {
				'retur_pos_invoice': invoice_return,
				'amount_used': amount_used,
				'amount_left': amount_left
			})

			
		except Exception as e:
			frappe.log_error(
				message=f"Error processing POS Invoice {invoice_return}: {str(e)}",
				title="POS Closing Return Usage Error"
			)

@frappe.whitelist()
def debug():
	doc = frappe.get_doc("POS Closing Entry", "POS-CLO-2026-00010")
	ambil_return_usage(doc,"validate")

@frappe.whitelist()
def get_pos_invoices(start, end, pos_profile, user):
	data = frappe.db.sql(
		"""
	select
		name, timestamp(posting_date, posting_time) as "timestamp"
	from
		`tabPOS Invoice`
	where
		owner = %s and docstatus = 1 and pos_profile = %s and ifnull(consolidated_invoice,'') = ''
	""",
		(user, pos_profile),
		as_dict=1,
	)

	data = list(filter(lambda d: get_datetime(start) <= get_datetime(d.timestamp) <= get_datetime(end), data))
	# need to get taxes and payments so can't avoid get_doc

	data = [frappe.get_doc("POS Invoice", d.name).as_dict() for d in data]

	return data


def patch_pos_closing_totals():
    
    docs = frappe.get_all(
        "POS Closing Entry",   
        filters={"docstatus": 1},
        pluck="name"
    )

    for name in docs:
        try:
            doc = frappe.get_doc("POS Closing Entry", name)

            data = get_tutup_kasir(doc)
            if not data:
                continue

            frappe.db.set_value("POS Closing Entry", name, {
                "custom_kas_awal": data[0],
                "custom_online_partai": data[1],
                "custom_online": data[2],
                "custom_total_online": data[3],
                "custom_jual_cash": data[4],
                "custom_jual_card": data[5],
                "custom_voucher": data[6],
                "custom_jumlah_jual": data[7],
                "custom_retur_cash": data[8],
                "custom_retur_card": data[9],
                "custom_discount_item": data[10],
                "custom_discount_nota": data[11],
                "custom_total_jual": data[12],
                "custom_kas_akhir": data[13],
                "custom_member_free": data[17],
                "custom_member_non_free": data[18],
                "custom_biaya_member": data[19],
                "custom_total_kas_akhir": data[20],
                "custom_pinjaman": data[21],
                "custom_total": data[22],
                "custom_uang_charge_kredit": data[23],
                "custom_total_tutup": data[24],
            })

        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Patch POS Closing {name}")

    frappe.db.commit()


def force_start_date_midnight(doc, method):
    if not doc.period_start_date:
        return

    date_only = getdate(doc.period_start_date)
    doc.period_start_date = get_datetime(f"{date_only} 00:00:00")
