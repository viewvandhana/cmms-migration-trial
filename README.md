
# Smart CMMS Data Migration Assistant (Private Version)

This Streamlit-based app helps CMMS customers migrate their legacy data (Excel/CSV) with:
- AI-powered field mapping
- Data validation and cleaning
- Private login access

## 🚀 Features
- Secure login using `streamlit-authenticator`
- Fuzzy field mapping with synonyms
- Cleans date formats and missing required fields
- Downloadable cleaned output

## 📦 Installation

```bash
git clone https://github.com/your-org/cmms-migration-tool.git
cd cmms-migration-tool
pip install -r requirements.txt
```

## ▶️ Run the App

```bash
streamlit run cmms_migration_tool.py
```

The app will open at `http://localhost:8501`

## 🔐 Default Login Credentials
- **Username**: vandhana
- **Password**: your_password1

(Change these in `cmms_migration_tool.py`)

## 🛠 Customize
- Add more field synonyms
- Integrate with your CMMS API
- Deploy on your private cloud or VM
