import streamlit as st
import pandas as pd
import datetime
import time

import funcs as fns
import google_utils as gu
import assign_schedule as assign


MLATML_FOLDER_ID = st.secrets["mlatml_folder_id"]  # Folder ID for ML@ML
MLATML_SLIDES_FOLDER_ID = st.secrets[
    "mlatml_slides_folder_id"
]  # Folder ID for ML@ML Slides

SLIDES_TEMPLATE_ID = st.secrets["slides_template_id"]  # Template file ID for slides
ZOOM_LINK = st.secrets["zoom_link"]  # Zoom link for the meeting


@st.cache_data(ttl=300)
def load_schedule_data():
    return gu.get_schedule_df()


@st.cache_data(ttl=300)
def load_participants_data():
    return gu.get_participants_list()


@st.cache_data(ttl=300)
def load_materials_data():
    ws = gu.get_sheet("Materials")
    all_records = ws.get_all_records()
    return all_records


@st.cache_data(ttl=300)
def load_slides_data(selected_date_str):
    existing_slide = gu.find_slide(selected_date_str)
    return existing_slide


def refresh_main():
    load_schedule_data.clear()
    load_participants_data.clear()
    st.rerun()


def refresh_detail():
    load_schedule_data.clear()
    load_materials_data.clear()
    st.rerun()


# ----- PAGE CONFIG -----
st.set_page_config(
    page_title="QC@ML",
    page_icon="logo.png",
    initial_sidebar_state="collapsed",
    layout="centered",
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
    unsafe_allow_html=True,
)

# ----- TOP HEADER (LOGO + TITLE) -----
top_container = st.container()
with top_container:
    col1, col2 = st.columns([1, 6])
    with col1:
        st.image("logo.png", width=60)
    with col2:
        st.title("QC@ML")

st.write("---")

# ----- GET QUERY PARAMS -----
# selected_date_str = st.query_params.get("date", "")
params = st.query_params

########################################
# DETAIL VIEW
########################################


def redirect_to_schedule():
    with st.spinner("Redirecting back to the schedule..."):
        time.sleep(3)
        st.query_params.clear()
        st.rerun()


if "confirmation" in params:
    date_str = params.get("date", [""])
    role = params.get("role", [""]).replace("_", " ")  # e.g., "Presenter_1"
    encrypted_name = params.get("name", [""])  # e.g., "[P] Alessandro"
    try:
        pending_name = fns.decrypt_name(encrypted_name)
    except Exception as e:
        st.error("Failed to decode the name parameter.")
        st.stop()

    if not date_str or not role or not pending_name:
        st.error("Missing required parameters.")
        st.stop()

    # Convert the provided date string to a date object.
    try:
        meeting_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception as e:
        st.error("Invalid date format.")
        st.stop()

    # check that the name in the date starts with [P], otherwise, say that the form has been used already and redirect to the schedule
    # Load the schedule DataFrame.
    with st.spinner("Loading data. Please wait..."):
        df = gu.get_schedule_df()
        row_indices = df.index[df["Date"] == meeting_date].tolist()
        if not row_indices:
            st.error("No meeting scheduled for this date.")
            st.stop()
        row_idx = row_indices[0]

    if not any(
        df.at[row_idx, role].startswith("[P]")
        for role in ["Presenter 1", "Presenter 2"]
    ):
        st.error(
            "This form has already been used, please contact the organizer if you need to change your response."
        )
        redirect_to_schedule()

    st.subheader("Schedule form 📝")
    st.write(
        f"Dear **{''.join(pending_name.split()[1:])}**, you have been randomly scheduled to present for 20 minutes on **{meeting_date.strftime('%B %d, %Y')}** as **{role}**. If you either are unable to present on this date **or** would like to have 40 minutes instead, choose the 'Reschedule' option."
    )
    st.write("**Please select one of the options below:**")

    # Display option buttons in three columns.
    confirm_clicked = st.button("Confirm ✅", key="confirm")
    reschedule_clicked = st.button("Reschedule 🔁", key="reschedule")
    dont_want_clicked = st.button("Decline ❌", key="dont_want")

    # Determine which button was clicked.
    clicked_option = None
    if confirm_clicked:
        clicked_option = "Confirm"
    elif reschedule_clicked:
        clicked_option = "Reschedule"
    elif dont_want_clicked:
        clicked_option = "Decline"

    # Display what the user clicked.
    if clicked_option:
        st.info(f"You clicked: {clicked_option}")

    # Use a placeholder to display results/messages.
    response_placeholder = st.empty()

    if clicked_option == "Confirm":
        # Confirm: remove the "[P]" marker.
        current_value = df.at[row_idx, role]
        if current_value.startswith("[P]"):
            new_value = current_value.replace("[P]", "").strip()
        else:
            new_value = current_value
        df.at[row_idx, role] = new_value
        gu.save_schedule_df(df)
        response_placeholder.success("Thank you, your presentation has been confirmed!")
        redirect_to_schedule()

    elif clicked_option == "Reschedule":
        current_value = df.at[row_idx, role]
        if current_value.startswith("[P]"):
            new_value = current_value.replace("[P]", "[R]")
        else:
            new_value = current_value
        df.at[row_idx, role] = new_value
        gu.save_schedule_df(df)
        response_placeholder.success("Please contact us for rescheduling.")
        redirect_to_schedule()

    elif clicked_option == "Decline":
        # Don't want: use a form inside an expander to keep it visible after submission.
        df.at[row_idx, role] = "EMPTY"
        gu.save_schedule_df(df)
        response_placeholder.success("Your response has been recorded.")
        redirect_to_schedule()

elif "date" in params:
    try:
        selected_date_str = params.get("date", [""])
        selected_date = datetime.datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    except ValueError:
        st.error("Invalid date in URL. Please go back to the schedule.")
        st.stop()

    st.title(f"Quantum Subgroup Meeting")
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
        datestr = datetime.datetime.strptime(selected_date_str, "%Y-%m-%d").strftime(
            "%b %d %Y"
        )
        st.write(f"### Schedule for {datestr}")
        for col in role_cols:
            if row[col]:
                ps.append(row[col])
                st.write(f"##### 🚀 &nbsp; **{col}**: {row[col]}")

    existing_slide = load_slides_data(selected_date_str)
    st.write(f" ")

    # col1, col2, _, _ = st.columns(4)
    col1, col2 = st.columns([0.2, 1])

    with col1:
        if existing_slide:
            # st.markdown(f"##### [View Slides]({existing_slide['Presentation_Link']})")
            st.link_button("View Slides", existing_slide["Presentation_Link"])
        else:
            if st.button("Make Slides", key=f"main_slides_{idx}"):
                try:
                    from googleapiclient.errors import HttpError

                    drive_service = gu.get_drive_service()
                    file = (
                        drive_service.files().get(fileId=SLIDES_TEMPLATE_ID).execute()
                    )
                except HttpError as e:
                    st.error(f"Template file not found or access denied: {e}")

                presentation_id, presentation_link = gu.generate_presentation(
                    selected_date_str,
                    ps[0],
                    ps[1],
                    SLIDES_TEMPLATE_ID,
                    folder_id=MLATML_SLIDES_FOLDER_ID,
                )
                if presentation_id and presentation_link:
                    # Save slide entry using date, presentation ID, and link
                    gu.add_slide_entry(
                        selected_date_str, presentation_id, presentation_link
                    )
                    st.success("Slides generated successfully.")
                    load_slides_data.clear()
                    st.rerun()

    with col2:
        st.link_button("Join Zoom", ZOOM_LINK)

    # 5. Materials / Documents Section (persisted store via JSON)
    st.write("---")
    st.subheader("Documents 📚")

    ws = gu.get_sheet("Materials")
    all_records = load_materials_data()

    target_rows = []  # list of tuples (row_index, material_record)
    for idx, record in enumerate(
        all_records, start=2
    ):  # start=2 to account for header row
        # Assuming date is stored as a string in the same format as selected_date_str
        if str(record.get("Date")) == selected_date_str:
            target_rows.append((idx, record))

    # Display materials for the selected date
    if target_rows:
        for indx, (row_idx, mat) in enumerate(target_rows):
            st.write(f"##### **{indx+1}. {mat['Title']}**")
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

    # st.write("---")
    # st.subheader("Add New Document")
    with st.expander("Add New Document"):
        # Input fields for new document
        new_title = st.text_input("Document Title or Link:")
        new_description = st.text_area(
            "Description (optional):"
        )  # New description input
        pdf_file = st.file_uploader("Upload a PDF (optional):", type=["pdf"])

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
                    _, drive_link = gu.upload_file_to_drive(
                        pdf_name,
                        pdf_bytes,
                        mime_type,
                        parent_folder_id=MLATML_FOLDER_ID,
                    )

                # Pass the description to add_material
                gu.add_material(
                    selected_date_str,
                    new_title.strip(),
                    new_description.strip(),  # Pass the description here
                    pdf_name,
                    drive_link,
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

    st.title("Weekly Schedule :calendar:")

    df = df_full.copy()

    schedule_placeholder = st.container()

    st.markdown(
        """**Status:** ⚫ Accepted -- 🔵 Pending confirmation -- 🔴 Cancelled"""
    )
    col1, col2 = st.columns([0.3, 1])  # Adjust ratios as needed
    with col1:
        # Hide past dates if desired
        hide_past = st.checkbox("Hide past dates", value=True)
        today = datetime.date.today()
        if hide_past:
            df = df[df["Date"] >= today]
        else:
            df = df_full.copy()

    with col2:
        # Refresh button placed side by side with the checkbox
        if st.button("Refresh Data"):
            refresh_main()

    with schedule_placeholder:
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
                st.info(
                    "You are in admin mode. Feel free to edit and save the schedule."
                )

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
                        ),
                    },
                    hide_index=True,
                    key="schedule_editor",
                )
                col1, col2, col3, col4 = st.columns(
                    [0.2, 0.15, 0.32, 0.33]
                )  # Adjust ratios as needed


                message_placeholder = st.empty()

                with col1:
                    if st.button("Save Changes"):

                        updated_df = df_full.copy()

                        if "Date" in edited_df.columns:
                            edited_df["Date"] = pd.to_datetime(
                                edited_df["Date"], errors="coerce"
                            ).dt.date
                        updated_df["Date"] = pd.to_datetime(
                            updated_df["Date"], errors="coerce"
                        ).dt.date

                        for idx, row in edited_df.iterrows():
                            mask = updated_df["Date"] == row["Date"]
                            if not mask.any():
                                updated_df.loc[len(updated_df)] = row
                            else:
                                updated_df.loc[mask, updated_df.columns] = row.values

                        gu.save_schedule_df(updated_df)
                        message_placeholder.success("Schedule updated and saved!")

                with col2:
                    if st.button("Add Row"):
                        # Use a copy of df_full for modification
                        updated_df = df_full.copy()
                        if not updated_df.empty and "Date" in updated_df.columns:
                            last_date = updated_df["Date"].max()
                        else:
                            last_date = datetime.date.today()
                        next_wed = fns.get_next_wednesday(last_date)

                        # Create a new row with default values using updated_df's columns
                        new_row = {}
                        for col in updated_df.columns:
                            if col == "Date":
                                new_row[col] = next_wed
                            elif "Presenter" in col:
                                new_row[col] = "EMPTY"
                            else:
                                new_row[col] = ""
                        new_row_df = pd.DataFrame([new_row])

                        # Append the new row to our copy
                        updated_df = pd.concat(
                            [updated_df, new_row_df], ignore_index=True
                        )
                        if "Date" in updated_df.columns:
                            updated_df["Date"] = updated_df["Date"].astype(str)
                        gu.save_schedule_df(updated_df)
                        refresh_main()
                        message_placeholder.success(
                            f"Added new row for date: {next_wed}"
                        )
                        st.rerun()

                with col3:
                    if st.button("Send Confirmation Emails"):
                        result = gu.send_confirmation_emails()
                        # st.info(result)
                        message_placeholder.info(result)

                with col4:
                    if st.button("Fill empty slots"): 
                        filled_df = assign.fill_empty_slots(seed=0) 
                        gu.save_schedule_df(filled_df)
                        refresh_main()
                        st.rerun()

                # ---- Delete Row Option ----
                if not df.empty:
                    # Build a dictionary mapping each row label to its original index (do not reset the index)
                    row_dict = {
                        f"Date: {row['Date']}, Presenters: {row['Presenter 1']} & {row['Presenter 2']}": idx
                        for idx, row in df.iterrows()
                    }

                    col_del1, col_del2 = st.columns(
                        [1, 0.2], vertical_alignment="bottom"
                    )

                    with col_del1:
                        selected_label = st.selectbox(
                            "Select a row to delete:", options=list(row_dict.keys())
                        )

                    with col_del2:
                        if st.button("Delete"):
                            selected_index = row_dict[selected_label]
                            # Work on a copy of the full schedule, preserving all rows
                            updated_df = df_full.copy()
                            # Remove the row using the original index
                            updated_df = updated_df.drop(index=selected_index)
                            if "Date" in updated_df.columns:
                                updated_df["Date"] = updated_df["Date"].astype(str)
                            gu.save_schedule_df(updated_df)
                            refresh_main()
                            message_placeholder.success(
                                f"Deleted row at index {selected_index}."
                            )
                            st.rerun()

            else:
                # READ-ONLY for non-admin
                # st.dataframe(df, use_container_width=True)

                # 1) Create a column with just the link (relative query param)
                df["DetailsLink"] = df["Date"].apply(
                    lambda d: f"?date={d.strftime('%Y-%m-%d')}"
                )

                # Apply styling to Presenter columns to highlight "EMPTY" cells
                style_cols = [
                    col for col in ["Presenter 1", "Presenter 2"] if col in df.columns
                ]
                styled_df = df.style.map(fns.highlight_empty, subset=style_cols).map(
                    fns.highlight_random, subset=style_cols
                )

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
                        ),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

    # ----- PARTICIPANT USAGE SCORES -----
    st.write("---")
    st.subheader("Participants :robot_face:")

    try:
        valid_participants = load_participants_data()
    except Exception as e:
        st.error(f"Error loading participants: {e}")
        st.stop()

    participants_usage = {p["Name"]: {"presenter_count": 0} for p in valid_participants}

    # Calculate cutoff date: 5 months ago from today (same as assign_roles)
    today = datetime.date.today()
    five_months_ago = today - datetime.timedelta(days=150)  # ~5 months (150 days)

    for col in ["Presenter 1", "Presenter 2"]:
        if col in df_full.columns:
            for idx, row in df_full.iterrows():
                presentation_date = row["Date"]
                person = row[col].strip()
                if not person or person not in participants_usage:
                    continue
                # Only count presentations within the last 5 months
                if presentation_date >= five_months_ago:
                    participants_usage[person]["presenter_count"] += 1

    records = []
    for participant in valid_participants:
        name = participant["Name"]
        usage_dict = participants_usage.get(name, {"presenter_count": 0})
        weighted_usage = (
            usage_dict["presenter_count"] * 4
        )  # Add journal points if needed
        records.append(
            {
                "Name": name,
                "Presentations": usage_dict["presenter_count"],
                "Points": weighted_usage,
            }
        )

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
            df_scores = df_scores[
                df_scores["Name"].str.contains(search_name, case=False, na=False)
            ]

        df_scores.drop(columns=["Points", "Presentations"], inplace=True)

        styled_df = df_scores.style.map(color_for_score, subset=["Score"]).format(
            {"Score": "{:.2f}"}
        )

        if not df_scores.empty:
            column_config = {
                "Name": st.column_config.TextColumn("Name", width="large"),  # Increase first column width
                "Score": st.column_config.NumberColumn("Score (over past 5 months)", width="medium")  # Keep second column smaller
            }
            st.dataframe(styled_df, use_container_width=True, column_config=column_config)
        else:
            st.info("No matching participants.")
    else:
        st.info("No participants found in the schedule.")

    if admin_mode:
        st.subheader("Manage Participants")
        try:
            participants = load_participants_data()
        except Exception as e:
            st.error(f"Error loading participants: {e}")
            st.stop()

        col1, col2 = st.columns([1, 0.2], vertical_alignment="bottom")
        pmessage_placeholder = st.empty()
        with col1:
            new_participant = st.text_input(
                "Add participant:", key="add_input", placeholder="Name"
            )
            new_participant_email = st.text_input(
                "Email:",
                key="email_input",
                placeholder="Email",
                label_visibility="collapsed",
            )
        with col2:
            if st.button("Add"):
                if new_participant and new_participant_email:
                    if not any(p["Name"] == new_participant for p in participants):
                        participants.append(
                            {"Name": new_participant, "Email": new_participant_email}
                        )
                        gu.save_participants_list(participants)
                        refresh_main()
                        st.rerun()
                    else:
                        pmessage_placeholder.warning(
                            f"{new_participant} is already in the list."
                        )
                else:
                    pmessage_placeholder.warning(
                        "Please enter a name and email to add."
                    )

        if participants:
            col1, col2 = st.columns([1, 0.2], vertical_alignment="bottom")
            participant_names = [p["Name"] for p in participants]
            with col1:
                remove_participant = st.selectbox(
                    "Remove participant:",
                    options=participant_names,
                    key="remove_select",
                )
            with col2:
                if st.button("Remove"):
                    participants = [
                        p for p in participants if p["Name"] != remove_participant
                    ]
                    gu.save_participants_list(participants)
                    refresh_main()
                    st.rerun()
        else:
            st.info("No participants available to remove.")

    # put legend for colors of score
    st.markdown("""**Activity:** 🟥 Low -- 🟨  Avg. -- 🟩 High""")
