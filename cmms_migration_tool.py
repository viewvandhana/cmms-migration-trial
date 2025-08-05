import streamlit as st
import pandas as pd
import difflib
from datetime import datetime

st.title("🧠 Smart CMMS Data Migration Assistant")

st.write("Upload your Excel or CSV file to auto-map fields, validate data, and clean common issues.")

# Step 1: Upload file
uploaded_file = st.file_uploader("Upload your data file (Excel or CSV)", type=["csv", "xlsx"])

# CMMS internal field definitions
cmms_fields = {
    "Work Order Number": {"type": "Text", "required": True},
    "Work Order Date": {"type": "Date", "required": True},
    "Asset": {"type": "Text", "required": True},
    "Technician": {"type": "Text", "required": False}
}

# Define synonyms for better matching
field_synonyms = {
    "WO_ID": "Work Order Number",
    "WO_Date": "Work Order Date",
    "Asset_Name": "Asset",
    "Assigned_Tech": "Technician"
}

def map_fields(customer_columns, cmms_keys):
    mappings = {}
    for col in customer_columns:
        if col in field_synonyms:
            mappings[col] = field_synonyms[col]
            continue
        match = difflib.get_close_matches(col, cmms_keys, n=1, cutoff=0.4)
        mappings[col] = match[0] if match else "Unmapped"
    return mappings

def validate_and_clean(df, field_map):
    validation_report = []
    cleaned_df = pd.DataFrame()

    for source_col, target_col in field_map.items():
        if target_col == "Unmapped":
            continue
        if target_col not in cmms_fields:
            continue

        field_type = cmms_fields[target_col]["type"]
        required = cmms_fields[target_col]["required"]
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

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("📄 Uploaded Data Preview")
    st.dataframe(df.head())

    customer_columns = df.columns.tolist()
    cmms_keys = list(cmms_fields.keys())
    mapped_fields = map_fields(customer_columns, cmms_keys)

    st.subheader("🔄 Field Mapping Suggestions")
    mapping_df = pd.DataFrame({
        "Your Column": list(mapped_fields.keys()),
        "Mapped To": list(mapped_fields.values())
    })
    st.dataframe(mapping_df)

    cleaned_data, report = validate_and_clean(df, mapped_fields)

    st.subheader("✅ Validation Report")
    for line in report:
        st.write("• " + line)

    st.subheader("🧹 Cleaned Data Preview")
    st.dataframe(cleaned_data.head())

    csv = cleaned_data.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Cleaned Data", csv, "cleaned_cmms_data.csv", "text/csv")
