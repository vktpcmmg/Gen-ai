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

st.title("🔍 New Commissioning Search Tool (Card View)")

df = load_excel()
st.success("Excel loaded successfully from GitHub")

selected_column = st.selectbox("Select Column to Search", df.columns)
search_value = st.text_input("Enter value to search")

if st.button("Search"):
    if search_value.strip() == "":
        st.warning("Please enter a value.")
    else:
        mask = df[selected_column].astype(str).str.contains(search_value, case=False, na=False)
        results = df[mask]

        if results.empty:
            st.error("No matching records found.")
        else:
            st.success(f"{len(results)} record(s) found.")

            # ----------- CARD VIEW -----------
            for idx, row in results.iterrows():
                
                st.markdown(
                    """
                    <div style="
                        background-color: #f2f2f2; 
                        padding: 15px; 
                        border-radius: 10px; 
                        margin-bottom: 20px;
                        border-left: 8px solid #4CAF50;
                    ">
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(f"### 🧾 Result {idx+1}")

                # Display each column vertically inside card
                for col in df.columns:
                    value = row[col]
                    st.markdown(f"**{col}:** {value}")

                st.markdown("</div>", unsafe_allow_html=True)
