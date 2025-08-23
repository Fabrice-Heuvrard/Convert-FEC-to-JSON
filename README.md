# Convert FEC to JSON

> Convert **FEC (Fichier des Écritures Comptables)** files to **structured JSON**—fast, robust, and scalable.

- 🇬🇧 [English](#english)
- 🇫🇷 [Français](#français)

---

## English

### Overview
This project provides a **single Python script** to convert a French **FEC** file (DGFiP, 18 columns) into **structured JSON by accounting entry**.  
It auto-detects **encoding** and **separator**, supports **chunked reading** for large files, and can output either a single JSON array or **JSON Lines** (one entry per line).

### Features
- 🧠 **Auto-detect** input **encoding** (UTF-8, ISO-8859-15, ISO-8859-1)
- 🧩 **Auto-detect** field **separator** (tab, `|`, `;`, `,`)
- 🚀 **Chunked/streaming** processing (handles multi-million-row FEC)
- 🧾 **Two output modes**: JSON array or **JSONL**
- 📅 **Dates normalized** to `YYYY-MM-DD`
- 💶 Amounts exported as **strings** by default (for accounting precision) — optional `--numbers float`
- ✅ Optional **validation**: column presence + **Debit = Credit** check per entry
- 🗜️ **Transparent gzip** output if filename ends with `.gz`
- 🛠️ Clean **CLI** with helpful logs

### Prerequisites
- Python **3.9+**
- Library: **pandas**
```bash
pip install pandas
```

### Quick start
```bash
# JSON array (list of entries)
python fec_to_json.py -i FEC_2023.txt -o FEC_2023.json

# JSON Lines (one entry per line) — recommended for very large files
python fec_to_json.py -i FEC_2023.txt -o FEC_2023.jsonl --jsonl

# With validation (warn) and strict mode (error)
python fec_to_json.py -i FEC.txt -o FEC.json --validate --strict

# Force encoding / separator if needed
python fec_to_json.py -i FEC.txt -o out.json --encoding iso-8859-15 --sep "\t"

# Output compressed
python fec_to_json.py -i FEC.txt -o FEC.json.gz
```

### CLI options
| Option | Default | Description |
|---|---:|---|
| `-i, --input` | — | Path to input FEC file (text) |
| `-o, --output` | — | Path to output JSON/JSONL (`.gz` supported) |
| `--encoding` | `auto` | `auto`, `utf-8`, `iso-8859-15`, `iso-8859-1` |
| `--sep` | `auto` | `auto`, `\t`, `|`, `;`, `,` |
| `--chunksize` | `200000` | Pandas chunk size (rows) |
| `--mode` | `stream` | `stream` (contiguous entries) or `inmem` (safe grouping) |
| `--jsonl` | `False` | Output JSON Lines (one entry per line) |
| `--numbers` | `string` | `string` (default) or `float` for amounts |
| `--validate` | `False` | Enable column & balance checks |
| `--strict` | `False` | Turn validation warnings into errors |

### Output schema (per entry)
```json
{
  "journal": {"code": "ACH", "lib": "Purchases"},
  "ecritureNum": "2023-000123",
  "date": "2023-05-18",
  "libelle": "Invoice X",
  "lignes": [
    {
      "compte": "401000",
      "compteLib": "Vendors",
      "compAuxNum": "",
      "compAuxLib": "",
      "debit": "0.00",
      "credit": "125.33",
      "pieceRef": "FAC-20230518-ACME",
      "pieceDate": "2023-05-18",
      "ecritureLet": "",
      "dateLet": "",
      "validDate": "2023-05-20",
      "montantDevise": "",
      "iDevise": ""
    }
  ],
  "rawKeys": ["JournalCode","JournalLib","EcritureNum","EcritureDate","CompteNum","CompteLib","CompAuxNum","CompAuxLib","PieceRef","PieceDate","EcritureLib","Debit","Credit","EcritureLet","DateLet","ValidDate","Montantdevise","Idevise"]
}
```
> Amounts are **strings** to preserve precision. Use `--numbers float` if you need numeric types.

### Notes & assumptions
- **Streaming mode** (`--mode stream`) assumes lines of the same entry are **contiguous** in the FEC (typical export).  
  If not guaranteed, use `--mode inmem`.
- Validation (`--validate`) checks for **18 required columns** and **Debit = Credit** per entry (`--strict` to fail).

### Performance tips
- Prefer `--jsonl` for downstream processing and very large files.
- Increase `--chunksize` if you have enough RAM; decrease it otherwise.
- Use gzip (`.gz`) to reduce disk I/O and storage footprint.

### Local install (optional venv)
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip pandas
```

### License
GNU **Affero GPL v3.0**. See [LICENSE](./LICENSE).

### Contact
- Twitter: [@FabriceHeuvrard](https://twitter.com/FabriceHeuvrard)  
- LinkedIn: <https://www.linkedin.com/in/fabriceheuvrard/>

---

## Français

### Présentation
Ce projet fournit un **script Python unique** pour convertir un **FEC** (DGFiP, 18 colonnes) en **JSON structuré par écriture**.  
Il détecte automatiquement l’**encodage** et le **séparateur**, lit en **chunks** pour les gros fichiers et peut produire un **JSON** (liste) ou du **JSON Lines** (une écriture par ligne).

### Fonctionnalités
- 🧠 **Auto-détection** de l’**encodage** (UTF-8, ISO-8859-15, ISO-8859-1)
- 🧩 **Auto-détection** du **séparateur** (tabulation, `|`, `;`, `,`)
- 🚀 Traitement **en chunks/streaming** (FEC de plusieurs millions de lignes)
- 🧾 **Deux formats de sortie** : tableau JSON ou **JSONL**
- 📅 **Dates normalisées** en `YYYY-MM-DD`
- 💶 Montants exportés en **chaînes** par défaut (précision comptable) — `--numbers float` possible
- ✅ **Validation** optionnelle : présence des **18 colonnes** + équilibre **Débit = Crédit**
- 🗜️ **Compression gzip** transparente si le fichier termine par `.gz`
- 🛠️ **CLI** claire avec logs

### Prérequis
- Python **3.9+**
- Bibliothèque : **pandas**
```bash
pip install pandas
```

### Démarrage rapide
```bash
# JSON (liste d’écritures)
python fec_to_json.py -i FEC_2023.txt -o FEC_2023.json

# JSON Lines (une écriture par ligne) — idéal pour très gros FEC
python fec_to_json.py -i FEC_2023.txt -o FEC_2023.jsonl --jsonl

# Validation (avertissements) + mode strict (erreurs)
python fec_to_json.py -i FEC.txt -o FEC.json --validate --strict

# Forcer encodage / séparateur si besoin
python fec_to_json.py -i FEC.txt -o out.json --encoding iso-8859-15 --sep "\t"

# Sortie compressée
python fec_to_json.py -i FEC.txt -o FEC.json.gz
```

### Options CLI
| Option | Défaut | Description |
|---|---:|---|
| `-i, --input` | — | Chemin du FEC en entrée (texte) |
| `-o, --output` | — | Chemin de sortie JSON/JSONL (`.gz` accepté) |
| `--encoding` | `auto` | `auto`, `utf-8`, `iso-8859-15`, `iso-8859-1` |
| `--sep` | `auto` | `auto`, `\t`, `|`, `;`, `,` |
| `--chunksize` | `200000` | Taille de chunk (lignes) pour pandas |
| `--mode` | `stream` | `stream` (écritures contiguës) ou `inmem` (regroupement sûr) |
| `--jsonl` | `False` | Sortie JSON Lines (1 écriture par ligne) |
| `--numbers` | `string` | `string` (défaut) ou `float` pour les montants |
| `--validate` | `False` | Active les contrôles (colonnes + équilibre) |
| `--strict` | `False` | Rend les avertissements bloquants |

### Schéma de sortie (par écriture)
```json
{
  "journal": {"code": "ACH", "lib": "Achats"},
  "ecritureNum": "2023-000123",
  "date": "2023-05-18",
  "libelle": "Facture X",
  "lignes": [
    {
      "compte": "401000",
      "compteLib": "Fournisseurs",
      "compAuxNum": "",
      "compAuxLib": "",
      "debit": "0.00",
      "credit": "125.33",
      "pieceRef": "FAC-20230518-ACME",
      "pieceDate": "2023-05-18",
      "ecritureLet": "",
      "dateLet": "",
      "validDate": "2023-05-20",
      "montantDevise": "",
      "iDevise": ""
    }
  ],
  "rawKeys": ["JournalCode","JournalLib","EcritureNum","EcritureDate","CompteNum","CompteLib","CompAuxNum","CompAuxLib","PieceRef","PieceDate","EcritureLib","Debit","Credit","EcritureLet","DateLet","ValidDate","Montantdevise","Idevise"]
}
```
> Par défaut, les montants sont **des chaînes** pour éviter tout aléa d’arrondi. Utilise `--numbers float` si tu veux des nombres.

### Hypothèses & remarques
- Le mode **streaming** (`--mode stream`) suppose que les lignes d’une même écriture sont **contiguës** dans le FEC (cas le plus courant).  
  Si ce n’est pas garanti, préfère `--mode inmem`.
- La **validation** (`--validate`) vérifie la présence des **18 colonnes** et l’équilibre **Débit = Crédit** par écriture (`--strict` pour échouer).

### Conseils performance
- Utilise `--jsonl` sur des volumes massifs ou pour l’ingestion incrémentale.
- Ajuste `--chunksize` selon ta RAM.
- Ajoute `.gz` pour réduire I/O et stockage.

### Installation locale (venv optionnel)
```bash
python -m venv .venv
source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -U pip pandas
```

### Licence
Licence **GNU Affero GPL v3.0**. Voir [LICENSE](./LICENSE).

### Contact
- Twitter : [@FabriceHeuvrard](https://twitter.com/FabriceHeuvrard)  
- LinkedIn : <https://www.linkedin.com/in/fabriceheuvrard/>

---

## Changelog (high level)
- **feat:** robust converter `fec_to_json.py` (auto encoding/sep, streaming, JSONL, validation, CLI)  
- **breaking:** output is now **one object per entry** (not raw lines list)

## Contributing
Issues and PRs are welcome. Please keep changes focused and add a short test/example when relevant.
