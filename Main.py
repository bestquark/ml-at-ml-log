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
    initial_sidebar_state="collapsed",
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

########################################
# UTILITY FUNCTIONS FOR MATERIALS
########################################
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

########################################
# DETAIL VIEW
########################################
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
    role_cols = ["Journal 1", "Journal 2", "Presenter 1", "Presenter 2"]
    role_cols = [col for col in role_cols if col in day_df.columns]

    for idx, row in day_df.iterrows():
        st.write("### Schedule")
        st.write(f"**Date:** {row['Date']}")
        for col in role_cols:
            if row[col]:
                st.write(f"- **{col}**: {row[col]}")

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
        if not new_title.strip():
            st.warning("Please enter a valid document title/link.")
        else:
            material_entry = {"title": new_title.strip()}
            if pdf_file is not None:
                # Convert PDF bytes to base64
                pdf_bytes = pdf_file.read()
                b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
                material_entry["pdf_name"] = pdf_file.name
                material_entry["pdf_data_b64"] = b64_pdf
            # Append to the date-specific list
            materials_data.append(material_entry)
            save_materials_data(st.session_state["materials_data"])
            st.success("Material added successfully.")
            st.rerun()

    st.write("---")
    # 6. “Back to Schedule” button: clear 'date' query param
    if st.button("Back to Schedule"):
        st.query_params.clear()  # Removes all query params
        st.rerun()

########################################
# MAIN SCHEDULE VIEW
########################################
else:
    st.title("Weekly Schedule")

    # For demonstration, let's have a simple 'admin' text input in the sidebar
    admin_mode = False
    admin_password = st.sidebar.text_input("Admin password:", type="password")
    if admin_password == "1234":
        admin_mode = True

    # Load schedule CSV
    try:
        df_full = pd.read_csv("schedule.csv")
    except FileNotFoundError:
        st.error("Schedule CSV not found! Please run 'assign_schedule.py' first.")
        st.stop()

    df_full.fillna("", inplace=True)
    # Convert Date column if present
    if "Date" in df_full.columns:
        df_full["Date"] = pd.to_datetime(df_full["Date"], errors="coerce").dt.date
    else:
        st.warning("No 'Date' column found in CSV.")
        st.stop()

    # Create a working copy
    df = df_full.copy()

    # Hide past dates if desired
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

    # Show a read-only or editable schedule
    if df.empty:
        st.write("No matching rows.")
    else:
        if admin_mode:
            # EDITABLE for admin
            st.info("You are in admin mode. Feel free to edit and save the schedule.")
            edited_df = st.data_editor(
                df,
                num_rows="fixed",
                use_container_width=True,
                column_config={
                    "Date": st.column_config.DateColumn("Date"),
                    "DetailsLink": st.column_config.LinkColumn(
                        label="Info",
                        help="Click to view details for this date",
                        display_text="See Details",
                        # If you need validation, set validate="^\\?date=.*$" etc.
                    )
                },
                hide_index=True,
                key="schedule_editor",
            )

            if st.button("Save changes"):
                # Convert date column back to string for CSV
                if "Date" in edited_df.columns:
                    edited_df["Date"] = edited_df["Date"].astype(str)
                edited_df.to_csv("schedule.csv", index=False)
                st.success("Schedule updated and saved to 'schedule.csv'!")
        else:
            # READ-ONLY for non-admin
            st.write("You are **not** in admin mode, schedule is read-only.")
            # st.dataframe(df, use_container_width=True)

            # 1) Create a column with just the link (relative query param)
            df["DetailsLink"] = df["Date"].apply(lambda d: f"?date={d.strftime('%Y-%m-%d')}")

            # 2) Show the DataFrame with LinkColumn
            st.dataframe(
                df,
                column_config={
                    "Date": st.column_config.DateColumn("Date"),
                    "DetailsLink": st.column_config.LinkColumn(
                        label="Info",
                        help="Click to view details for this date",
                        display_text="See Details",
                        # If you need validation, set validate="^\\?date=.*$" etc.
                    )
                },
                hide_index=True,
                use_container_width=True,
            )


    # ----- PARTICIPANT USAGE SCORES -----
    st.write("---")
    st.subheader("Participants")

    # Weighted usage for each participant (4 points/presentation, 1 point/journal)
    participants_usage = {}
    for col in ["Presenter 1", "Presenter 2", "Journal 1", "Journal 2"]:
        if col in df_full.columns:
            for person in df_full[col]:
                if not person:
                    continue
                if person not in participants_usage:
                    participants_usage[person] = {"presenter_count": 0, "journal_count": 0}
                if "Presenter" in col:
                    participants_usage[person]["presenter_count"] += 1
                else:
                    participants_usage[person]["journal_count"] += 1

    records = []
    for person, usage_dict in participants_usage.items():
        weighted_usage = usage_dict["presenter_count"] * 4 + usage_dict["journal_count"]
        records.append({
            "Name": person,
            "Presentations": usage_dict["presenter_count"],
            "Journals": usage_dict["journal_count"],
            "Points": weighted_usage,
        })

    df_scores = pd.DataFrame(records)

    if not df_scores.empty:
        

        min_usage = df_scores["Points"].min()
        max_usage = df_scores["Points"].max()

        def calc_normalized_score(x):
            if max_usage == min_usage:
                return 0.0
            return 2 * ((x - min_usage) / (max_usage - min_usage)) - 1

        df_scores["Score"] = df_scores["Points"].apply(calc_normalized_score).round(2)

        def color_for_score(val):
            if val < -0.5:
                return "background-color: red"
            elif val > 0.5:
                return "background-color: green"
            else:
                return "background-color: yellow"

        df_scores.sort_values("Score", ascending=False, inplace=True)

        if search_name.strip():
            df_scores = df_scores[df_scores["Name"].str.contains(search_name, case=False, na=False)]

        styled_df = (
            df_scores.style
            .applymap(color_for_score, subset=["Score"])
            .format({"Score": "{:.2f}"})
        )

        if not df_scores.empty:
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.info("No matching participants.")
    else:
        st.info("No participants found in the schedule.")