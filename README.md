# CBR Putusan Kejahatan Terhadap Ketertiban Umum

Sistem **Case-Based Reasoning (CBR)** untuk analisis putusan **Pidana Kejahatan Terhadap Ketertiban Umum**  
menggunakan data dari Direktori Putusan Mahkamah Agung Republik Indonesia.   

**Nama Anggota Kelompok 1:** Revaldo Ramadana (202310370311202)  
**Nama Anggota Kelompok 2:** Wirsan Wijoyo (202310370311193) 
**Mata Kuliah:** Penalaran Komputer – SubCPMK-3  
**Universitas Muhammadiyah Malang – Fakultas Teknik Informatika**

---

## Struktur Repository

```
cbr-ketertiban-umum/          ← ROOT PROJECT (buka terminal di sini)
│
├── data/
│   ├── raw/                  ← Taruh PDF putusan di sini, lalu jalankan script Tahap 1
│   │   ├── case_001.pdf      ← PDF asli putusan (kamu yang menyiapkan, min. 30 file)
│   │   ├── case_002.pdf
│   │   ├── ...
│   │   ├── case_001.txt      ← Hasil Tahap 1 (otomatis dibuat oleh script)
│   │   ├── case_002.txt
│   │   ├── ...
│   │   └── metadata_raw.json ← Hasil Tahap 1 (otomatis dibuat oleh script)
│   │
│   ├── processed/            ← Hasil Tahap 2 & 3 (otomatis dibuat)
│   │   ├── cases.csv         ← Metadata terstruktur (bisa dibuka di Excel)
│   │   ├── cases.json        ← Data lengkap untuk model
│   │   └── models.pkl        ← Model TF-IDF + SVM + NB tersimpan
│   │
│   ├── eval/                 ← Hasil Tahap 5 (otomatis dibuat)
│   │   ├── queries.json
│   │   ├── split_info.json
│   │   ├── retrieval_metrics.csv
│   │   ├── prediction_metrics.csv
│   │   └── error_analysis.csv
│   │
│   └── results/              ← Hasil Tahap 4 (otomatis dibuat)
│       └── predictions_demo.csv
│
├── figures/                  ← Grafik & visualisasi (otomatis dibuat)
│   ├── data_exploration.png
│   ├── metrics_comparison.png
│   └── confusion_matrix.png
│
├── notebooks/
│   └── CBR_Ketertiban_Umum.ipynb  ← NOTEBOOK UTAMA (Tahap 3, 4, 5)
│
├── scripts/
│   ├── 01_proses_pdf.py      ← Tahap 1: Ekstrak PDF → .txt
│   └── 02_representasi.py    ← Tahap 2: Ekstrak metadata → cases.json
│
├── requirements.txt
└── README.md
```

---

## Cara Menjalankan (Langkah-langkah)

### Langkah 0 – Install Dependencies

Buka terminal, pastikan Python sudah terinstall, lalu:

```bash
pip install -r requirements.txt
```

---

### Langkah 1 – Siapkan Data PDF

Taruh semua file PDF putusan ke dalam folder `data/raw/`:

```
cbr-ketertiban-umum/
└── data/
    └── raw/
        ├── putusan_001.pdf
        ├── putusan_002.pdf
        └── ... (minimal 30 file PDF)
```

> PDF bisa diunduh dari https://putusan3.mahkamahagung.go.id  
> Cari: "ketertiban umum" → filter Pidana

---

### Langkah 2 – Jalankan Tahap 1 (Ekstrak PDF)

Buka terminal **di folder `cbr-ketertiban-umum/`** (ROOT PROJECT), lalu:

```bash
python scripts/01_proses_pdf.py
```

**Output yang dihasilkan di `data/raw/`:**
- `case_001.txt`, `case_002.txt`, dst. — teks bersih tiap putusan
- `metadata_raw.json` — metadata dasar semua kasus

---

### Langkah 3 – Jalankan Tahap 2 (Ekstrak Metadata)

Masih di terminal yang sama:

```bash
python scripts/02_representasi.py
```

**Output yang dihasilkan di `data/processed/`:**
- `cases.csv` — bisa dibuka di Excel untuk cek
- `cases.json` — data lengkap untuk model (wajib ada sebelum buka notebook)

---

### Langkah 4 – Jalankan Notebook (Tahap 3, 4, 5)

```bash
jupyter notebook
```

Browser otomatis terbuka → klik `notebooks/CBR_Ketertiban_Umum.ipynb`

Jalankan semua cell: **Kernel → Restart & Run All**

> ⚠️ Notebook membaca data dari `../data/` (naik 1 level dari folder `notebooks/`).  
> Jangan pindahkan atau rename folder, biarkan strukturnya seperti di atas.

---

## Ringkasan Tahapan CBR

| Tahap | Nama | Cara Jalankan | Output |
|-------|------|---------------|--------|
| 1 | Membangun Case Base | `python scripts/01_proses_pdf.py` | `data/raw/*.txt` |
| 2 | Case Representation | `python scripts/02_representasi.py` | `data/processed/cases.json` |
| 3 | Case Retrieval | Notebook (cell Tahap 3) | Model TF-IDF+SVM & NB |
| 4 | Case Solution Reuse | Notebook (cell Tahap 4) | `data/results/predictions_demo.csv` |
| 5 | Model Evaluation | Notebook (cell Tahap 5) | Metrik, Grafik, Error Analysis |

---

## Hasil Evaluasi Model

| Model | Accuracy | Precision | Recall | F1-Score | Top-5 Retrieval |
|-------|----------|-----------|--------|----------|-----------------|
| TF-IDF + SVM | 0.7500 | 0.5625 | 0.7500 | 0.6429 | 1.0000 |
| TF-IDF + Naive Bayes | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

> **Catatan:** Hasil NB = 1.0 karena test set kecil (4 kasus dari 19 berlabel).  
> Nilai akan lebih representatif dengan data lebih banyak (disarankan 50+ dokumen).

---

## Dependencies

```
pdfminer.six    # Ekstrak teks dari PDF
pandas          # Pengolahan data tabular
numpy           # Komputasi numerik
scikit-learn    # TF-IDF, SVM, Naive Bayes, Metrics
matplotlib      # Visualisasi grafik
seaborn         # Visualisasi heatmap
tqdm            # Progress bar
jupyter         # Menjalankan notebook
```

Install semua sekaligus:
```bash
pip install -r requirements.txt
```
