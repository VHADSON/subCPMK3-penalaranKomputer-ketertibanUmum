"""
02_representation_lokal.py
Jalankan di komputermu di folder SubCPMK_3_Genap/
Baca semua case_*.txt dari data/raw/ → hasilkan cases.csv & cases.json
"""
import re, json
import pandas as pd
from pathlib import Path

SCRIPT_DIR  = Path(__file__).resolve().parent
RAW_DIR     = SCRIPT_DIR / "data" / "raw"
OUT_DIR     = SCRIPT_DIR / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BULAN_MAP = {
    "januari":"01","februari":"02","maret":"03","april":"04",
    "mei":"05","juni":"06","juli":"07","agustus":"08",
    "september":"09","oktober":"10","november":"11","desember":"12"
}

HAPUS_POLA = [
    r"Kepaniteraan berusaha untuk selalu mencantumkan.*?(?=\n\n|\Z)",
    r"Email\s*:.*?mahkamahagung\.go\.id[^\n]*",
    r"Telp\s*:[^\n]*",
    r"Halaman\s+\d+",
    r"putusan\.mahkamahagung\.go\.id",
    r"Putusan Nomor[\w\s./]+(?=\n|\f)",
]

def bersihkan(teks):
    for p in HAPUS_POLA:
        teks = re.sub(p, "", teks, flags=re.DOTALL|re.IGNORECASE)
    teks = re.sub(r"\n{3,}", "\n\n", teks)
    teks = re.sub(r"[ \t]{2,}", " ", teks)
    return teks.strip()

def get_no_perkara(teks, fallback=""):
    m = re.search(r"Nomor\s+([\d]+/[\w.]+/[\d]+/[\w\s.]+?)(?:\n|DEMI)", teks, re.IGNORECASE)
    if m: return m.group(1).strip()
    m = re.search(r"\b(\d+/(?:Pid\.B|Pid|PID|Pdt\.G)[\w./\s-]+\d{4}[\w./\s-]*)\b", teks, re.IGNORECASE)
    return m.group(1).strip() if m else fallback

def get_tanggal(teks):
    for pola in [
        r"(?:diputus(?:kan)?|pada\s+hari\s+\w+\s+tanggal)\s*(?:hari\s+\w+\s+)?(?:tanggal\s+)?(\d{1,2})\s+(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)\s+(\d{4})",
        r"tanggal\s+(\d{1,2})\s+(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)\s+(\d{4})",
    ]:
        m = re.search(pola, teks, re.IGNORECASE)
        if m:
            bln = BULAN_MAP.get(m.group(2).lower(), "00")
            return f"{m.group(3)}-{bln}-{int(m.group(1)):02d}"
    return ""

def get_terdakwa(teks):
    m = re.search(r"Nama\s+(?:lengkap|Lengkap)\s*:\s*([A-Z][A-Za-z\s.,''()\-/]+?)(?:;|\n|NIK)", teks)
    if m:
        nama = re.sub(r"\s+", " ", m.group(1)).strip().rstrip(";,")
        if len(nama) < 60 and not any(x in nama.lower() for x in ["advokat","penasihat","pengadilan","jaksa"]):
            return nama
    return ""

def get_vonis(teks):
    bagian = teks
    m_adili = re.search(r"MENGADILI(.*?)(?=\n\nDemikian|\n\nDitetapkan|\Z)", teks, re.DOTALL|re.IGNORECASE)
    if m_adili: bagian = m_adili.group(1)
    m = re.search(r"pidana\s+penjara\s+selama\s+([\d]+)\s*\([^)]+\)\s*(bulan|tahun)", bagian, re.IGNORECASE)
    if m: return f"{m.group(1)} {m.group(2)}"
    m = re.search(r"pidana\s+penjara\s+selama\s+([\d\s\w]+(?:bulan|tahun))", bagian, re.IGNORECASE)
    if m: return m.group(1).strip()
    if re.search(r"membebaskan\s+terdakwa|tidak\s+terbukti", bagian, re.IGNORECASE):
        return "bebas"
    return ""

def get_amar(teks):
    m = re.search(r"MENGADILI(.*?)(?=\n\nDemikian|\n\nDitetapkan|\Z)", teks, re.DOTALL|re.IGNORECASE)
    if m:
        amar = re.sub(r"\s+", " ", m.group(1)).strip()
        return amar[:600] + ("..." if len(amar) > 600 else "")
    return ""

def get_dakwaan(teks):
    m = re.search(r"(?:DAKWAAN|surat\s+dakwaan)[:\s]*(.*?)(?=Menimbang|\Z)", teks, re.DOTALL|re.IGNORECASE)
    if m:
        d = re.sub(r"\s+", " ", m.group(1)).strip()
        return d[:500] + ("..." if len(d) > 500 else "")
    return ""

def get_ringkasan(teks):
    m = re.search(r"Bahwa\s+(?:Para\s+)?[Tt]erdakwa\s+(?:diajukan|didakwa)(.*?)(?=Menimbang,\s+bahwa\s+untuk\s+membuktikan|\Z)", teks, re.DOTALL)
    if m:
        txt = re.sub(r"\s+", " ", m.group(0)).strip()
        return txt[:500] + ("..." if len(txt) > 500 else "")
    return teks[:400].replace("\n", " ").strip()

def get_label(vonis, amar):
    v, a = vonis.lower(), amar.lower()
    if "bebas" in v or "membebaskan" in a or "tidak terbukti" in a: return "bebas"
    if "lepas" in a: return "lepas"
    m = re.search(r"(\d+)\s*(tahun|bulan)", v)
    if m:
        n, satuan = int(m.group(1)), m.group(2)
        total_bln = n*12 if satuan=="tahun" else n
        return "bersalah_berat" if total_bln > 24 else "bersalah_ringan"
    if "terbukti" in a or "bersalah" in a: return "bersalah_ringan"
    return "tidak_diketahui"

def get_pasal(teks):
    pasals = re.findall(r"[Pp]asal\s+[\d]+(?:\s+[Aa]yat\s*\([\d]+\))?", teks)
    unik = list(dict.fromkeys(pasals))[:4]
    return "; ".join(unik)

# ── Load metadata ───────────────────────────────────────────────────────────
with open(RAW_DIR / "metadata_raw.json", encoding="utf-8") as f:
    metadata = json.load(f)

records = []
for meta in metadata:
    case_id  = meta["case_id"]
    txt_path = RAW_DIR / f"{case_id}.txt"

    if not txt_path.exists():
        print(f"[SKIP] {case_id} - file tidak ditemukan")
        continue

    teks       = txt_path.read_text(encoding="utf-8", errors="ignore")
    teks_brsih = bersihkan(teks)

    no_perkara = get_no_perkara(teks_brsih, meta.get("no_perkara",""))
    tanggal    = get_tanggal(teks_brsih) or meta.get("tanggal","")
    terdakwa   = get_terdakwa(teks_brsih) or meta.get("terdakwa","")
    vonis      = get_vonis(teks_brsih)
    amar       = get_amar(teks_brsih)
    dakwaan    = get_dakwaan(teks_brsih)
    ringkasan  = get_ringkasan(teks_brsih)
    label      = get_label(vonis, amar)
    pasal      = get_pasal(teks_brsih) or meta.get("pasal","")
    pengadilan = meta.get("pengadilan","")

    records.append({
        "case_id"        : case_id,
        "no_perkara"     : no_perkara,
        "tanggal"        : tanggal,
        "jenis_perkara"  : "Pidana - Kejahatan Terhadap Ketertiban Umum",
        "pengadilan"     : pengadilan,
        "terdakwa"       : terdakwa,
        "pasal"          : pasal,
        "dakwaan"        : dakwaan,
        "amar_putusan"   : amar,
        "vonis"          : vonis,
        "label"          : label,
        "ringkasan_fakta": ringkasan,
        "word_count"     : meta.get("word_count",0),
        "file_asli"      : meta.get("file_asli",""),
        "text_full"      : teks_brsih,
    })
    print(f"[OK] {case_id} | {no_perkara} | vonis: {vonis or '-'} | label: {label}")

df = pd.DataFrame(records)
print(f"\n=== SELESAI: {len(df)} kasus ===")
print(f"Label:\n{df['label'].value_counts()}")
print(f"Vonis terisi: {(df['vonis']!='').sum()}/{len(df)}")

# Simpan
df_csv = df.drop(columns=["text_full"])
df_csv.to_csv(OUT_DIR / "cases.csv", index=False, encoding="utf-8-sig")
df.to_json(OUT_DIR / "cases.json", orient="records", force_ascii=False, indent=2)
print(f"\n✓ Tersimpan di {OUT_DIR}")
