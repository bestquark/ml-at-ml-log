import streamlit as st
import pandas as pd
import datetime
import base64
import json
import os

import functions as fns

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

    # 4. Show info about presenters
    role_cols = ["Presenter 1", "Presenter 2"]
    role_cols = [col for col in role_cols if col in day_df.columns]

    for idx, row in day_df.iterrows():
        st.write("### Schedule")
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
    pw = st.secrets["admin_password"]
    if admin_password == pw:
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
    role_cols = ["Presenter 1", "Presenter 2"]
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

            if st.button("Add New Row"):
                # Calculate next Wednesday after the last date in df
                if not df.empty and "Date" in df.columns:
                    last_date = df["Date"].max()
                else:
                    last_date = today
                next_wed = fns.get_next_wednesday(last_date)

                # Create a new row with default values
                new_row = {}
                for col in df.columns:
                    if col == "Date":
                        new_row[col] = next_wed
                    elif "Presenter" in col:
                        new_row[col] = "EMPTY"
                    else:
                        new_row[col] = ""
                # Append the new row to the dataframe
                # df = df.append(new_row, ignore_index=True)
                # st.success(f"Added new row for date: {next_wed}")
                new_row_df = pd.DataFrame([new_row])
                df = pd.concat([df, new_row_df], ignore_index=True)

                if "Date" in df.columns:
                    df["Date"] = df["Date"].astype(str)
                df.to_csv("schedule.csv", index=False)
                st.success(f"Added new row for date: {next_wed}")
                st.rerun()
            
            # ---- Delete Row Option ----
             # Provide a dropdown or selectbox to choose a row to delete
            if not df.empty:
                # Create a unique identifier for each row, e.g., using the index and date
                df = df.reset_index(drop=True)  # ensure proper indexing
                row_labels = df.apply(lambda row: f"Date: {row['Date']}, Presenters: {row['Presenter 1']} & {row['Presenter 2']}", axis=1).tolist()

                selected_row = st.selectbox("Select a row to delete:", options=row_labels)
                if st.button("Delete Selected Row"):
                    # Extract the index from the selected label
                    selected_index = int(selected_row.split(":")[0].split()[1])
                    df = df.drop(index=selected_index).reset_index(drop=True)
                    
                    # Save the updated DataFrame to CSV after deletion
                    if "Date" in df.columns:
                        df["Date"] = df["Date"].astype(str)
                    df.to_csv("schedule.csv", index=False)
                    st.success(f"Deleted row at index {selected_index}.")
                    st.rerun()
   
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

            # Apply styling to Presenter columns to highlight "EMPTY" cells
            style_cols = [col for col in ["Presenter 1", "Presenter 2"] if col in df.columns]
            styled_df = df.style.applymap(fns.highlight_empty, subset=style_cols)

            # 2) Show the DataFrame with LinkColumn
            st.dataframe(
                styled_df,
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

    # Step 1: Read valid participants from participants.txt
    try:
        with open("participants.txt", "r") as f:
            valid_participants = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        valid_participants = []
        st.warning("participants.txt not found. No valid participants loaded.")

    # Initialize usage dictionary for all valid participants with 0 counts
    participants_usage = {person: {"presenter_count": 0} for person in valid_participants}

    # Weighted usage for each participant (4 points/presentation)
    for col in ["Presenter 1", "Presenter 2"]:
        if col in df_full.columns:
            for person in df_full[col]:
                # Only consider non-empty names that are in the list of valid participants
                if not person or person not in participants_usage:
                    continue
                participants_usage[person]["presenter_count"] += 1

    # Build records list from all valid participants
    records = []
    for person in valid_participants:
        usage_dict = participants_usage.get(person, {"presenter_count": 0})
        weighted_usage = usage_dict["presenter_count"] * 4  # Add journal points if needed
        records.append({
            "Name": person,
            "Presentations": usage_dict["presenter_count"],
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

        df_scores.sort_values("Score", ascending=True, inplace=True)

        if search_name.strip():
            df_scores = df_scores[df_scores["Name"].str.contains(search_name, case=False, na=False)]

        # Remove unnecessary columns before styling
        df_scores.drop(columns=["Points", "Presentations"], inplace=True)

        styled_df = (
            df_scores.style
            .map(color_for_score, subset=["Score"])
            .format({"Score": "{:.2f}"})
        )

        if not df_scores.empty:
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.info("No matching participants.")
    else:
        st.info("No participants found in the schedule.")

    if admin_mode:
        st.subheader("Manage Participants")

        # Read current participants from file
        try:
            with open("participants.txt", "r") as f:
                participants = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            participants = []
            st.warning("participants.txt not found. Starting with an empty list.")

        # Add Participant Section
        new_participant = st.text_input("Add participant:", key="add_input")
        if st.button("Add Participant"):
            if new_participant:
                if new_participant not in participants:
                    participants.append(new_participant)
                    with open("participants.txt", "w") as f:
                        f.write("\n".join(participants) + "\n")
                    st.success(f"Added participant: {new_participant}")
                    st.rerun()
                else:
                    st.warning(f"{new_participant} is already in the list.")
            else:
                st.warning("Please enter a name to add.")

        # Remove Participant Section using a dropdown
        if participants:  # Only show dropdown if there are participants
            remove_participant = st.selectbox("Select participant to remove:", options=participants, key="remove_select")
            if st.button("Remove Participant"):
                if remove_participant in participants:
                    participants.remove(remove_participant)
                    with open("participants.txt", "w") as f:
                        f.write("\n".join(participants) + "\n")
                    st.success(f"Removed participant: {remove_participant}")
                    st.rerun()
                else:
                    st.warning(f"{remove_participant} not found in the list.")
        else:
            st.info("No participants available to remove.")
