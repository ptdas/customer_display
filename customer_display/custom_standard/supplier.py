import frappe


def set_vendor_company(doc, method=None):
    """
    Set custom_vendor_company dan custom_vendor_company_bjm
    berdasarkan custom_pkp_type pada Supplier.
    """

    if not doc.custom_pkp_type:
        return

    settings = frappe.get_single("AXTRA Settings")

    if doc.custom_pkp_type == "PKP":
        doc.custom_vendor_company = settings.default_target_pkp_company
        doc.custom_vendor_company_bjm = settings.default_target_pkp_company_bjm

    elif doc.custom_pkp_type == "Non":
        doc.custom_vendor_company = settings.default_target_pitza_company
        doc.custom_vendor_company_bjm = settings.default_target_pitza_company_bjm