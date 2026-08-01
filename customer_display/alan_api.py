import frappe
import requests
import json

def debug():
	execute_to_alan_server(frappe.get_doc("Customer","test"),"after_insert")


@frappe.whitelist()
def execute_to_alan_server(doc, method):

	if frappe.local.site != "erp_alan.digitalasiasolusindo.com":
		return

	try:
		# Target server details
		target_url = "https://alan.digitalasiasolusindo.com"
		api_endpoint = f"{target_url}/api/method/alan.api.create_customer_from_api"
		
		# API credentials for alan server
		api_key = "caf9a53009f700b"
		api_secret = "ea9b2ac94f65097"
		
		# Prepare customer data
		customer_data = {
			"kode": doc.custom_customer_kode,
			"nama": doc.customer_name,
			"alamat_1": doc.custom_alamat_1,
			"kota": doc.custom_kota,
			"telpon": doc.custom_telpon,
			"handphone": doc.custom_handphone,
			"no_whatsapp": doc.custom_no_whatsapp,
			"tanggal_lahir": doc.custom_tanggal_lahir,
			"email": doc.custom_email,
			"jenis_id": doc.custom_jenis_id,
			"no_id":doc.custom_no_id
		}
		
		# Send API request
		headers = {
			"Authorization": f"token {api_key}:{api_secret}",
			"Content-Type": "application/json"
		}
		
		response = requests.post(
			api_endpoint,
			headers=headers,
			data=json.dumps({"customer_data": customer_data}),
			timeout=30
		)
		
		if response.status_code == 200:
			result = response.json()
			frappe.msgprint(f"Customer synced to alan server: {result.get('message')}")
		else:
			frappe.log_error(
				f"Status: {response.status_code}\nResponse: {response.text}",
				"Customer Sync Failed"
			)
			
	except Exception as e:
		print("GAGAL")
		frappe.log_error(frappe.get_traceback(), "Customer API Sync Error")

def debug_lp():
	sync_loyalty_point_entry_to_poin_customer(frappe.get_doc("Loyalty Point Entry","l3uqivblce"),"after_insert")

@frappe.whitelist()
def sync_loyalty_point_entry_to_poin_customer(doc, method):
	# Only execute for specific site
	if frappe.local.site != "erp_alan.digitalasiasolusindo.com":
		return
	
	try:
		# Target server details
		target_url = "https://alan.digitalasiasolusindo.com"
		api_endpoint = f"{target_url}/api/method/alan.api.create_poin_customer_from_api"
		
		# API credentials for alan server
		api_key = "caf9a53009f700b"
		api_secret = "ea9b2ac94f65097"
		
		# Determine tipe based on loyalty_points
		tipe = "Acquired" if doc.loyalty_points > 0 else "Redeemed"
		
		# Get customer name
		customer_doc = frappe.get_doc("Customer", doc.customer)
		customer_name = customer_doc.customer_name
		kode = customer_doc.custom_customer_kode
		
		# Get nilai_konversi
		loyalty_program_doc = frappe.get_doc("Loyalty Program", doc.loyalty_program)
		nilai_konversi = 0
		
		if doc.loyalty_points > 0:
			for rule in loyalty_program_doc.collection_rules:
				if rule.tier_name == doc.loyalty_program_tier:
					nilai_konversi = rule.collection_factor
					break
		else:
			nilai_konversi = loyalty_program_doc.conversion_factor
		
		company_doc = frappe.get_doc("Company", doc.company)
		toko = company_doc.parent_company or doc.company
		
		# Prepare poin customer data
		poin_customer_data = {
			"invoice": doc.invoice, 
			"tipe": tipe,
			"customer": kode,
			"customer_name": customer_name,
			"deskripsi": "Loyalty Program from ERP",
			"tanggal_posting": str(doc.posting_date) if doc.posting_date else None,
			"nilai_konversi": nilai_konversi,
			"nominal_transaksi": doc.purchase_amount,
			"poin": doc.loyalty_points,
			"toko": toko,
			"no_lpe_erp": doc.name
		}
		print(poin_customer_data)
		# Send API request
		headers = {
			"Authorization": f"token {api_key}:{api_secret}",
			"Content-Type": "application/json"
		}
		
		response = requests.post(
			api_endpoint,
			headers=headers,
			data=json.dumps({"poin_customer_data": poin_customer_data}),
			timeout=30
		)
		
		if response.status_code == 200:
			result = response.json()
			frappe.msgprint(f"Loyalty Point Entry synced to Alan server: {result.get('message')}")
		else:
			frappe.log_error(
				f"Status: {response.status_code}\nResponse: {response.text}",
				"Loyalty Point Entry Sync Failed"
			)
			
	except Exception as e:
		print("GAGAL")
		frappe.log_error(frappe.get_traceback(), "Loyalty Point Entry API Sync Error")