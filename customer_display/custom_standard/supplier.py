import frappe

from customer_display.vendor_company import set_vendor_companies


def set_vendor_company(doc, method=None):
    """Set company vendor pada Supplier berdasarkan custom_pkp_type.

    Di site gabungan sepasang field diisi (sisi BJB dan sisi BJM). Di site
    hasil pecah cuma `custom_vendor_company` yang ada, dan yang masuk ke situ
    adalah setelan berlabel polos - split_company.py sudah memindahkan sisi
    yang bertahan ke sana.
    """

    if not doc.custom_pkp_type:
        return

    settings = frappe.get_single("AXTRA Settings")

    if doc.custom_pkp_type == "PKP":
        set_vendor_companies(
            doc,
            settings.default_target_pkp_company,
            settings.default_target_pkp_company_bjm,
        )

    elif doc.custom_pkp_type == "Non":
        set_vendor_companies(
            doc,
            settings.default_target_pitza_company,
            settings.default_target_pitza_company_bjm,
        )
