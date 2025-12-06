import pandas as pd
import streamlit as st
import requests
from io import BytesIO

# ====================
# CONFIG
# ====================

GITHUB_EXCEL_URL = "https://raw.githubusercontent.com/vktpcmmg/Gen-ai/main/new_commissioning.xlsx"

@st.cache_data
def load_excel():
    resp = requests.get(GITHUB_EXCEL_URL)
    resp.raise_for_status()
    df = pd.read_excel(BytesIO(resp.content))
    return df

# ====================
# STREAMLIT UI
# ====================

st.title("New Commissioning Search Tool (No OpenAI Needed)")

df = load_excel()

st.success("Excel loaded successfully from GitHub")

# Let user choose any column
selected_column = st.selectbox("Select Column to Search", df.columns)

# Let user enter value
search_value = st.text_input("Enter value to search")

if st.button("Search"):
    if search_value.strip() == "":
        st.warning("Please enter a value.")
    else:
        # Convert everything to string for easy matching
        mask = df[selected_column].astype(str).str.contains(search_value, case=False, na=False)

        results = df[mask]

        if results.empty:
            st.error("No matching records found.")
        else:
            st.success(f"{len(results)} record(s) found.")
            st.dataframe(results)
