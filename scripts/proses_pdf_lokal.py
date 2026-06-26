import re
import json
import os
import sys
from pathlib import Path
from tqdm import tqdm

# ── Cek & install dependency otomatis ────────────────────────────────────────
def install(pkg):
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

try:
    from pdfminer.high_level import extract_text
    from pdfminer.pdfparser import PDFSyntaxError
except ImportError:
    print("Menginstall pdfminer.six...")
    install("pdfminer.six")
    from pdfminer.high_level import extract_text
    from pdfminer.pdfparser import PDFSyntaxError

try:
    import pandas as pd
except ImportError:
    print("Menginstall pandas...")
    install("pandas")
    import pandas as pd

# ── Konfigurasi folder ────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).resolve().parent
OUTPUT_DIR  = SCRIPT_DIR / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Pola header/footer MA RI ──────────────────────────────────────────────────
HAPUS_POLA = [
    r"Mahkamah Agung Republik Indonesia",
    r"Direktori Putusan",
    r"Disclaimer[^\n]*",
    r"putusan\.mahkamahagung\.go\.id",
    r"halaman\s+\d+\s+dari\s+\d+",
    r"^\s*-\s*\d+\s*-\s*$",   # - 1 -
    r"^\s*\d+\s*$",            # nomor halaman saja
]

def bersihkan_teks(raw: str) -> str:
    teks = raw
    for pola in HAPUS_POLA:
        teks = re.sub(pola, "", teks, flags=re.IGNORECASE | re.MULTILINE)
    teks = re.sub(r"\n{3,}", "\n\n", teks)   # max 2 baris kosong
    teks = re.sub(r"[ \t]{2,}", " ", teks)   # spasi ganda → 1
    teks = re.sub(r"\r", "", teks)
    return teks.strip()

def ekstrak_pdf(pdf_path: Path) -> str | None:
    try:
        raw = extract_text(str(pdf_path))
        if not raw or len(raw.strip()) < 100:
            return None
        return raw
    except PDFSyntaxError:
        return None
    except Exception:
        return None

def ekstrak_metadata_dasar(teks: str) -> dict:
    """Ekstrak metadata sederhana dari teks putusan."""
    meta = {}

    # Nomor perkara
    m = re.search(r"\b(\d+[\w/.\-]+(?:Pid|Pdt)[\w/.\-]+)\b", teks, re.IGNORECASE)
    meta["no_perkara"] = m.group(1).strip() if m else ""

    # Tanggal
    BULAN = {"januari":"01","februari":"02","maret":"03","april":"04",
              "mei":"05","juni":"06","juli":"07","agustus":"08",
              "september":"09","oktober":"10","november":"11","desember":"12"}
    m = re.search(
        r"tanggal\s+(\d{1,2})\s+(januari|februari|maret|april|mei|juni|"
        r"juli|agustus|september|oktober|november|desember)\s+(\d{4})",
        teks, re.IGNORECASE
    )
    if m:
        bln = BULAN.get(m.group(2).lower(), "00")
        meta["tanggal"] = f"{m.group(3)}-{bln}-{int(m.group(1)):02d}"
    else:
        meta["tanggal"] = ""

    # Pengadilan
    m = re.search(r"PENGADILAN NEGERI\s+([A-Z\s.]+?)(?:\s+Yang|\s+Memeriksa|\n)",
                  teks, re.IGNORECASE)
    meta["pengadilan"] = ("PN " + m.group(1).strip().title()) if m else \
                         ("Mahkamah Agung" if re.search(r"Mahkamah Agung", teks, re.IGNORECASE) else "")

    # Pasal
    pasals = re.findall(r"[Pp]asal\s+[\d\s,dananatau]+", teks)
    meta["pasal"] = "; ".join(list(dict.fromkeys(
        re.sub(r"\s+", " ", p).strip() for p in pasals[:3]
    )))

    # Terdakwa
    m = re.search(r"(?:terdakwa)[:\s]+([A-Z][a-zA-Z\s.,']+?)(?:\s*(?:bin|binti|alias|,|\n))",
                  teks, re.IGNORECASE)
    meta["terdakwa"] = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""

    # Vonis
    m = re.search(r"(?:penjara|pidana penjara)\s+selama\s+([\d\s\w]+tahun[\w\s]*)",
                  teks, re.IGNORECASE)
    meta["vonis"] = m.group(1).strip() if m else ""

    # Amar putusan (ringkas)
    m = re.search(r"(?:M\s*E\s*N\s*G\s*A\s*D\s*I\s*L\s*I|MENGADILI)[:\s]*(.*?)(?=\n\n|\Z)",
                  teks, re.DOTALL | re.IGNORECASE)
    meta["amar_putusan"] = (m.group(1).strip()[:400] + "...") if m else ""

    # Ringkasan fakta
    for pola in [
        r"(?:DUDUK PERKARA|Duduk Perkara)[:\s]*(.*?)(?=PERTIMBANGAN|MENGADILI|\Z)",
        r"(?:Menimbang)[:\s]*(.*?)(?=Mengadili|MENGADILI|\Z)",
    ]:
        m = re.search(pola, teks, re.DOTALL | re.IGNORECASE)
        if m:
            fakta = m.group(1).strip()
            paragraf = [p.strip() for p in fakta.split("\n\n") if len(p.strip()) > 50]
            meta["ringkasan_fakta"] = " ".join(paragraf[:2])[:400]
            break
    else:
        meta["ringkasan_fakta"] = teks[:300].replace("\n", " ").strip()

    # Label otomatis
    amar   = meta["amar_putusan"].lower()
    vonis  = meta["vonis"].lower()
    if "bebas" in amar or "lepas" in amar:
        meta["label"] = "bebas"
    else:
        tahun = re.search(r"(\d+)\s*tahun", vonis)
        if tahun:
            meta["label"] = "bersalah_berat" if int(tahun.group(1)) > 2 else "bersalah_ringan"
        elif "bersalah" in amar or "terbukti" in amar:
            meta["label"] = "bersalah_ringan"
        else:
            meta["label"] = "tidak_diketahui"

    return meta

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Cari PDF di folder yang sama dengan script
    pdf_files = sorted(SCRIPT_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"\n[!] Tidak ada PDF ditemukan di: {SCRIPT_DIR}")
        print("    Pastikan PDF-mu ada di folder yang sama dengan script ini.")
        return

    print(f"\nDitemukan {len(pdf_files)} file PDF")
    print(f"Output akan disimpan di: {OUTPUT_DIR}\n")

    metadata  = []
    berhasil  = 0
    gagal     = 0

    for pdf_path in tqdm(pdf_files, desc="Memproses PDF"):
        # Buat case_id: urutan atau dari nama file
        idx      = len(metadata) + 1
        case_id  = f"case_{idx:03d}"
        txt_path = OUTPUT_DIR / f"{case_id}.txt"

        raw  = ekstrak_pdf(pdf_path)
        if raw:
            bersih    = bersihkan_teks(raw)
            word_cnt  = len(bersih.split())
            status    = "ok" if word_cnt > 300 else "partial"

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(bersih)

            meta_dasar = ekstrak_metadata_dasar(bersih)
            metadata.append({
                "case_id"         : case_id,
                "file_asli"       : pdf_path.name,
                "txt_path"        : str(txt_path),
                "word_count"      : word_cnt,
                "status"          : status,
                "jenis_perkara"   : "Pidana - Kejahatan Terhadap Ketertiban Umum",
                **meta_dasar,
            })
            berhasil += 1
            tqdm.write(f"  ✓ {pdf_path.name} → {word_cnt} kata [{status}]")
        else:
            metadata.append({
                "case_id": case_id, "file_asli": pdf_path.name,
                "txt_path": "", "word_count": 0, "status": "failed",
                "jenis_perkara": "Pidana - Kejahatan Terhadap Ketertiban Umum",
                "no_perkara":"","tanggal":"","pengadilan":"","pasal":"",
                "terdakwa":"","vonis":"","amar_putusan":"","ringkasan_fakta":"",
                "label":"tidak_diketahui",
            })
            gagal += 1
            tqdm.write(f"  ✗ {pdf_path.name} → GAGAL (mungkin PDF scan/gambar)")

    # Simpan metadata_raw.json
    meta_path = OUTPUT_DIR / "metadata_raw.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # Simpan juga cases.csv langsung (untuk kemudahan cek)
    import pandas as pd
    df = pd.DataFrame(metadata)
    df.to_csv(OUTPUT_DIR / "cases_preview.csv", index=False, encoding="utf-8-sig")

    print(f"\n{'='*50}")
    print(f"SELESAI!")
    print(f"  Berhasil : {berhasil} dokumen")
    print(f"  Gagal    : {gagal} dokumen")
    print(f"  Output   : {OUTPUT_DIR}")
    print(f"  Metadata : {meta_path}")

    if gagal > 0:
        gagal_list = [m["file_asli"] for m in metadata if m["status"] == "failed"]
        print(f"\n[!] PDF yang gagal diekstrak (kemungkinan scan/gambar):")
        for f in gagal_list:
            print(f"    - {f}")
        print("    → Coba buka PDF-nya, lalu Ctrl+A → apakah teks bisa diselect?")
        print("      Kalau tidak bisa, PDF tersebut adalah gambar (butuh OCR).")

    if berhasil >= 30:
        print(f"\n✓ {berhasil} dokumen berhasil — memenuhi syarat minimal 30 dokumen!")
        print("  Langkah selanjutnya: jalankan 02_representation.py")
    else:
        print(f"\n[!] Hanya {berhasil} dokumen berhasil — butuh minimal 30.")

if __name__ == "__main__":
    main()
