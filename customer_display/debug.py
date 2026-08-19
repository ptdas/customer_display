import frappe

@frappe.whitelist()
def check_return_accounts(return_invoice="RBJM26H040001"):
    ret = frappe.get_doc("POS Invoice", return_invoice)
    orig = frappe.get_doc("POS Invoice", ret.return_against)

    print("=== RETURN ===")
    print(ret.name)
    print(ret.debit_to)

    print()
    print("=== ORIGINAL ===")
    print(orig.name)
    print(orig.debit_to)

    return {
        "return_debit_to": ret.debit_to,
        "original_debit_to": orig.debit_to
    }


@frappe.whitelist()
def test_pos_return_real_submit(pos_invoice="RBJM26H040001"):
    original = frappe.get_doc("POS Invoice", pos_invoice)

    print("=== ORIGINAL ===")
    print("Name:", original.name)
    print("Company:", original.company)
    print("Is Return:", original.is_return)
    print("Return Against:", original.return_against)
    print()

    try:
        # copy dokumen supaya tidak mengubah dokumen asli
        doc = frappe.copy_doc(original)
        doc.name = None
        doc.docstatus = 0

        print("=== INSERT TEST DOC ===")
        doc.insert(ignore_permissions=True)
        print("Inserted:", doc.name)

        print()
        print("=== SUBMIT TEST DOC ===")

        doc.submit()

        print("SUBMIT SUCCESS")

        # rollback supaya tidak tersimpan
        frappe.db.rollback()

        return "SUBMIT SUCCESS"

    except Exception:
        print()
        print("=== REAL ERROR ===")
        print(frappe.get_traceback())

        frappe.db.rollback()

        return "SUBMIT FAILED"

@frappe.whitelist()
def test_pos_return_coa(pos_invoice="RBJM26H040001"):
    doc = frappe.get_doc("POS Invoice", pos_invoice)

    print("=== POS INVOICE DEBUG ===")
    print("Name       :", doc.name)
    print("Company    :", doc.company)
    print("Is Return  :", doc.is_return)
    print("Return Agst:", doc.return_against)
    print()

    print("=== ITEMS ===")
    for row in doc.items:
        acc_company = None

        if row.income_account:
            acc_company = frappe.db.get_value(
                "Account",
                row.income_account,
                "company"
            )

        status = "OK" if acc_company == doc.company else "MISMATCH"

        print(
            f"ITEM={row.item_code} | ACCOUNT={row.income_account} | "
            f"ACC_COMPANY={acc_company} | STATUS={status}"
        )

    print()
    print("=== TAXES ===")
    for row in doc.taxes:
        acc_company = None

        if row.account_head:
            acc_company = frappe.db.get_value(
                "Account",
                row.account_head,
                "company"
            )

        status = "OK" if acc_company == doc.company else "MISMATCH"

        print(
            f"TAX={row.description} | ACCOUNT={row.account_head} | "
            f"ACC_COMPANY={acc_company} | STATUS={status}"
        )

    print()
    print("=== POS PROFILE ===")
    if doc.pos_profile:
        profile_company = frappe.db.get_value(
            "POS Profile",
            doc.pos_profile,
            "company"
        )

        status = "OK" if profile_company == doc.company else "MISMATCH"

        print(
            f"POS_PROFILE={doc.pos_profile} | PROFILE_COMPANY={profile_company} | STATUS={status}"
        )

    print()
    print("=== COST CENTER ===")
    if doc.cost_center:
        cc_company = frappe.db.get_value(
            "Cost Center",
            doc.cost_center,
            "company"
        )

        status = "OK" if cc_company == doc.company else "MISMATCH"

        print(
            f"COST_CENTER={doc.cost_center} | CC_COMPANY={cc_company} | STATUS={status}"
        )

    print()
    print("=== VALIDATE GL ===")

    try:
        gl_entries = doc.get_gl_entries()

        for gle in gl_entries:
            acc_company = frappe.db.get_value(
                "Account",
                gle.account,
                "company"
            )

            status = "OK" if acc_company == doc.company else "MISMATCH"

            print(
                f"GL ACCOUNT={gle.account} | DR={gle.debit} | CR={gle.credit} | "
                f"ACC_COMPANY={acc_company} | STATUS={status}"
            )

    except Exception as e:
        print("GL ERROR:", frappe.get_traceback())

    return "Done"

def test_pos_submit():
    pos = frappe.get_doc("POS Invoice", "BJB26H040004")

    print("docstatus:", pos.docstatus)

    try:
        pos.submit()
        print("SUBMIT OK")
    except Exception:
        print(frappe.get_traceback())

@frappe.whitelist()
def repair_gl_entry():	
	doctype = "Sales Invoice"
	docname = "ACC-SINV-2025-00063-1"

	docu = frappe.get_doc(doctype, docname)	
	delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
	docu.make_gl_entries()


@frappe.whitelist()
def create_tutup_kasir():
	from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import make_closing_entry_from_opening
	closing_entry = make_closing_entry_from_opening(frappe.get_doc("POS Opening Entry","POS-OPE-2025-00009"))
	closing_entry.save()
	
def start_import():
	doc = frappe.get_doc("Data Import","Stock Entry Import on 2026-01-01 22:40:58.797076")
	doc.start_import()

def start_import2():
	doc = frappe.get_doc("Data Import","Item Price Import on 2026-01-01 05:23:08.379058")
	doc.start_import()
def rename_customer():
	data = frappe.db.sql("select name , custom_kode from `tabCustomer` where name != custom_kode", as_list=1)
	count=0
	for row in data:
		frappe.rename_doc("Customer",row[0],row[1])
		frappe.db.commit()
		count=count+1
		print(count)

def debug():
	doc = frappe.get_doc("Company","BJB4")
	doc.create_default_accounts()