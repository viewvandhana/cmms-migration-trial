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
        raw_ref = str(row.get("Reference Values", "")).strip().lower()
        ref_values = []
        if raw_ref and raw_ref not in ["", "None", "n/a", "na"]:
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
                        "Issue": f"Value '{val}' not in reference list for '{target_col}'"
                    })

        cleaned_df[target_col] = cleaned_series

    return cleaned_df, error_log

# --- Generate Excel Template ---
def generate_excel_template(cmms_fields, cmms_field_rules):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CMMS Template"

    for col_index, field in enumerate(cmms_fields, start=1):
        ws.cell(row=1, column=col_index, value=field)
        hint = f"({cmms_field_rules[field]['type']}){'*' if cmms_field_rules[field]['required'] else ''}"
        ws.cell(row=2, column=col_index, value=hint)
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_index)].width = max(15, len(field) + 5)

    ref_ws = wb.create_sheet("ReferenceData")
    ref_ws.sheet_state = 'hidden'
    ref_field_map = {}
    ref_col_index = 1

    for field, rule in cmms_field_rules.items():
        ref_values = rule.get("ref_values", [])
        if ref_values:
            for i, val in enumerate(ref_values):
                ref_ws.cell(row=i+1, column=ref_col_index, value=val)
            col_letter = openpyxl.utils.get_column_letter(ref_col_index)
            ref_range = f"ReferenceData!${col_letter}$1:${col_letter}${len(ref_values)}"
            ref_field_map[field] = ref_range
            ref_col_index += 1

    for col_index, field in enumerate(cmms_fields, start=1):
        rule = cmms_field_rules.get(field, {})
        col_letter = openpyxl.utils.get_column_letter(col_index)
        target_range = f"{col_letter}3:{col_letter}100"

        if field in ref_field_map:
            dv = DataValidation(type="list", formula1=f"={ref_field_map[field]}", showDropDown=True)
            dv.error = "Invalid selection"
            dv.prompt = "Choose from list"
            dv.promptTitle = f"{field}"
            dv.add(target_range)
            ws.add_data_validation(dv)

        elif rule.get("type") == "Number":
            dv = DataValidation(type="decimal", allow_blank=not rule["required"])
            dv.error = "Please enter a valid number"
            dv.prompt = "Enter a number"
            dv.promptTitle = f"{field} (Number)"
            dv.add(target_range)
            ws.add_data_validation(dv)

        elif rule.get("type") == "Date":
            dv = DataValidation(type="date", allow_blank=not rule["required"])
            dv.error = "Please enter a valid date"
            dv.prompt = "Enter a date (YYYY-MM-DD)"
            dv.promptTitle = f"{field} (Date)"
            dv.add(target_range)
            ws.add_data_validation(dv)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

# --- Streamlit App ---
rules_file = st.file_uploader("Upload CMMS Field Rules Excel File", type=["xlsx"])

if rules_file:
    cmms_fields, cmms_field_rules, synonym_map = load_field_rules_from_excel(rules_file)
    st.success("✅ Field rules loaded.")

    template_file = generate_excel_template(cmms_fields, cmms_field_rules)
    st.download_button("📄 Download Excel Template", data=template_file, file_name="cmms_template.xlsx")

    uploaded_file = st.file_uploader("Upload Your Data File", type=["csv", "xlsx"])

    if uploaded_file:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
        st.subheader("📄 Uploaded Data Preview")
        st.dataframe(df.head())

        mapped_fields = map_using_synonyms(df.columns.tolist(), synonym_map)
        st.subheader("🧩 Field Mapping (Auto)")
        st.dataframe(pd.DataFrame.from_dict(mapped_fields, orient='index', columns=['Mapped To']))

        cleaned_data, error_log = validate_and_clean(df, mapped_fields, cmms_field_rules)

        if not cleaned_data.empty:
            st.subheader("✅ Cleaned Data")
            st.dataframe(cleaned_data.head())
            st.download_button("📥 Download Cleaned Data", cleaned_data.to_csv(index=False), "cleaned_cmms_data.csv")

        if error_log:
            error_df = pd.DataFrame(error_log)
            st.subheader("❌ Cell-level Error Log")
            st.dataframe(error_df)
            st.download_button("📥 Download Error Log", error_df.to_csv(index=False), "cmms_error_log.csv")
        else:
            st.success("🎉 No validation errors found!")
