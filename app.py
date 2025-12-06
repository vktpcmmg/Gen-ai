# app.py
# -------------------------
# Simple GenAI Q&A over "New Commissioning" Excel stored on GitHub.
# Share the Streamlit app link with employees so they can ask questions like:
# "What is notification no. of meter no. 123123?"

import os
import re
from io import BytesIO

import pandas as pd
import requests
import streamlit as st
from openai import OpenAI


# =============== CONFIG ===============

# 1) Put your RAW GitHub URL of the New Commissioning Excel here
# Example:
# GITHUB_EXCEL_URL = "https://raw.githubusercontent.com/USERNAME/REPO/BRANCH/path/to/new_commissioning.xlsx"
GITHUB_EXCEL_URL = "https://raw.githubusercontent.com/vktpcmmg/Gen-ai/main/new_commissioning.xlsx"

# 2) OpenAI model name
OPENAI_MODEL = "gpt-4.1-mini"

# 3) Choose which columns are searchable & answerable.
#    You can edit this list as per your actual column names.
ALLOWED_COLUMNS = [
    "Month",
    "Service Order(SO) Type",
    "Service Order(SO) Number",
    "Notification Type",
    "Notification No.",
    "Zone",
    "MIT Zone",
    "Work Center",
    "Consumer/ customer Type",
    "No of Mtrs",
    "Meter Type",
    "Old Meter",
    "New Meter",
    "Service Order(SO) Meter Type",
    "Service Order(SO) Status",
    "Notification Status",
    "Basic Date",
    "Notification Creation Date",
    "Service Order(SO) Date",
    "Service Order(SO) Time",
    "Activity Date",
    "Activity Time",
    "Start Date",
    "Start Time",
    "Finish date",
    "Finish Time",
    "Choice of Mtr",
    "Rate Category",
    "Manufacturer",
    "Device Desc.",
    "Material No",
    "M.F",
    "AMR-Modem Details",
    "Engineer",
    "Sec. Rep.",
    "Vendor",
    "Tata Representative",
    "Notif. Desc",
    "Subject Category 1",
    "Subject Category Cat2",
    "Subject Category 3",
    "Subject Category 4",
    "Reason Category1",
    "Reason Category2",
    "Reason Category3",
    "Reason Category4",
    "CA No",
    "Business Partner",
    "MRU",
    "Consumer Name",
    "Site Address",
    "District",
    "networkdays site (Site TAT)",
    "networkdays SAP (SAP TAT)",
    "overall TAT",
    "Beyond TAT site Status",
    "Beyond TAT SAP status",
]

# As you requested: ID columns are same as allowed columns
ID_COLUMNS = ALLOWED_COLUMNS[:]


# =============== HELPERS ===============

@st.cache_data(show_spinner=True)
def load_data_from_github(url: str) -> pd.DataFrame:
    resp = requests.get(url)
    resp.raise_for_status()
    df = pd.read_excel(BytesIO(resp.content))
    return df


def find_candidate_rows(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """
    Very simple search:
    - Extract numbers (like meter no, CA no, SO no, notification no) from the query.
    - Return rows where any ID_COLUMN contains one of those numbers as substring.
    """
    # Get only columns that actually exist in the DataFrame
    existing_id_cols = [c for c in ID_COLUMNS if c in df.columns]

    if not existing_id_cols:
        return df.iloc[0:0]  # empty df

    # Extract numbers from query (e.g. "123123")
    numbers = re.findall(r"\d+", query)
    if not numbers:
        # If no numbers, do a simple full-text search in all ID columns
        mask = pd.Series(False, index=df.index)
        q_lower = query.lower()
        for col in existing_id_cols:
            mask = mask | df[col].astype(str).str.lower().str.contains(q_lower, na=False)
        return df[mask]

    # If we have numbers, match on them
    mask = pd.Series(False, index=df.index)
    for col in existing_id_cols:
        col_str = df[col].astype(str)
        for num in numbers:
            mask = mask | col_str.str.contains(num, na=False)

    return df[mask]


def build_context_from_rows(rows: pd.DataFrame, max_rows: int = 10) -> str:
    """
    Convert a few matching rows into a text table for the AI model.
    """
    if rows.empty:
        return "No matching rows were found in the data."

    # Only keep columns that actually exist and are allowed
    existing_allowed_cols = [c for c in ALLOWED_COLUMNS if c in rows.columns]

    rows = rows[existing_allowed_cols].head(max_rows)

    lines = []
    for idx, row in rows.iterrows():
        parts = []
        for col in existing_allowed_cols:
            value = row[col]
            if pd.isna(value):
                continue
            parts.append(f"{col}: {value}")
        lines.append(" | ".join(parts))

    context = "\n".join(lines)
    return context


def ask_genai(question: str, context: str) -> str:
    """
    Send question + context to OpenAI and return answer text.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "Error: OPENAI_API_KEY environment variable is not set on the server."

    client = OpenAI(api_key=api_key)

    system_prompt = (
        "You are a Tata Power metering data assistant. "
        "You answer questions ONLY based on the tabular context provided. "
        "If information is not present in context, say clearly that you cannot find it. "
        "Answer very concisely and include key IDs (meter no, CA no, SO, notification) when relevant."
    )

    full_input = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Question: {question}\n\n"
                f"Here is the data context (rows from Excel):\n{context}"
            ),
        },
    ]

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=full_input,
    )

    # Extract first text output
    try:
        return response.output[0].content[0].text
    except Exception:
        return "Error: Could not parse response from model."


# =============== STREAMLIT APP ===============

def main():
    st.title("New Commissioning Data – GenAI Assistant")
    st.write(
        """
        Ask questions about **new commissioning** meters using natural language.
        Examples:
        - "What is notification no of meter no 123123?"
        - "Give CA number and site address for service order 4500XXXXX."
        - "What is the zone and MIT zone for CA no 5000XXXXX?"
        """
    )

    # Load data
    with st.spinner("Loading data from GitHub..."):
        try:
            df = load_data_from_github(GITHUB_EXCEL_URL)
        except Exception as e:
            st.error(f"Failed to load Excel from GitHub. Check GITHUB_EXCEL_URL.\n\n{e}")
            return

    st.success("Excel loaded successfully from GitHub.")

    # Show columns (optional, for debug)
    with st.expander("Show available columns in Excel"):
        st.write(list(df.columns))

    question = st.text_input(
        "Type your question:",
        placeholder="e.g. What is notification no of meter no 123123?",
    )

    if st.button("Get Answer") and question.strip():
        with st.spinner("Searching in data and asking GenAI..."):
            # 1) Find candidate rows
            candidate_rows = find_candidate_rows(df, question)

            if candidate_rows.empty:
                st.warning("No matching rows found in the Excel for this query.")
                return

            # 2) Build context for the model
            context_text = build_context_from_rows(candidate_rows, max_rows=10)

            # 3) Ask GenAI
            answer = ask_genai(question, context_text)

        # 4) Show only text output (as you requested)
        st.subheader("Answer")
        st.write(answer)

        # Optional: Show the rows used as context for transparency
        with st.expander("Show matching rows from data (for reference)"):
            st.dataframe(candidate_rows.head(20))


if __name__ == "__main__":
    main()
