
import streamlit as st
import pandas as pd
from datetime import datetime

st.title("📥 CMMS Data Migration Tool (Excel-based Rules + Type Validation)")

st.write("Upload your CMMS field rules Excel file and a data file to auto-map fields, validate types and required values, and clean data.")

# Step 1: Load rules from Excel
def load_field_rules_from_excel(file):
    df = pd.read_excel(file)

    cmms_fields = df["Field Name"].tolist()

    # Build rules
    field_rules = {}
    for _, row in df.iterrows():
        field_rules[row["Field Name"]] = {
            "type": row["Type"],
            "required": bool(row["Required"])
        }

    # Build synonym map
    synonym_map = {}
    for _, row in df.iterrows():
        synonyms = [s.strip().lower() for s in str(row["Synonyms"]).split(";") if s.strip()]
        synonym_map[row["Field Name"]] = synonyms

    return cmms_fields, field_rules, synonym_map

# Step 2: Synonym-based mapper
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

# Step 3: Validation and cleaning
def validate_and_clean(df, field_map, field_rules):
    validation_report = []
    cleaned_df = pd.DataFrame()

    for source_col, target_col in field_map.items():
        if target_col == "Unmapped" or target_col not in field_rules:
            continue

        field_type = field_rules[target_col]["type"]
        required = field_rules[target_col]["required"]
        series = df[source_col].copy()

        if field_type == "Date":
            series = pd.to_datetime(series, errors='coerce')
            invalid_dates = series.isna().sum()
            validation_report.append(f"{target_col}: {invalid_dates} invalid dates corrected.")

        elif field_type == "Number":
            series = pd.to_numeric(series, errors='coerce')
            invalid_numbers = series.isna().sum()
            validation_report.append(f"{target_col}: {invalid_numbers} invalid numbers corrected.")

        elif field_type == "Text":
            # Convert all to string (if not missing)
            series = series.astype(str).where(~series.isna(), None)
            non_string_count = sum([not isinstance(val, str) for val in series.dropna()])
            validation_report.append(f"{target_col}: {non_string_count} values coerced to text.")

        if required:
            missing_count = series.isna().sum()
            validation_report.append(f"{target_col}: {missing_count} missing required values.")

        cleaned_df[target_col] = series

    return cleaned_df, validation_report

# Upload rules file
rules_file = st.file_uploader("Upload CMMS Field Rules Excel File", type=["xlsx"])

if rules_file:
    cmms_fields, cmms_field_rules, synonym_map = load_field_rules_from_excel(rules_file)
    st.success("✅ Field rules loaded successfully!")

    # Upload data file
    uploaded_file = st.file_uploader("Upload your data file (Excel or CSV)", type=["csv", "xlsx"])

    if uploaded_file:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.subheader("📄 Uploaded Data Preview")
        st.dataframe(df.head())

        # Field mapping
        st.subheader("🔄 Field Mapping Using Synonyms")
        user_columns = df.columns.tolist()
        mapped_fields = map_using_synonyms(user_columns, synonym_map)

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
        cleaned_data, report = validate_and_clean(df, mapped_fields, cmms_field_rules)

        for line in report:
            st.write("• " + line)

        st.subheader("🧹 Cleaned Data Preview")
        st.dataframe(cleaned_data.head())

        csv = cleaned_data.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Cleaned Data", csv, "cleaned_cmms_data.csv", "text/csv")
