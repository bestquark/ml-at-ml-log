import streamlit as st
import pandas as pd
import datetime
import base64
import json
import os

# ----- PAGE CONFIG -----
st.set_page_config(
    page_title="ML@ML Schedule",
    page_icon="logo.png",
    layout="centered"
)

# ----- GLOBAL STYLES -----
st.markdown(
    """
    <style>
    /* Overall font size for the app */
    html, body, [class*="css"]  {
        font-size: 15px !important; /* Adjust as desired */
    }
    /* Specifically enlarge table content if you like */
    tbody, th, td {
        font-size: 10px !important;
    }
    /* Hide the row index in st.dataframe / st.markdown tables */
    div[data-testid="stDataFrame"] .row_heading.level0 {
        display: none
    }
    div[data-testid="stDataFrame"] thead tr th:first-child {
        display: none
    }
    div[data-testid="stDataFrame"] tbody th {
        display: none
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ----- TOP HEADER (LOGO + TITLE) -----
top_container = st.container()
with top_container:
    col1, col2 = st.columns([1, 6])
    with col1:
        st.image("logo.png", width=60)
    with col2:
        st.markdown("## ML@ML")

# ----- GET QUERY PARAMS -----
selected_date_str = st.query_params.get("date", "")

# ======================== DETAIL VIEW (IF 'date' PARAM IS PROVIDED) ========================
if selected_date_str:
    # 1. Convert to date object if possible
    try:
        selected_date = datetime.datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    except ValueError:
        st.error("Invalid date in URL. Please go back to the schedule.")
        st.stop()

    st.title(f"Details for {selected_date_str}")

    # 2. Load the schedule
    try:
        df = pd.read_csv("schedule.csv")
    except FileNotFoundError:
        st.error("Schedule CSV not found! Please run 'assign_schedule.py' first.")
        st.stop()

    df.fillna("", inplace=True)

    # Convert date column properly
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df[df["Date"].notna()]
        df["Date"] = df["Date"].dt.date
    else:
        st.warning("No 'Date' column found in CSV.")
        st.stop()

    # 3. Filter to this date’s row(s)
    day_df = df[df["Date"] == selected_date]
    if day_df.empty:
        st.warning("No entries found for this date.")
        st.stop()

    # 4. Show info about presenters/journal
    #    (If renamed to "Presenter 1" etc., adjust accordingly)
    role_cols = ["Journal 1", "Journal 2", "Presenter 1", "Presenter 2"]
    role_cols = [col for col in role_cols if col in day_df.columns]

    for idx, row in day_df.iterrows():
        st.write("### Schedule")
        st.write(f"**Date:** {row['Date']}")
        for col in role_cols:
            if row[col]:
                st.write(f"- **{col}**: {row[col]}")
                
    DATA_FILE = "materials_data.json"

    def load_materials_data():
        """Load the materials from a JSON file, or return an empty dict if it doesn't exist."""
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            return {}

    def save_materials_data(data):
        """Write the entire materials structure to JSON."""
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # 5. Materials / Documents Section (persisted store via JSON)
    st.write("---")
    st.subheader("Materials / Documents")

    # 1) Load JSON into session_state if not already there
    if "materials_data" not in st.session_state:
        st.session_state["materials_data"] = load_materials_data()

    # If this date doesn't exist in the dictionary, initialize a list
    if selected_date_str not in st.session_state["materials_data"]:
        st.session_state["materials_data"][selected_date_str] = []

    materials_data = st.session_state["materials_data"][selected_date_str]

    # 3. Show existing materials
    if materials_data:
        st.write("#### Existing Materials:")
        for i, mat in enumerate(materials_data):
            st.write(f"**{i+1}. {mat['title']}**")
            
            # If there's a PDF, show a "Download PDF" link/button
            if "pdf_data_b64" in mat:
                pdf_name = mat["pdf_name"]
                pdf_b64 = mat["pdf_data_b64"]
                # Create a download link using base64
                href = f'<a href="data:application/octet-stream;base64,{pdf_b64}" download="{pdf_name}">Download PDF</a>'
                st.markdown(href, unsafe_allow_html=True)

            # Remove button
            if st.button(f"Remove #{i+1}", key=f"remove_{i}"):
                materials_data.pop(i)
                # Save updated data to JSON
                save_materials_data(st.session_state["materials_data"])
                st.success("Material removed.")
                st.rerun()
    else:
        st.write("No materials yet.")


    # 1. Input fields for Title/Description
    new_title = st.text_input("Document Title or Link:")

    # 2. Optional PDF Upload
    pdf_file = st.file_uploader("Upload a PDF (optional):", type=["pdf"])

    if st.button("Add Material"):
        # Basic validation
        if not new_title.strip():
            st.warning("Please enter a valid document title/link.")
        else:
            # Build the material dictionary
            material_entry = {
                "title": new_title.strip(),
            }
            
            if pdf_file is not None:
                # Convert PDF bytes to base64 so we can store it in session_state and JSON
                pdf_bytes = pdf_file.read()
                b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
                # Store the PDF
                material_entry["pdf_name"] = pdf_file.name
                material_entry["pdf_data_b64"] = b64_pdf
            
            # Append to the date-specific list
            materials_data.append(material_entry)

            # Save updated data to JSON
            save_materials_data(st.session_state["materials_data"])

            st.success("Material added successfully.")
            st.rerun()


    st.write("---")
    # 6. “Back to Schedule” button: clear 'date' query param
    if st.button("Back to Schedule"):
        st.query_params.clear()  # Removes all query params
        st.rerun()

# ======================== MAIN SCHEDULE VIEW (NO 'date' QUERY PARAM) ========================
else:
    st.title("Weekly Schedule")

    # Load CSV
    try:
        df_full = pd.read_csv("schedule.csv")
    except FileNotFoundError:
        st.error("Schedule CSV not found! Please run 'assign_schedule.py' first.")
        st.stop()

    df_full.fillna("", inplace=True)
    df = df_full.copy()

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df[df["Date"].notna()]
        df["Date"] = df["Date"].dt.date
    else:
        st.warning("No 'Date' column found in CSV.")
        st.stop()

    # Optional: hide past dates
    hide_past = st.checkbox("Hide past dates", value=True)
    today = datetime.date.today()
    if hide_past:
        df = df[df["Date"] >= today]

    # Search by participant name
    search_name = st.text_input("Search by participant name:")
    role_cols = ["Journal 1", "Journal 2", "Presenter 1", "Presenter 2"]
    role_cols = [c for c in role_cols if c in df.columns]

    if search_name.strip():
        mask = False
        for c in role_cols:
            mask = mask | df[c].str.contains(search_name, case=False, na=False)
        df = df[mask]

    if df.empty:
        st.write("No matching rows.")
    else:
        # We'll build an HTML table so we can embed a 'Details' link for each row
        def details_link(d):
            """Return an HTML <a> that sets ?date=YYYY-MM-DD."""
            return f'<a href="?date={d.strftime("%Y-%m-%d")}">Details</a>'

        if "Date" not in df.columns:
            st.error("No 'Date' column found after transformations.")
        else:
            # Create an HTML "Details" link for each row (no 'target', so same tab)
            def details_link(d):
                """Return an HTML <a> that sets ?date=YYYY-MM-DD."""
                return f'<a href="?date={d.strftime("%Y-%m-%d")}">Details</a>'

            df["Info"] = df["Date"].apply(details_link)
            # Convert to HTML (escape=False so <a> is clickable)
            html_table = df.to_html(index=False, escape=False)
            st.markdown(html_table, unsafe_allow_html=True)

    # ----- PARTICIPANT USAGE SCORES -----
    st.write("---")
    st.subheader("Participants")

    # 1) Count weighted usage for each participant (4 points per presentation, 1 per journal)
    participants_usage = {}
    role_columns = ["Presenter 1", "Presenter 2", "Journal 1", "Journal 2"]
    for role_col in role_columns:
        if role_col in df_full.columns:
            for person in df_full[role_col]:
                # Skip if blank
                if not person:
                    continue
                if person not in participants_usage:
                    participants_usage[person] = {
                        "presenter_count": 0,
                        "journal_count": 0
                    }
                if "Presenter" in role_col:
                    participants_usage[person]["presenter_count"] += 1
                else:
                    participants_usage[person]["journal_count"] += 1

    # 2) Convert to a list of dicts for DataFrame
    records = []
    for person, usage_dict in participants_usage.items():
        # Weighted total: 4 points per present, 1 point per journal
        weighted_usage = usage_dict["presenter_count"] * 4 + usage_dict["journal_count"]
        records.append({
            "Name": person,
            "Presentations": usage_dict["presenter_count"],
            "Journals": usage_dict["journal_count"],
            "Points": weighted_usage,
        })

    df_scores = pd.DataFrame(records)

    if not df_scores.empty:
        # 3) Min–max normalize to [-1..1] range
        min_usage = df_scores["Points"].min()
        max_usage = df_scores["Points"].max()

        def calc_normalized_score(x):
            if max_usage == min_usage:
                # Everyone has the same usage, so just return 0
                return 0.0
            return 2 * ((x - min_usage) / (max_usage - min_usage)) - 1

        df_scores["Score"] = df_scores["Points"].apply(calc_normalized_score).round(2)

        # 4) Color-coding based on Score
        def color_for_score(val):
            if val < -0.5:
                return "background-color: red"
            elif val > 0.5:
                return "background-color: green"
            else:
                return "background-color: yellow"

        # Sort by highest Score, for convenience
        df_scores.sort_values("Score", ascending=False, inplace=True)

        # 5) Display as a styled DataFrame
        styled_df = df_scores.style.applymap(color_for_score, subset=["Score"]).format({"Score": "{:.2f}"})
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("No participants found in the schedule.")
