import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# =========================
# CONFIG: GITHUB EXCEL URL
# =========================
GITHUB_EXCEL_URL = (
    "https://raw.githubusercontent.com/vktpcmmg/Gen-ai/main/new_commissioning.xlsx"
    # If you change file name / repo / branch, update this link
)


# =========================
# HELPER: LOAD EXCEL FROM GITHUB
# =========================
@st.cache_data(show_spinner=True)
def load_excel_from_github(url: str) -> pd.DataFrame:
    resp = requests.get(url)
    resp.raise_for_status()
    # Read first sheet (new commissioning)
    df = pd.read_excel(BytesIO(resp.content))
    return df


# =========================
# HELPER: CONVERT DF TO EXCEL BYTES
# (SAME COLUMNS / FORMAT AS INPUT)
# =========================
def df_to_excel_bytes(df: pd.DataFrame) -> BytesIO:
    output = BytesIO()
    # Keep same columns and order
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output


# =========================
# CARD VIEW RENDERING
# =========================
def show_record_card(record: dict, index: int):
    """
    Show one row as a 'card' with vertical key: value pairs.
    """
    with st.container():
        st.markdown(
            """
            <style>
            .record-card {
                border-radius: 12px;
                border: 1px solid #e0e0e0;
                padding: 12px 16px;
                margin-bottom: 12px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.04);
                background-color: #fdfdfd;
            }
            .record-title {
                font-weight: 600;
                margin-bottom: 6px;
                font-size: 15px;
            }
            .record-field {
                font-size: 13px;
                margin-bottom: 2px;
            }
            .record-label {
                font-weight: 500;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # You can choose any key as title – trying New Meter or CA No if exists
        title_parts = []
        for key_candidate in ["New Meter", "CA No", "Service Order(SO) Number", "Notification No."]:
            if key_candidate in record and pd.notna(record[key_candidate]):
                title_parts.append(f"{key_candidate}: {record[key_candidate]}")
        title_text = " | ".join(title_parts) if title_parts else f"Record #{index + 1}"

        st.markdown('<div class="record-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="record-title">{title_text}</div>', unsafe_allow_html=True)

        # Show all fields in vertical mode
        for key, value in record.items():
            val_str = "" if pd.isna(value) else str(value)
            st.markdown(
                f'<div class="record-field"><span class="record-label">{key}:</span> {val_str}</div>',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)


# =========================
# MAIN APP
# =========================
def main():
    st.set_page_config(page_title="New Commissioning Search", layout="wide")
    st.title("🔍 New Commissioning Data Search (GitHub Excel)")

    st.write(
        "This app reads the **New Commissioning** Excel directly from GitHub "
        "and lets you search by any column (Meter No, CA No, Notification No, etc.)."
    )

    # 1) LOAD DATA
    with st.spinner("Loading Excel from GitHub..."):
        try:
            df = load_excel_from_github(GITHUB_EXCEL_URL)
        except Exception as e:
            st.error(f"Error loading Excel from GitHub: {e}")
            return

    st.success(f"Loaded {len(df)} rows and {len(df.columns)} columns from GitHub.")

    # 2) SEARCH CONTROLS
    st.subheader("Search")

    col1, col2 = st.columns([1, 2])

    with col1:
        search_column = st.selectbox(
            "Select column to search in",
            options=df.columns.tolist(),
            index=df.columns.get_loc("New Meter") if "New Meter" in df.columns else 0,
        )

    with col2:
        query = st.text_input(
            "Enter search value (full or partial)",
            placeholder="e.g. 123123 (meter no), or CA number, or notification no...",
        )

    match_type = st.radio(
        "Match type",
        ["Contains (recommended)", "Exact match"],
        horizontal=True,
        index=0,
    )

    # 3) FILTER DATA
    filtered_df = pd.DataFrame()

    if query.strip():
        # Convert selected column to string for comparison
        col_data = df[search_column].astype(str)

        if match_type == "Contains (recommended)":
            mask = col_data.str.contains(query.strip(), case=False, na=False)
        else:  # Exact match
            mask = col_data.str.strip().str.lower() == query.strip().lower()

        filtered_df = df[mask]

        st.info(f"Found **{len(filtered_df)}** matching row(s).")

        if filtered_df.empty:
            st.warning("No data found for your search.")
        else:
            st.subheader("Result – Card View (Vertical)")
            for idx, row in filtered_df.iterrows():
                show_record_card(row.to_dict(), index=idx)

            # 4) DOWNLOAD EXCEL (SAME FORMAT AS GITHUB EXCEL)
            st.subheader("Download filtered data as Excel")

            excel_bytes = df_to_excel_bytes(filtered_df)

            st.download_button(
                label="⬇️ Download filtered Excel",
                data=excel_bytes,
                file_name="new_commissioning_filtered.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                help=(
                    "Download only the matching rows. "
                    "Columns and headers remain same as original GitHub Excel."
                ),
            )

    else:
        st.info("Enter a search value above to see results.")

    # OPTIONAL: Download full original data as Excel (same as GitHub file)
    with st.expander("Download full original Excel (all rows)"):
        full_bytes = df_to_excel_bytes(df)
        st.download_button(
            label="⬇️ Download full Excel (same as GitHub)",
            data=full_bytes,
            file_name="new_commissioning_full.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )


if __name__ == "__main__":
    main()
