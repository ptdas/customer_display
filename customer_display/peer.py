"""Sambungan ke site seberang: bjb_alan <-> bjm_alan.

Sesudah `erp_alan` dipecah, BJB dan BJM tinggal di dua site terpisah. Semua
yang perlu bicara ke seberang lewat sini - satu tempat yang tahu URL, kunci
API, dan grup mana yang dipegang site ini. Ini sekaligus mengganti hardcode
("BJB", "BJM") yang dulu bertebaran di kode.

`site_config.json` tiap site (contoh untuk site BJB):

    "alan_grup": "BJB",
    "alan_peer": {
        "grup": "BJM",
        "url": "http://127.0.0.1",
        "host_header": "bjm_alan.digitalasiasolusindo.com",
        "api_key": "...",
        "api_secret": "..."
    }

Kredensialnya sengaja di site_config, bukan di doctype: nilainya beda per
site, tidak ikut masuk git, dan tidak terlihat dari UI.

Dua kunci tambahan yang boleh diisi:

`host_header` - hostname yang dikirim sebagai header `Host`, terpisah dari
alamat yang benar-benar dihubungi. Ini yang dipakai kalau kedua site duduk di
mesin yang sama: `url` menunjuk loopback, `host_header` menyebut site tujuan,
dan nginx memilih site dari header itu (ia meneruskannya ke frappe sebagai
`X-Frappe-Site-Name`). Lalu lintasnya tidak pernah meninggalkan mesin, jadi
tidak ada DNS publik, sertifikat, atau perjalanan keluar-masuk internet yang
perlu benar hanya supaya dua site bertetangga bisa bicara.

`verify: false` - lewati pemeriksaan sertifikat TLS. Hanya masuk akal kalau
memang harus lewat HTTPS dan sertifikatnya belum benar; kunci API tetap
terkirim lewat jaringan, jadi tiap panggilan meninggalkan peringatan di log
supaya tidak ditinggal menyala.

Catatan kalau nanti hostname site dipakai langsung lewat HTTPS: nama seperti
`bjm_alan.digitalasiasolusindo.com` **tidak** dicakup sertifikat wildcard
`*.digitalasiasolusindo.com`. Wildcard tidak boleh mencocoki label yang
mengandung garis bawah, karena itu bukan karakter sah untuk hostname DNS.
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

    # Alamat yang dihubungi dan site yang dituju tidak harus sama - lihat
    # `host_header` di keterangan modul.
    if peer.get("host_header"):
        headers["Host"] = peer["host_header"]

    verify = peer.get("verify", True)
    if not verify:
        frappe.logger("peer").warning(
            "Pemeriksaan sertifikat TLS ke site %s dimatikan lewat alan_peer.verify",
            peer["grup"],
        )

    try:
        jawaban = requests.post(
            url,
            headers=headers,
            data=json.dumps(payload),
            timeout=TIMEOUT,
            verify=verify,
        )
    except requests.exceptions.SSLError as e:
        # Dipisah karena sebabnya beda sama sekali dari jaringan putus, dan
        # obatnya ada di nginx/sertifikat - bukan sesuatu yang membaik sendiri
        # kalau ditunggu atau diulang.
        raise PeerTidakTerjangkau(
            _(
                "Sertifikat TLS site {0} tidak sah untuk hostname-nya, jadi "
                "sambungan ditolak sebelum sempat masuk. Perbaiki sertifikat "
                "site itu (nginx belum tentu punya server block untuk hostname "
                "baru). Rincian: {1}"
            ).format(peer["grup"], e)
        ) from e
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
