"""Sambungan ke site seberang: bjb_alan <-> bjm_alan.

Sesudah `erp_alan` dipecah, BJB dan BJM tinggal di dua site terpisah. Semua
yang perlu bicara ke seberang lewat sini - satu tempat yang tahu URL, kunci
API, dan grup mana yang dipegang site ini. Ini sekaligus mengganti hardcode
("BJB", "BJM") yang dulu bertebaran di kode.

`site_config.json` tiap site (contoh untuk site BJB):

    "alan_grup": "BJB",
    "alan_peer": {
        "grup": "BJM",
        "url": "https://bjm_alan.digitalasiasolusindo.com",
        "api_key": "...",
        "api_secret": "..."
    }

Kredensialnya sengaja di site_config, bukan di doctype: nilainya beda per
site, tidak ikut masuk git, dan tidak terlihat dari UI.
"""

import json

import frappe
import requests
from frappe import _

TIMEOUT = 30


class PeerError(frappe.ValidationError):
    """Induk semua kegagalan bicara dengan site seberang."""


class PeerTidakTerjangkau(PeerError):
    """Jaringan, DNS, atau timeout. Layak diulang otomatis."""


class PeerMenolak(PeerError):
    """Seberang menjawab dengan error. Mengulang tanpa perbaikan percuma."""


def grup_lokal():
    """Grup yang dipegang site ini: 'BJB' atau 'BJM'."""
    grup = frappe.conf.get("alan_grup")
    if not grup:
        frappe.throw(
            _("`alan_grup` belum diisi di site_config.json site ini."),
            exc=PeerError,
        )
    return grup


def setelan_peer():
    peer = frappe.conf.get("alan_peer") or {}
    kurang = [k for k in ("grup", "url", "api_key", "api_secret") if not peer.get(k)]
    if kurang:
        frappe.throw(
            _("`alan_peer` di site_config.json belum lengkap, kurang: {0}").format(
                ", ".join(kurang)
            ),
            exc=PeerError,
        )
    return peer


def grup_peer():
    return setelan_peer()["grup"]


def site_lokal():
    return frappe.local.site


def panggil(metode, **payload):
    """Panggil satu metode whitelist di site seberang.

    Balikkan isi `message` dari jawaban. Melempar PeerTidakTerjangkau kalau
    seberang tidak terhubung (boleh diulang), PeerMenolak kalau seberang
    menjawab dengan error (jangan diulang buta - ada yang salah di isinya).
    """
    peer = setelan_peer()
    url = "{0}/api/method/{1}".format(peer["url"].rstrip("/"), metode)
    headers = {
        "Authorization": "token {0}:{1}".format(peer["api_key"], peer["api_secret"]),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        jawaban = requests.post(
            url, headers=headers, data=json.dumps(payload), timeout=TIMEOUT
        )
    except requests.RequestException as e:
        raise PeerTidakTerjangkau(
            _("Site {0} tidak bisa dihubungi: {1}").format(peer["grup"], e)
        ) from e

    if jawaban.status_code >= 400:
        raise PeerMenolak(
            _("Site {0} menolak {1}: {2}").format(
                peer["grup"], metode, _pesan_error(jawaban)
            )
        )

    try:
        return (jawaban.json() or {}).get("message")
    except ValueError as e:
        # Balasan bukan JSON - biasanya halaman login HTML karena kunci API
        # salah, atau proxy yang menyela.
        raise PeerMenolak(
            _("Jawaban site {0} tidak bisa dibaca (HTTP {1}).").format(
                peer["grup"], jawaban.status_code
            )
        ) from e


def _pesan_error(jawaban):
    """Gali pesan yang berguna dari balasan error frappe."""
    try:
        isi = jawaban.json() or {}
    except ValueError:
        return "HTTP {0}".format(jawaban.status_code)

    pesan = isi.get("_server_messages")
    if pesan:
        try:
            baris = [json.loads(p) for p in json.loads(pesan)]
            return " | ".join(
                (b.get("message") if isinstance(b, dict) else str(b)) for b in baris
            )
        except (ValueError, TypeError):
            return str(pesan)

    return isi.get("exception") or isi.get("message") or "HTTP {0}".format(
        jawaban.status_code
    )
