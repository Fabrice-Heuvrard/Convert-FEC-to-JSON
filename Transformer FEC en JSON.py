#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
fec_to_json.py
--------------
Convertit un fichier FEC (DGFiP, 18 colonnes) en JSON structuré par écriture.

Points clés :
- Détection automatique de l'encodage (UTF-8, ISO-8859-15, ISO-8859-1).
- Détection automatique du séparateur (tab, |, ;, ,) via heuristiques équilibrées.
- Lecture "gros fichiers" en chunks, avec mode streaming (écritures contiguës) ou in-memory.
- Conversion des dates FEC (YYYYMMDD) en ISO (YYYY-MM-DD).
- Montants en string pour préserver la précision (option pour float).
- Option JSON Lines pour pipeline big data.
- Contrôles optionnels : présence des 18 colonnes, équilibre débit/crédit.
- Sortie compressée si l'extension se termine par .gz

Auteur : Fabrice-friendly
Licence : AGPL-3.0 (alignée avec un partage d'améliorations en réseau)
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import sys
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Dict, Iterable, Iterator, List, Optional, Tuple, Union

import pandas as pd


# -----------------------------
# Constantes FEC & colonnes
# -----------------------------

FEC_COLUMNS: List[str] = [
    "JournalCode",
    "JournalLib",
    "EcritureNum",
    "EcritureDate",
    "CompteNum",
    "CompteLib",
    "CompAuxNum",
    "CompAuxLib",
    "PieceRef",
    "PieceDate",
    "EcritureLib",
    "Debit",
    "Credit",
    "EcritureLet",
    "DateLet",
    "ValidDate",
    "Montantdevise",
    "Idevise",
]

# Colonnes numériques (format DGFiP : généralement virgule décimale)
NUM_COLS = ["Debit", "Credit", "Montantdevise"]

# Colonnes date au format FEC (YYYYMMDD)
DATE_COLS = ["EcritureDate", "PieceDate", "DateLet", "ValidDate"]

# Séparateurs souvent rencontrés dans la nature
CANDIDATE_SEPARATORS = ["\t", "|", ";", ","]

# Encodages usuels de FEC (ordre d'essai)
CANDIDATE_ENCODINGS = ["utf-8", "iso-8859-15", "iso-8859-1"]


# -----------------------------
# Utilitaires d'affichage
# -----------------------------

def log(msg: str, level: str = "INFO") -> None:
    """Affiche un message sur stderr avec un niveau simple."""
    sys.stderr.write(f"[{level}] {msg}\n")


@contextmanager
def timed(section: str):
    """Mesure un bloc pour logs simples."""
    t0 = time.time()
    try:
        yield
    finally:
        dt = time.time() - t0
        log(f"{section} terminé en {dt:.2f}s")


# -----------------------------
# Détection encodage & séparateur
# -----------------------------

def try_decode(sample: bytes, encoding: str) -> Optional[str]:
    """Tente de décoder un échantillon en str. Retourne le texte ou None."""
    try:
        return sample.decode(encoding)
    except UnicodeDecodeError:
        return None


def detect_encoding(path: str, encodings: List[str] = None, sample_size: int = 256 * 1024) -> str:
    """
    Détecte l'encodage en essayant une liste courte d'encodages courants.
    - On évite d'importer chardet/charset-normalizer (dépendance en plus).
    - Heuristique suffisante pour la grande majorité des FEC.

    Retourne l'encodage retenu (défaut utf-8 si rien ne marche, ce qui est rare).
    """
    encs = encodings or CANDIDATE_ENCODINGS
    with open(path, "rb") as f:
        sample = f.read(sample_size)
    for enc in encs:
        txt = try_decode(sample, enc)
        if txt is not None:
            log(f"Encodage détecté : {enc}")
            return enc
    log("Aucun encodage testé n'a fonctionné — fallback UTF-8", level="WARN")
    return "utf-8"


def detect_separator(sample_text: str) -> str:
    """
    Détecte le séparateur en stock en se basant sur :
    - Lignes d'en-tête : on suppose que les 18 colonnes FEC sont présentes.
    - Comptage des occurrences de candidats sur la première ligne.
    - On privilégie tabulation ou '|' si match plausible.

    NB : pandas a un 'sep=None' (python engine) qui sniffe, mais ici on veut être déterministe.
    """
    # Prend les premières lignes non vides
    lines = [ln for ln in sample_text.splitlines() if ln.strip()]
    head = lines[0] if lines else sample_text

    best_sep = None
    best_score = -1

    for sep in CANDIDATE_SEPARATORS:
        parts = head.split(sep)
        score = len(parts)
        # Heuristique : meilleur est celui qui approche 18 colonnes
        # (mais certains FEC ont plus de colonnes -> on demande >= 18)
        if score >= 18 and score > best_score:
            best_sep = sep
            best_score = score

    if best_sep:
        human = "\\t" if best_sep == "\t" else best_sep
        log(f"Séparateur détecté : '{human}'")
        return best_sep

    # Fallback : on essaye csv.Sniffer sur un petit sample
    try:
        dialect = csv.Sniffer().sniff(sample_text[:10000], delimiters="".join(CANDIDATE_SEPARATORS))
        if dialect.delimiter in CANDIDATE_SEPARATORS:
            best = dialect.delimiter
            human = "\\t" if best == "\t" else best
            log(f"Séparateur sniffer : '{human}'")
            return best
    except Exception:
        pass

    # Dernier recours : tab
    log("Séparateur non détecté avec certitude — fallback tabulation", level="WARN")
    return "\t"


# -----------------------------
# Conversions de champs
# -----------------------------

def normalize_date(val: str) -> str:
    """
    Convertit 'YYYYMMDD' en 'YYYY-MM-DD'.
    - Si vide ou invalid, retourne '' (chaîne vide).
    - Si déjà au bon format, renvoie tel quel.
    """
    v = (val or "").strip()
    if not v:
        return ""
    # Déjà en ISO ?
    if len(v) == 10 and v[4] == "-" and v[7] == "-":
        return v
    # FEC : 8 chiffres
    if len(v) == 8 and v.isdigit():
        return f"{v[0:4]}-{v[4:6]}-{v[6:8]}"
    # On tente parse soft
    try:
        # pandas to_datetime est permissif, mais on normalise en date
        dt = pd.to_datetime(v, errors="coerce")
        if pd.isna(dt):
            return ""
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""


def detect_decimal_comma(df_sample: pd.DataFrame) -> bool:
    """
    Détecte si les montants utilisent la virgule décimale (format FR).
    On inspecte quelques valeurs de Debit/Credit/Montantdevise.
    """
    for col in NUM_COLS:
        if col in df_sample.columns:
            series = df_sample[col].dropna().astype(str).head(100)
            if any("," in s for s in series):
                return True
    return False


def to_decimal_str(val: str, decimal_is_comma: bool) -> str:
    """
    Convertit un montant texte en chaîne normalisée '1234.56' (point décimal),
    en passant par Decimal pour préserver la précision.
    - Entrée : str ou vide
    - Retour : str ('' si vide)
    """
    s = (val or "").strip()
    if s == "":
        return ""
    # Supprime espaces insécables etc.
    s = s.replace("\u00A0", "").replace(" ", "")
    # Remplace virgule par point si nécessaire
    if decimal_is_comma:
        s = s.replace(",", ".")
    try:
        q = Decimal(s)
    except InvalidOperation:
        # Certains FEC mettent '' ou des tirets pour zéros
        return ""
    # Normalisation : 2 décimales pour FEC montants (convention courante)
    q = q.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return format(q, "f")


def to_float(val: str, decimal_is_comma: bool) -> Optional[float]:
    """Conversion alternative vers float (avec perte potentielle de précision)."""
    s = to_decimal_str(val, decimal_is_comma)
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


# -----------------------------
# Modèle de sortie
# -----------------------------

@dataclass
class EntryLine:
    compte: str
    compteLib: str
    compAuxNum: str
    compAuxLib: str
    debit: str
    credit: str
    pieceRef: str
    pieceDate: str
    ecritureLet: str
    dateLet: str
    validDate: str
    montantDevise: str
    iDevise: str


@dataclass
class Entry:
    journal_code: str
    journal_lib: str
    ecriture_num: str
    ecriture_date: str
    ecriture_lib: str
    lignes: List[EntryLine]

    def to_dict(self, numbers: str = "string") -> Dict:
        """
        numbers: 'string' (par défaut) ou 'float'
        """
        def num_out(s: str) -> Union[str, float, None]:
            if numbers == "float":
                return float(s) if s != "" else None
            return s

        return {
            "journal": {"code": self.journal_code, "lib": self.journal_lib},
            "ecritureNum": self.ecriture_num,
            "date": self.ecriture_date,
            "libelle": self.ecriture_lib,
            "lignes": [
                {
                    "compte": ln.compte,
                    "compteLib": ln.compteLib,
                    "compAuxNum": ln.compAuxNum,
                    "compAuxLib": ln.compAuxLib,
                    "debit": num_out(ln.debit),
                    "credit": num_out(ln.credit),
                    "pieceRef": ln.pieceRef,
                    "pieceDate": ln.pieceDate,
                    "ecritureLet": ln.ecritureLet,
                    "dateLet": ln.dateLet,
                    "validDate": ln.validDate,
                    "montantDevise": num_out(ln.montantDevise),
                    "iDevise": ln.iDevise,
                }
                for ln in self.lignes
            ],
            "rawKeys": FEC_COLUMNS,
        }


# -----------------------------
# Validation & contrôles
# -----------------------------

def validate_columns(df: pd.DataFrame, strict: bool) -> None:
    """
    Valide la présence des 18 colonnes FEC.
    - En mode strict : lève une exception si manquant.
    - Sinon : log WARN (on créera des colonnes vides pour lisser la suite).
    """
    missing = [c for c in FEC_COLUMNS if c not in df.columns]
    if missing:
        msg = f"Colonnes FEC manquantes : {missing}"
        if strict:
            raise ValueError(msg)
        else:
            log(msg, level="WARN")


def balance_check(entry: Entry, numbers: str) -> Tuple[Decimal, Decimal, bool]:
    """
    Vérifie équilibre Débit/Crédit au niveau de l'écriture.
    Retourne (sum_debit, sum_credit, ok)
    """
    def dec_of(v) -> Decimal:
        if v in (None, ""):
            return Decimal("0")
        return Decimal(str(v))

    dsum = Decimal("0")
    csum = Decimal("0")
    for ln in entry.lignes:
        d = ln.debit if numbers == "string" else ("" if ln.debit is None else str(ln.debit))
        c = ln.credit if numbers == "string" else ("" if ln.credit is None else str(ln.credit))
        dsum += dec_of(d)
        csum += dec_of(c)
    return dsum, csum, (dsum == csum)


# -----------------------------
# E/S JSON (fichier ou gzip)
# -----------------------------

@contextmanager
def smart_open_write(path: str):
    """
    Ouvre un fichier en écriture, avec gzip auto si l'extension finit par .gz.
    Utilise utf-8 pour JSON.
    """
    if path.endswith(".gz"):
        with gzip.open(path, "wt", encoding="utf-8") as f:
            yield f
    else:
        with open(path, "w", encoding="utf-8") as f:
            yield f


# -----------------------------
# Conversion : DataFrame -> Entries
# -----------------------------

def df_iter_entries_sorted(df: pd.DataFrame, decimal_is_comma: bool, numbers: str) -> Iterator[Entry]:
    """
    Suppose que df est **trié par** (JournalCode, EcritureNum) et que les lignes
    d'une écriture sont contiguës (cas standard des FEC exportés).
    Construit au fil de l'eau des Entry, sans tout charger en mémoire.
    """
    # On s'assure de garder l'ordre d'entrée (pas de sort implicite)
    df = df  # already chunk; no sort
    last_key: Optional[Tuple[str, str]] = None
    buffer_lines: List[EntryLine] = []
    header_ctx = {"JournalCode": "", "JournalLib": "", "EcritureNum": "", "EcritureDate": "", "EcritureLib": ""}

    for _, row in df.iterrows():
        jc = str(row.get("JournalCode", "") or "")
        jl = str(row.get("JournalLib", "") or "")
        en = str(row.get("EcritureNum", "") or "")
        key = (jc, en)

        # Prépare ligne normalisée
        ln = EntryLine(
            compte=str(row.get("CompteNum", "") or ""),
            compteLib=str(row.get("CompteLib", "") or ""),
            compAuxNum=str(row.get("CompAuxNum", "") or ""),
            compAuxLib=str(row.get("CompAuxLib", "") or ""),
            debit=to_decimal_str(str(row.get("Debit", "") or ""), decimal_is_comma),
            credit=to_decimal_str(str(row.get("Credit", "") or ""), decimal_is_comma),
            pieceRef=str(row.get("PieceRef", "") or ""),
            pieceDate=normalize_date(str(row.get("PieceDate", "") or "")),
            ecritureLet=str(row.get("EcritureLet", "") or ""),
            dateLet=normalize_date(str(row.get("DateLet", "") or "")),
            validDate=normalize_date(str(row.get("ValidDate", "") or "")),
            montantDevise=to_decimal_str(str(row.get("Montantdevise", "") or ""), decimal_is_comma),
            iDevise=str(row.get("Idevise", "") or ""),
        )

        if last_key is None:
            # Premier passage : amorce le buffer
            buffer_lines = [ln]
            header_ctx = {
                "JournalCode": jc,
                "JournalLib": jl,
                "EcritureNum": en,
                "EcritureDate": normalize_date(str(row.get("EcritureDate", "") or "")),
                "EcritureLib": str(row.get("EcritureLib", "") or ""),
            }
            last_key = key
            continue

        if key == last_key:
            # Même écriture : accumule
            buffer_lines.append(ln)
        else:
            # Nouvelle écriture : on yield l'ancienne
            yield Entry(
                journal_code=header_ctx["JournalCode"],
                journal_lib=header_ctx["JournalLib"],
                ecriture_num=header_ctx["EcritureNum"],
                ecriture_date=header_ctx["EcritureDate"],
                ecriture_lib=header_ctx["EcritureLib"],
                lignes=buffer_lines,
            )
            # Reset avec la nouvelle écriture
            buffer_lines = [ln]
            header_ctx = {
                "JournalCode": jc,
                "JournalLib": jl,
                "EcritureNum": en,
                "EcritureDate": normalize_date(str(row.get("EcritureDate", "") or "")),
                "EcritureLib": str(row.get("EcritureLib", "") or ""),
            }
            last_key = key

    # Fin de chunk : sortir la dernière écriture si présente
    if last_key is not None and buffer_lines:
        yield Entry(
            journal_code=header_ctx["JournalCode"],
            journal_lib=header_ctx["JournalLib"],
            ecriture_num=header_ctx["EcritureNum"],
            ecriture_date=header_ctx["EcritureDate"],
            ecriture_lib=header_ctx["EcritureLib"],
            lignes=buffer_lines,
        )


def df_group_inmem(df: pd.DataFrame, decimal_is_comma: bool, numbers: str) -> Iterator[Entry]:
    """
    Alternative 'in-memory' : regroupe par (JournalCode, EcritureNum) sans présumer contiguïté.
    Moins scalable mais sûr si le FEC est désordonné.
    """
    grouped = df.groupby(["JournalCode", "EcritureNum"], sort=False, dropna=False)
    for (jc, en), g in grouped:
        # On reprend les valeurs de la première ligne pour l'en-tête écriture
        first = g.iloc[0]
        ecriture_date = normalize_date(str(first.get("EcritureDate", "") or ""))
        ecriture_lib = str(first.get("EcritureLib", "") or "")
        jl = str(first.get("JournalLib", "") or "")

        lines: List[EntryLine] = []
        for _, row in g.iterrows():
            lines.append(
                EntryLine(
                    compte=str(row.get("CompteNum", "") or ""),
                    compteLib=str(row.get("CompteLib", "") or ""),
                    compAuxNum=str(row.get("CompAuxNum", "") or ""),
                    compAuxLib=str(row.get("CompAuxLib", "") or ""),
                    debit=to_decimal_str(str(row.get("Debit", "") or ""), decimal_is_comma),
                    credit=to_decimal_str(str(row.get("Credit", "") or ""), decimal_is_comma),
                    pieceRef=str(row.get("PieceRef", "") or ""),
                    pieceDate=normalize_date(str(row.get("PieceDate", "") or "")),
                    ecritureLet=str(row.get("EcritureLet", "") or ""),
                    dateLet=normalize_date(str(row.get("DateLet", "") or "")),
                    validDate=normalize_date(str(row.get("ValidDate", "") or "")),
                    montantDevise=to_decimal_str(str(row.get("Montantdevise", "") or ""), decimal_is_comma),
                    iDevise=str(row.get("Idevise", "") or ""),
                )
            )

        yield Entry(
            journal_code=str(jc or ""),
            journal_lib=jl,
            ecriture_num=str(en or ""),
            ecriture_date=ecriture_date,
            ecriture_lib=ecriture_lib,
            lignes=lines,
        )


# -----------------------------
# Pipeline principal
# -----------------------------

def process_file(
    input_path: str,
    output_path: str,
    encoding: str = "auto",
    sep: str = "auto",
    chunksize: int = 200_000,
    mode: str = "stream",  # 'stream' (écritures contiguës) ou 'inmem'
    jsonl: bool = False,
    numbers: str = "string",  # 'string' ou 'float'
    validate: bool = False,
    strict: bool = False,
) -> None:
    """
    Exécute la conversion avec lecture par chunks. Écrit le JSON/JSONL à la volée.
    """
    # 1) Détection encodage & séparateur sur un échantillon lisible
    with open(input_path, "rb") as fb:
        sample_bytes = fb.read(512 * 1024)

    # Encodage
    enc = detect_encoding(input_path) if encoding == "auto" else encoding

    # Séparateur (après décodage)
    sample_text = try_decode(sample_bytes, enc) or ""
    delimiter = detect_separator(sample_text) if sep == "auto" else sep

    # 2) Lecture chunkée
    reader = pd.read_csv(
        input_path,
        sep=delimiter,
        encoding=enc,
        dtype=str,                   # on lit tout en str pour maîtriser les conversions
        keep_default_na=False,       # évite NaN -> on préfère chaînes vides pour JSON
        on_bad_lines="error",        # fail fast si lignes cassées
        chunksize=chunksize,
        engine="python",             # compatible avec sep variable
    )

    written = 0
    first_entry = True  # pour JSON array
    total_rows = 0
    total_entries = 0
    decimal_is_comma_global: Optional[bool] = None

    with smart_open_write(output_path) as out:
        if not jsonl:
            out.write("[")  # on va écrire une liste d'objets

        with timed("Conversion"):
            for i, df in enumerate(reader, start=1):
                # Stats & logs
                rows = len(df)
                total_rows += rows
                log(f"Chunk {i}: {rows} lignes")

                # Colonnes FEC : ajouter manquantes si besoin (non strict)
                if validate:
                    validate_columns(df, strict)
                for col in FEC_COLUMNS:
                    if col not in df.columns:
                        df[col] = ""

                # Détection globale virgule décimale sur le 1er chunk
                if decimal_is_comma_global is None:
                    decimal_is_comma_global = detect_decimal_comma(df)

                # Normalisation légère : on s'assure du type str (already) et aucun tri implicite
                # Option 'mode'
                if mode == "inmem":
                    entries_iter = df_group_inmem(df, decimal_is_comma_global, numbers)
                else:
                    # Mode 'stream' : suppose que (JournalCode, EcritureNum) est contigu.
                    # On ne combine pas avec le chunk précédent ici : subtilité -> une écriture
                    # peut chevaucher deux chunks. On gère ça en bufferisant la fin/début.
                    # Implémentation : on utilise un pont "tail" (dernier groupe du chunk précédent).
                    # Pour rester simple et lisible, on fait ci-dessous une concat minime :
                    if i == 1:
                        prev_tail_df = None  # initialisation
                    # Si on a une "queue" du chunk précédent, on la préfixe
                    if "prev_tail_df" in locals() and prev_tail_df is not None:
                        df = pd.concat([prev_tail_df, df], ignore_index=True)

                    # On va découper le dernier groupe pour le buffer "tail_new"
                    # Détecte la clé du dernier groupe
                    if not df.empty:
                        last_jc = df["JournalCode"].iloc[-1]
                        last_en = df["EcritureNum"].iloc[-1]
                        # Indices des lignes du dernier groupe
                        mask_tail = (df["JournalCode"] == last_jc) & (df["EcritureNum"] == last_en)
                        # tail_new = lignes du dernier groupe
                        tail_new = df[mask_tail]
                        # head_df = tout sauf ces lignes (pour sortie immédiate)
                        head_df = df[~mask_tail]
                    else:
                        tail_new = df.iloc[0:0]
                        head_df = df

                    # Iterator sur la partie "head", le "tail" sera préfixé au prochain chunk
                    entries_iter = df_iter_entries_sorted(head_df, decimal_is_comma_global, numbers)

                # Écriture des entries
                for entry in entries_iter:
                    total_entries += 1

                    # Contrôles optionnels
                    if validate:
                        dsum, csum, ok = balance_check(entry, numbers)
                        if not ok:
                            msg = (f"Écriture non équilibrée {entry.journal_code}/{entry.ecriture_num} "
                                   f"(Débit={dsum}, Crédit={csum})")
                            if strict:
                                raise ValueError(msg)
                            else:
                                log(msg, level="WARN")

                    # Sortie JSON/JSONL
                    obj = entry.to_dict(numbers=numbers)
                    if jsonl:
                        out.write(json.dumps(obj, ensure_ascii=False))
                        out.write("\n")
                    else:
                        if not first_entry:
                            out.write(",")
                        out.write(json.dumps(obj, ensure_ascii=False))
                        first_entry = False

                # Mise à jour du tail pour chunk suivant (mode stream)
                if mode == "stream":
                    prev_tail_df = tail_new if not tail_new.empty else None

            # Après la boucle chunks : sortir le dernier tail si présent (mode stream)
            if mode == "stream" and "prev_tail_df" in locals() and prev_tail_df is not None:
                for entry in df_iter_entries_sorted(prev_tail_df, decimal_is_comma_global, numbers):
                    total_entries += 1
                    if validate:
                        dsum, csum, ok = balance_check(entry, numbers)
                        if not ok:
                            msg = (f"Écriture non équilibrée {entry.journal_code}/{entry.ecriture_num} "
                                   f"(Débit={dsum}, Crédit={csum})")
                            if strict:
                                raise ValueError(msg)
                            else:
                                log(msg, level="WARN")
                    obj = entry.to_dict(numbers=numbers)
                    if jsonl:
                        out.write(json.dumps(obj, ensure_ascii=False))
                        out.write("\n")
                    else:
                        if not first_entry:
                            out.write(",")
                        out.write(json.dumps(obj, ensure_ascii=False))
                        first_entry = False

        if not jsonl:
            out.write("]")

    log(f"Lignes lues : {total_rows}")
    log(f"Écritures émises : {total_entries}")
    log(f"Fichier de sortie : {output_path}")


# -----------------------------
# CLI
# -----------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Convertit un FEC (DGFiP) en JSON structuré par écriture, robuste et scalable."
    )
    p.add_argument("-i", "--input", required=True, help="Chemin du fichier FEC en entrée")
    p.add_argument("-o", "--output", required=True, help="Chemin du fichier JSON/JSONL en sortie ('.gz' accepté)")
    p.add_argument("--encoding", default="auto", help="Encodage d'entrée (auto|utf-8|iso-8859-15|iso-8859-1)")
    p.add_argument("--sep", default="auto", help=r"Séparateur (auto|\t|,|;| |)")
    p.add_argument("--chunksize", type=int, default=200_000, help="Taille de chunk pandas (par défaut 200k)")
    p.add_argument("--mode", choices=["stream", "inmem"], default="stream",
                   help="Regroupement : 'stream' (écritures contiguës) ou 'inmem' (sécurité, mémoire)")
    p.add_argument("--jsonl", action="store_true", help="Sortie JSON Lines (1 écriture par ligne)")
    p.add_argument("--numbers", choices=["string", "float"], default="string",
                   help="Format des montants dans la sortie (string|float)")
    p.add_argument("--validate", action="store_true", help="Active les contrôles (colonnes, équilibre écritures)")
    p.add_argument("--strict", action="store_true", help="En validation, transforme les warnings en erreurs")
    return p


def main():
    args = build_arg_parser().parse_args()
    with timed("Global"):
        process_file(
            input_path=args.input,
            output_path=args.output,
            encoding=args.encoding,
            sep=args.sep if args.sep != r"\t" else "\t",  # accepte --sep "\t"
            chunksize=args.chunksize,
            mode=args.mode,
            jsonl=args.jsonl,
            numbers=args.numbers,
            validate=args.validate,
            strict=args.strict,
        )


if __name__ == "__main__":
    main()
