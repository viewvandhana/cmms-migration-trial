import streamlit as st
import pandas as pd
from datetime import datetime

st.title("🔁 CMMS Data Migration Tool (Synonym Mapping, No GPT)")

st.write("Upload your Excel or CSV file to auto-map fields using synonyms, validate data, and clean common issues.")

# CMMS field definitions
cmms_fields = [
    "Work Order Number",
    "Work Order Date",
    "Asset",
    "Technician"
]

# Synonym map (case-insensitive matching)
synonym_map = {
    "Work Order Number": ["wo_id", "work order no", "wo no", "order id"],
    "Work Order Date": ["wo date", "work order date", "order date"],
    "Asset": ["equipment", "machine", "asset_name"],
    "Technician": ["tech", "technician name", "assigned to"]
}

# Validation rules
cmms_field_rules = {
    "Work Order Number": {"type": "Text", "required": True},
    "Work Order Date": {"type": "Date", "required": True},
    "Asset": {"type": "Text", "required": True},
    "Technician": {"type": "Text", "required": False}
}

# Synonym-based mapper
def map_using_synonyms(user_columns):
    field_map = {}
    for col in user_columns:
        mapped = "Unmapped"
        col_lower = col.strip().lower()
        for cmms_field, synonyms in synonym_map.items():
            if col_lower == cmms_field.lower() or col_lower in [s.lower() for s in synonyms]:
                mapped = cmms_field
                break
        field_map[col] = mapped
    return field_map

# Validation & cleaning
def validate_and_clean(df, field_map):
    validation_report = []
    cleaned_df = pd.DataFrame()

    for source_col, target_col in field_map.items():
        if target_col == "Unmapped" or target_col not in cmms_field_rules:
            continue

        field_type = cmms_field_rules[target_col]["type"]
        required = cmms_field_rules[target_col]["required"]
        series = df[source_col].copy()

        if field_type == "Date":
            try:
                series = pd.to_datetime(series, errors='coerce')
            except Exception:
                pass
            invalid_dates = series.isna().sum()
            validation_report.append(f"{target_col}: {invalid_dates} invalid dates corrected.")

        if required:
            missing_count = series.isna().sum()
            validation_report.append(f"{target_col}: {missing_count} missing required values.")

        cleaned_df[target_col] = series

    return cleaned_df, validation_report

# Upload file
uploaded_file = st.file_uploader("Upload your data file (Excel or CSV)", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("📄 Uploaded Data Preview")
    st.dataframe(df.head())

    # Mapping with synonyms
    st.subheader("🔄 Field Mapping Using Synonyms")
    user_columns = df.columns.tolist()
    mapped_fields = map_using_synonyms(user_columns)

    mapping_df = pd.DataFrame({
        "Your Column": list(mapped_fields.keys()),
        "Mapped To": list(mapped_fields.values())
    })
    st.dataframe(mapping_df)

    # Check for missing required fields
    missing_required_fields = [
        field for field, rules in cmms_field_rules.items()
        if rules["required"] and field not in mapped_fields.values()
    ]
    if missing_required_fields:
        st.subheader("⚠️ Missing Required Fields in Uploaded Sheet")
        for field in missing_required_fields:
            st.error(f"Required field not found in upload: **{field}**")

    # Validation & Cleaning
    st.subheader("✅ Validation & Cleaning")
    cleaned_data, report = validate_and_clean(df, mapped_fields)

    for line in report:
        st.write("• " + line)

    st.subheader("🧹 Cleaned Data Preview")
    st.dataframe(cleaned_data.head())

    csv = cleaned_data.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Cleaned Data", csv, "cleaned_cmms_data.csv", "text/csv")
