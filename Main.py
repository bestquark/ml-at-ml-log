import streamlit as st
import pandas as pd
import datetime
import base64
import json
import os

import functions as fns
import gsheet_utils as gs

@st.cache_data(ttl=300)  # Cache for 5 minutes by default
def load_schedule_data():
    return gs.get_schedule_df()

@st.cache_data(ttl=300)
def load_participants_data():
    return gs.get_participants_list()

@st.cache_data(ttl=300)
def load_materials_data():
    ws = gs.get_sheet("Materials")
    all_records = ws.get_all_records()  
    return all_records

@st.cache_data(ttl=300)
def load_slides_data(selected_date_str):
    existing_slide = gs.find_slide(selected_date_str)
    return existing_slide

def refresh_main():
    # Clear cached data to force fresh reads on next call
    load_schedule_data.clear()
    load_participants_data.clear()
    st.rerun()

def refresh_detail():
    # Clear cached data to force fresh reads on next call
    load_schedule_data.clear()
    load_materials_data.clear()
    st.rerun()
    
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
# DATA_FILE = "materials_data.json"

# def load_materials_data():
#     """Load the materials from a JSON file, or return an empty dict if it doesn't exist."""
#     if os.path.exists(DATA_FILE):
#         with open(DATA_FILE, "r", encoding="utf-8") as f:
#             return json.load(f)
#     else:
#         return {}

# def save_materials_data(data):
#     """Write the entire materials structure to JSON."""
#     with open(DATA_FILE, "w", encoding="utf-8") as f:
#         json.dump(data, f, indent=2)

########################################
# DETAIL VIEW
########################################

SLIDES_TEMPLATE_ID="1XE_EB95lL4YwN1E7J6BgXpGzkTSpyTV021Fexqns4dw"
MLATML_SLIDES_FOLDER_ID="13My4DkbVC_LdHt5X91Od4MWtvo8X5BnG"
 
if selected_date_str:
    # 1. Convert to date object if possible
    try:
        selected_date = datetime.datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    except ValueError:
        st.error("Invalid date in URL. Please go back to the schedule.")
        st.stop()

    st.title(f"ML Subgroup Meeting")
    # st.title("")

    try:
        df = load_schedule_data()
    except FileNotFoundError:
        st.error("Schedule not found!")
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
    ps = []
    for idx, row in day_df.iterrows():
        st.write(f"### Schedule {selected_date_str}")
        for col in role_cols:
            if row[col]:
                ps.append(row[col])
                st.write(f"- **{col}**: {row[col]}")

    existing_slide = load_slides_data(selected_date_str)
    # st.write(f"{existing_slide}")

    if existing_slide:
        st.markdown(f"##### [View Slides]({existing_slide['Presentation_Link']})")
    else:
        if st.button("Generate slides", key=f"main_slides_{idx}"):
            try:
                from googleapiclient.errors import HttpError
                drive_service = gs.get_drive_service()
                file = drive_service.files().get(fileId=SLIDES_TEMPLATE_ID).execute()
            except HttpError as e:
                st.error(f"Template file not found or access denied: {e}")

            presentation_id, presentation_link = gs.generate_presentation(
                selected_date_str, ps[0], ps[1], SLIDES_TEMPLATE_ID, folder_id=MLATML_SLIDES_FOLDER_ID
            )
            if presentation_id and presentation_link:
                # Save slide entry using date, presentation ID, and link
                gs.add_slide_entry(selected_date_str, presentation_id, presentation_link)
                st.success("Slides generated successfully.")
                load_slides_data.clear()  
                st.rerun()

    # 5. Materials / Documents Section (persisted store via JSON)
    st.write("---")
    st.subheader("Documents")

    ws = gs.get_sheet("Materials")
    all_records = load_materials_data()

    target_rows = []  # list of tuples (row_index, material_record)
    for idx, record in enumerate(all_records, start=2):  # start=2 to account for header row
        # Assuming date is stored as a string in the same format as selected_date_str
        if str(record.get("Date")) == selected_date_str:
            target_rows.append((idx, record))

    # Display materials for the selected date
    if target_rows:
        for row_idx, mat in target_rows:
            st.write(f"##### **{mat['Title']}**")
            if mat.get("Description"):
                st.write(f"Description: {mat['Description']}")

            # Display PDF link if available
            if mat.get("PDF_Link"):
                drive_link = mat["PDF_Link"]
                href = f'<a href="{drive_link}" target="_blank">View PDF</a>'
                st.markdown(href, unsafe_allow_html=True)

            # Remove button for this material
            if st.button(f"Remove document", key=f"remove_{row_idx}"):
                ws.delete_rows(row_idx)
                refresh_detail()  # Rerun to refresh the list after deletion
                st.success(f"Removed material: {mat['Title']}")    
                st.rerun()  # Rerun to refresh the list after deletion
    else:
        st.write("No documents yet.")

    st.write("---")
    st.subheader("Add New Document")
    # Input fields for new document
    new_title = st.text_input("Document Title or Link:")
    new_description = st.text_area("Description (optional):")  # New description input
    pdf_file = st.file_uploader("Upload a PDF (optional):", type=["pdf"])

    MLATML_FOLDER_ID = "1EWEfieDpRW1jMSDkcwLxFc9EWAAyKeT1" 

    if st.button("Upload"):
        if not new_title.strip():
            st.warning("Please enter a valid document title/link.")
        else:
            pdf_name = ""
            drive_link = ""
            if pdf_file is not None:
                pdf_bytes = pdf_file.read()
                pdf_name = pdf_file.name
                mime_type = "application/pdf"
                _, drive_link = gs.upload_file_to_drive(pdf_name, pdf_bytes, mime_type, parent_folder_id=MLATML_FOLDER_ID)
            
            # Pass the description to add_material
            gs.add_material(
                selected_date_str,
                new_title.strip(),
                new_description.strip(),  # Pass the description here
                pdf_name,
                drive_link
            )

            refresh_detail()  # Rerun to refresh the list after addition
            st.success("Material added successfully.")
            st.rerun()

    st.write("---")
    # "Back to Schedule" button
    if st.button("Back to Schedule"):
        st.query_params.clear()
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
        df_full = load_schedule_data()
    except FileNotFoundError:
        st.error("Schedule not found!")
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
    # hide_past = st.checkbox("Hide past dates", value=True)
    # today = datetime.date.today()
    # if hide_past:
    #     df = df[df["Date"] >= today]

    col1, col2 = st.columns([2, 1])  # Adjust ratios as needed
    with col1:
    # Hide past dates if desired
        hide_past = st.checkbox("Hide past dates", value=True)
        today = datetime.date.today()
        if hide_past:
            df = df[df["Date"] >= today]

    with col2:
        # Refresh button placed side by side with the checkbox
        if st.button("Refresh Data"):
            refresh_main()

    # hide_past = st.checkbox("Hide past dates", value=True)
    # today = datetime.date.today()
    # if hide_past:
    #     df = df[df["Date"] >= today]

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
                gs.save_schedule_df(df)
                refresh_main()
                st.success(f"Added new row for date: {next_wed}")
                st.rerun()
            
            # ---- Delete Row Option ----
             # Provide a dropdown or selectbox to choose a row to delete
            if not df.empty:
                # Reset index to ensure proper indexing
                df = df.reset_index(drop=True)

                # Create a dictionary mapping each row label to its index
                row_dict = {
                    f"Date: {row['Date']}, Presenters: {row['Presenter 1']} & {row['Presenter 2']}": idx
                    for idx, row in df.iterrows()
                }

                # Create a selectbox with labels
                selected_label = st.selectbox("Select a row to delete:", options=list(row_dict.keys()))

                if st.button("Delete Selected Row"):
                    # Get the corresponding index for the selected label
                    selected_index = row_dict[selected_label]

                    # Drop the row and reset the index
                    df = df.drop(index=selected_index).reset_index(drop=True)

                    # Convert date column back to string if necessary
                    if "Date" in df.columns:
                        df["Date"] = df["Date"].astype(str)

                    gs.save_schedule_df(df)
                    refresh_main()   
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
                gs.save_schedule_df(edited_df)
                # refresh_main()
                st.success("Schedule updated and saved!")
        else:
            # READ-ONLY for non-admin
            st.write("You are **not** in admin mode, schedule is read-only.")
            # st.dataframe(df, use_container_width=True)

            # 1) Create a column with just the link (relative query param)
            df["DetailsLink"] = df["Date"].apply(lambda d: f"?date={d.strftime('%Y-%m-%d')}")

            # Apply styling to Presenter columns to highlight "EMPTY" cells
            style_cols = [col for col in ["Presenter 1", "Presenter 2"] if col in df.columns]
            styled_df = df.style.map(fns.highlight_empty, subset=style_cols)

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
    # try:
    #     with open("participants.txt", "r") as f:
    #         valid_participants = [line.strip() for line in f if line.strip()]
    # except FileNotFoundError:
    #     valid_participants = []
    #     st.warning("participants.txt not found. No valid participants loaded.")
    try:
        valid_participants = load_participants_data()
    except Exception as e:
        st.error(f"Error loading participants: {e}")
        st.stop()

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
        # try:
        #     with open("participants.txt", "r") as f:
        #         participants = [line.strip() for line in f if line.strip()]
        # except FileNotFoundError:
        #     participants = []
        #     st.warning("participants.txt not found. Starting with an empty list.")

        try:
            participants = load_participants_data()
        except Exception as e:
            st.error(f"Error loading participants: {e}")
            st.stop()

        # Add Participant Section
        new_participant = st.text_input("Add participant:", key="add_input")
        if st.button("Add Participant"):
            if new_participant:
                if new_participant not in participants:
                    participants.append(new_participant)
                    # with open("participants.txt", "w") as f:
                    #     f.write("\n".join(participants) + "\n")
                    gs.save_participants_list(participants)
                    st.success(f"Added participant: {new_participant}")
                    # refresh_main()
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
                    # with open("participants.txt", "w") as f:
                    #     f.write("\n".join(participants) + "\n")
                    gs.save_participants_list(participants)
                    st.success(f"Removed participant: {remove_participant}")
                    # refresh_main()
                    st.rerun()
                else:
                    st.warning(f"{remove_participant} not found in the list.")
        else:
            st.info("No participants available to remove.")
