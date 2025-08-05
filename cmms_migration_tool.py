import streamlit as st
import pandas as pd
import openai
from datetime import datetime

# --- Configuration ---
# Replace with your OpenAI key or load from env/secrets
openai.api_key = "your-openai-api-key"

st.title("🧠 Smart CMMS Data Migration Assistant (GPT-3.5 powered)")

st.write("Upload your Excel or CSV file to auto-map fields, validate data, and clean common issues using GPT.")

# CMMS internal field definitions
cmms_fields = [
    "Work Order Number",
    "Work Order Date",
    "Asset",
    "Technician"
]

# Validation rules
cmms_field_rules = {
    "Work Order Number": {"type": "Text", "required": True},
    "Work Order Date": {"type": "Date", "required": True},
    "Asset": {"type": "Text", "required": True},
    "Technician": {"type": "Text", "required": False}
}

# GPT-based column mapper
def gpt_field_mapper(column_name, cmms_fields):
    prompt = (
        "You are a smart CMMS data assistant.\n\n"
        "Your job is to match the following column to the most appropriate internal CMMS field.\n\n"
        f"User column: \"{column_name}\"\n"
        f"Available CMMS fields: {cmms_fields}\n\n"
        "Only return one of the CMMS fields exactly as listed. If no good match exists, return \"Unmapped\"."
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        return "Unmapped"

# Data validation and cleaning
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

# File upload
uploaded_file = st.file_uploader("Upload your data file (Excel or CSV)", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("📄 Uploaded Data Preview")
    st.dataframe(df.head())

    # GPT Mapping
    st.subheader("🔄 GPT Field Mapping Suggestions")
    customer_columns = df.columns.tolist()
    mapped_fields = {col: gpt_field_mapper(col, cmms_fields) for col in customer_columns}
    mapping_df = pd.DataFrame({
        "Your Column": list(mapped_fields.keys()),
        "Mapped To": list(mapped_fields.values())
    })
    st.dataframe(mapping_df)

    # ✅ Check for missing required fields
    missing_required_fields = [
        field for field, rules in cmms_field_rules.items()
        if rules["required"] and field not in mapped_fields.values()
    ]
    if missing_required_fields:
        st.subheader("⚠️ Missing Required Fields in Uploaded Sheet")
        for field in missing_required_fields:
            st.error(f"Required field not found in upload: **{field}**")

    # Validation + cleaning
    st.subheader("✅ Validation & Cleaning")
    cleaned_data, report = validate_and_clean(df, mapped_fields)

    for line in report:
        st.write("• " + line)

    st.subheader("🧹 Cleaned Data Preview")
    st.dataframe(cleaned_data.head())

    csv = cleaned_data.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Cleaned Data", csv, "cleaned_cmms_data.csv", "text/csv")
