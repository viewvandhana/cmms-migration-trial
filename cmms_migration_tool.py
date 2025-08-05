import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation

st.set_page_config(page_title="CMMS Migration Tool", layout="wide")
st.title("📥 CMMS Data Migration Tool")

st.markdown("Upload field rules and your CMMS data to validate, clean, and generate compliant import sheets.")

# --- Load field rules ---
def load_field_rules_from_excel(file):
    df = pd.read_excel(file)
    cmms_fields = df["Field Name"].apply(lambda x: str(x).strip()).tolist()
    field_rules = {}

    for _, row in df.iterrows():
        field_name = str(row["Field Name"]).strip()
        raw_ref = str(row.get("Reference Values", "")).strip()
        ref_values = []
        if raw_ref and any(c.isalnum() for c in raw_ref):
            ref_values = [val.strip() for val in raw_ref.split(";") if val.strip()]
        field_rules[field_name] = {
            "type": str(row["Type"]).strip(),
            "required": bool(row["Required"]),
            "ref_values": ref_values
        }

    synonym_map = {}
    for _, row in df.iterrows():
        field_name = str(row["Field Name"]).strip()
        synonyms = [s.strip().lower() for s in str(row["Synonyms"]).split(";") if s.strip()]
        synonym_map[field_name] = synonyms

    return cmms_fields, field_rules, synonym_map

# --- Map using synonyms ---
def map_using_synonyms(user_columns, synonym_map):
    field_map = {}
    for col in user_columns:
        mapped = "Unmapped"
        col_lower = col.strip().lower()
        for cmms_field, synonyms in synonym_map.items():
            if col_lower == cmms_field.lower() or col_lower in synonyms:
                mapped = cmms_field
                break
        field_map[col] = mapped
    return field_map

# --- Validation and error logging ---
def validate_and_clean(df, field_map, field_rules):
    cleaned_df = pd.DataFrame()
    error_log = []

    for source_col, target_col in field_map.items():
        if target_col == "Unmapped" or target_col not in field_rules:
            continue

        rule = field_rules[target_col]
        field_type = rule["type"]
        required = rule["required"]
        ref_values = rule.get("ref_values", [])
        original_series = df[source_col]
        cleaned_series = original_series.copy()

        for idx, val in original_series.items():
            row_num = idx + 2

            if required and (pd.isna(val) or val == ""):
                error_log.append({"Row": row_num, "Column": source_col, "Issue": "Missing required value"})
                continue

            if field_type == "Date":
                try:
                    cleaned_series[idx] = pd.to_datetime(val)
                except:
                    error_log.append({"Row": row_num, "Column": source_col, "Issue": "Invalid date format"})
                    cleaned_series[idx] = pd.NaT

            elif field_type == "Number":
                try:
                    cleaned_series[idx] = pd.to_numeric(val)
                except:
                    error_log.append({"Row": row_num, "Column": source_col, "Issue": "Invalid number"})
                    cleaned_series[idx] = pd.NA

            elif field_type == "Text":
                try:
                    cleaned_series[idx] = str(val)
                except:
                    error_log.append({"Row": row_num, "Column": source_col, "Issue": "Invalid text"})

            if ref_values:
                val_str = str(val).strip()
                if val_str not in ref_values:
                    error_log.append({
                        "Row": row_num,
                        "Column": source_col,
                        "Issue":
