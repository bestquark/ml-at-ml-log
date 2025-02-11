import streamlit as st
import datetime as dt
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
import base64
from email.mime.text import MIMEText
import smtplib
import time

from functions import encrypt_name

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/spreadsheets"
]

###############################################################################
# Google Sheets & Drive Utilities
###############################################################################


def get_gspread_client():
    service_account_info = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    return gspread.authorize(credentials)

def get_sheet(sheet_name):
    client = get_gspread_client()
    spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]
    return client.open_by_key(spreadsheet_id).worksheet(sheet_name)

def get_schedule_df():
    ws = get_sheet("Schedule")
    import pandas as pd
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
    return df

def save_schedule_df(df):
    ws = get_sheet("Schedule")
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.astype(str).values.tolist())

def get_participants_list():
    ws = get_sheet("Participants")
    data = ws.get_all_records()
    return [{"Name": row.get("Name"), "Email": row.get("Email", "")} for row in data if row.get("Name")]

def save_participants_list(participants):
    ws = get_sheet("Participants")
    data = [["Name", "Email"]] + [[p["Name"], p.get("Email", "")] for p in participants]
    ws.clear()
    ws.update(data)    

def get_drive_service():
    service_account_info = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    return build('drive', 'v3', credentials=credentials)

def upload_file_to_drive(file_name, file_bytes, mime_type, parent_folder_id=None):
    drive_service = get_drive_service()
    media = MediaInMemoryUpload(file_bytes, mimetype=mime_type)
    file_metadata = {'name': file_name}
    if parent_folder_id:
        file_metadata['parents'] = [parent_folder_id]
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()
    return uploaded_file.get('id'), uploaded_file.get('webViewLink')


def add_material(date_str, title, description="", pdf_name="", pdf_link=""):
    ws = get_sheet("Materials")
    new_row = [date_str, title, description, pdf_name, pdf_link]
    ws.append_row(new_row)

def delete_material_row(row_index):
    ws = get_sheet("Materials")
    ws.delete_rows(row_index)


def get_all_materials():
    ws = get_sheet("Materials")
    records = ws.get_all_records()
    materials_by_date = {}
    for record in records:
        date = record.get("Date")
        if date:
            materials_by_date.setdefault(date, [])
            material = {
                "title": record.get("Title", ""),
                "description": record.get("Description", ""),
                "pdf_name": record.get("PDF_Name", ""),
                "pdf_link": record.get("PDF_Link", ""),
            }
            materials_by_date[date].append(material)
    return materials_by_date

###############################################################################
# Slides Utilities
###############################################################################

def get_slides_service():
    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    return build('slides', 'v1', credentials=credentials)

def generate_presentation(date, presenter1, presenter2, template_id, folder_id=None):
    drive_service = get_drive_service()
    slides_service = get_slides_service()
    
    # Copy the template presentation
    copy_body = {'name': f"{date} ML Subgroup Meeting"}
    copied_file = drive_service.files().copy(fileId=template_id, body=copy_body).execute()
    presentation_id = copied_file.get('id')
    
    # Optionally move the copied file to a specific folder
    if folder_id:
        file = drive_service.files().get(fileId=presentation_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents'))
        drive_service.files().update(
            fileId=presentation_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()

    permission_body = {'type': 'anyone', 'role': 'writer'}
    drive_service.permissions().create(fileId=presentation_id, body=permission_body).execute()
    
    requests = [
        {
            'replaceAllText': {
                'containsText': {
                    'text': '{{PRESENTER1}}',
                    'matchCase': True
                },
                'replaceText': presenter1
            }
        },
        {
            'replaceAllText': {
                'containsText': {
                    'text': '{{PRESENTER2}}',
                    'matchCase': True
                },
                'replaceText': presenter2
            }
        },
        {
            'replaceAllText': {
                'containsText': {
                    'text': '{{DATE}}',
                    'matchCase': True
                },
                'replaceText': datetime.strptime(date, "%Y-%m-%d").strftime("%b %d %Y") 
            }
        }
        # Add additional requests here for other placeholders if needed.
    ]
    
    body = {'requests': requests}
    response = slides_service.presentations().batchUpdate(
        presentationId=presentation_id, body=body).execute()
    
    presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"
    return presentation_id, presentation_url

def get_all_slides():
    try:
        ws = get_sheet("Slides")
        records = ws.get_all_records()
        return records
    except Exception as e:
        st.error(f"Error fetching slides data: {e}")
        return []

def find_slide(date_str):
    slides_data = get_all_slides()
    for slide in slides_data:
        if slide.get("Date") == date_str:
            return slide
    return None

def add_slide_entry(date_str, presentation_id, presentation_link):
    try:
        ws = get_sheet("Slides")
        new_row = [date_str, presentation_id, presentation_link]
        ws.append_row(new_row)
    except Exception as e:
        st.error(f"Error adding slide entry: {e}")




###############################################################################
# CSLab (UofT) Email Utilities via SMTP
###############################################################################

def get_smtp_connection():
    smtp_server = st.secrets["smtp_server"]       # e.g. "smtp.cs.toronto.edu"
    smtp_port = st.secrets.get("smtp_port", 587)    # default to 587 for TLS
    sender_email = st.secrets["sender_email"]       # your UofT email address
    smtp_password = st.secrets["smtp_password"]     # your email password
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()  # secure the connection using TLS
    server.login(sender_email, smtp_password)
    return server

def send_email_via_smtp(smtp_conn, sender, to, subject, message_text):
    # Construct the MIMEText message
    message = MIMEText(message_text, 'html')
    message['To'] = to
    message['From'] = sender
    message['Subject'] = subject
    # Send the email using the SMTP connection
    smtp_conn.sendmail(sender, to, message.as_string())


@st.dialog("Send Confirmation Emails")
def recipients_dialog(pending_options, pending_mapping, participant_emails, app_url, organizer, sender, email_subject):
    # Show all pending recipients as a multiselect (all checked by default)
    selected = st.multiselect(
        "Select recipients to send confirmation emails to:",
        options=pending_options,
        default=pending_options,
        key="selected_recipients"
    )
    if st.button("Confirm Selection"):
        confirmations_sent = 0
        error_msgs = []
        try:
            smtp_conn = get_smtp_connection()  # Open SMTP connection inside the dialog
        except Exception as e:
            st.error(f"Error initializing SMTP connection: {e}")
            return

        # Loop over each selected recipient.
        for option in selected:
            entry = pending_mapping[option]
            to_email = participant_emails.get(entry["clean_name"], "")
            if not to_email:
                error_msgs.append(f"No email found for {entry['clean_name']}.")
                continue

            encrypted_name = encrypt_name(entry["pending_name"])
            confirmation_link = (
                f"{app_url}/?confirmation=1"
                f"&date={entry['date']}"
                f"&role={entry['role'].replace(' ', '_')}"
                f"&name={encrypted_name}"
            )
            try:
                formatted_date = dt.datetime.strptime(entry["date"], "%Y-%m-%d").strftime("%B %d, %Y")
            except Exception:
                formatted_date = entry["date"]

            with open("email_template.txt", "r") as template_file:
                email_template = template_file.read()
            email_message_text = email_template.format(
                name_presenter=entry["clean_name"],
                date=formatted_date,
                confirmation_link=confirmation_link,
                name_organizer=organizer
            )
            try:
                send_email_via_smtp(smtp_conn, sender, to_email, email_subject, email_message_text)
                confirmations_sent += 1
            except Exception as e:
                error_msgs.append(f"Error sending email to {to_email}: {e}")

        try:
            smtp_conn.quit()
        except Exception:
            pass

        st.success(f"Confirmation emails sent to {confirmations_sent} recipients.")
        if error_msgs:
            st.write("Errors encountered:")
            for err in error_msgs:
                st.write(err)

        with st.spinner("Redirecting to the dashboard..."):
            time.sleep(3)
            st.rerun()


# ----- Main Function -----
def send_confirmation_emails():
    # Load schedule and participants.
    df = get_schedule_df()  # Your function returning a DataFrame.
    participants = get_participants_list()  # Your function returning a list.
    
    # Build a mapping from participant name to email.
    participant_emails = {}
    for p in participants:
        name = p["Name"].strip()
        email = p.get("Email", "").strip()
        if email:
            participant_emails[name] = email

    # Identify pending entries (cells starting with "[P]").
    pending_entries = []
    for idx, row in df.iterrows():
        meeting_date = row.get("Date")
        meeting_date_str = (
            meeting_date.strftime("%Y-%m-%d")
            if isinstance(meeting_date, dt.date)
            else str(meeting_date)
        )
        for role in ["Presenter 1", "Presenter 2"]:
            cell_val = row.get(role, "")
            if isinstance(cell_val, str) and cell_val.strip().startswith("[P]"):
                pending_entries.append({
                    "date": meeting_date_str,
                    "role": role,
                    "pending_name": cell_val.strip(),               # e.g. "[P] Abdul"
                    "clean_name": cell_val.replace("[P]", "").strip() # e.g. "Abdul"
                })
    
    if not pending_entries:
        st.info("No pending confirmation entries found.")
        return

    # Prepare mapping for display options.
    pending_mapping = {}
    pending_options = []
    for entry in pending_entries:
        to_email = participant_emails.get(entry["clean_name"], "No Email")
        display = f"{entry['clean_name']} ({to_email}) on {entry['date']}"
        pending_options.append(display)
        pending_mapping[display] = entry

    # Save these in session state so the dialog function can access them.
    st.session_state.pending_mapping = pending_mapping
    st.session_state.pending_options = pending_options

    # Email sending details.
    sender = st.secrets["sender_email"]
    app_url = st.secrets["app_url"]
    organizer = st.secrets["organizer_name"]
    email_subject = "[Confirmation Required] ML Subgroup"

    # Call the dialog to select recipients and send emails.
    recipients_dialog(pending_options, pending_mapping, participant_emails, app_url, organizer, sender, email_subject)
    st.stop()  # Stop further execution until the dialog is closed.

# @st.dialog("Select Recipients")
# def recipients_dialog(pending_options):
#     selected = st.multiselect(
#         "Select recipients to send confirmation emails to:",
#         options=pending_options,
#         default=pending_options,
#         key="selected_recipients"
#     )
#     if st.button("Send Selected Emails"):
#         st.session_state.selected_pending_entries = selected
#         st.rerun()

# # ----- Main Function -----

# def send_confirmation_emails():
#     # Load schedule and participants.
#     df = get_schedule_df()                 # Your function returning a DataFrame.
#     participants = get_participants_list()   # Your function returning a list.
    
#     # Build a mapping from participant name to email.
#     participant_emails = {}
#     for p in participants:
#         name = p["Name"].strip()
#         email = p.get("Email", "").strip()
#         if email:
#             participant_emails[name] = email

#     # Identify pending entries (cells starting with "[P]").
#     pending_entries = []
#     for idx, row in df.iterrows():
#         meeting_date = row.get("Date")
#         meeting_date_str = (
#             meeting_date.strftime("%Y-%m-%d")
#             if isinstance(meeting_date, dt.date)
#             else str(meeting_date)
#         )
#         for role in ["Presenter 1", "Presenter 2"]:
#             cell_val = row.get(role, "")
#             if isinstance(cell_val, str) and cell_val.strip().startswith("[P]"):
#                 pending_entries.append({
#                     "date": meeting_date_str,
#                     "role": role,
#                     "pending_name": cell_val.strip(),               # e.g. "[P] Abdul"
#                     "clean_name": cell_val.replace("[P]", "").strip() # e.g. "Abdul"
#                 })
    
#     if not pending_entries:
#         st.info("No pending confirmation entries found.")
#         return

#     # Prepare a mapping for display options.
#     if "pending_mapping" not in st.session_state:
#         pending_mapping = {}
#         pending_options = []
#         for entry in pending_entries:
#             # Get recipient's email if available.
#             to_email = participant_emails.get(entry["clean_name"], "No Email")
#             display = f"{entry['clean_name']} ({to_email}) on {entry['date']}"
#             pending_options.append(display)
#             pending_mapping[display] = entry
#         st.session_state.pending_mapping = pending_mapping
#         st.session_state.pending_options = pending_options

#     # Show the dialog if the user hasn't made a selection yet.
#     if "selected_pending_entries" not in st.session_state:
#         recipients_dialog(st.session_state.pending_options)
#         st.stop()  # Wait until the dialog is submitted.

#     # ----- Now Send Emails for Selected Recipients -----
#     selected_options = st.session_state.selected_pending_entries

#     try:
#         smtp_conn = get_smtp_connection()  # Your function to establish an SMTP connection.
#     except Exception as e:
#         st.error(f"Error initializing SMTP connection: {e}")
#         return

#     sender = st.secrets["sender_email"]
#     app_url = st.secrets["app_url"]
#     organizer = st.secrets["organizer_name"]
#     email_subject = "[Confirmation Required] ML Subgroup"
#     confirmations_sent = 0
#     error_msgs = []

#     for option in selected_options:
#         entry = st.session_state.pending_mapping[option]
#         to_email = participant_emails.get(entry["clean_name"], "")
#         to_email = "luismantilla1999@gmail.com"
#         if not to_email:
#             error_msgs.append(f"No email found for {entry['clean_name']}.")
#             continue

#         encrypted_name = encrypt_name(entry["pending_name"])
#         confirmation_link = (
#             f"{app_url}/?confirmation=1"
#             f"&date={entry['date']}"
#             f"&role={entry['role'].replace(' ', '_')}"
#             f"&name={encrypted_name}"
#         )
#         try:
#             formatted_date = dt.datetime.strptime(entry["date"], "%Y-%m-%d").strftime("%B %d, %Y")
#         except Exception:
#             formatted_date = entry["date"]

#         with open("email_template.txt", "r") as template_file:
#             email_template = template_file.read()
#         email_message_text = email_template.format(
#             name_presenter=entry["clean_name"],
#             date=formatted_date,
#             confirmation_link=confirmation_link,
#             name_organizer=organizer
#         )
#         try:
#             send_email_via_smtp(smtp_conn, sender, to_email, email_subject, email_message_text)
#             confirmations_sent += 1
#         except Exception as e:
#             error_msgs.append(f"Error sending email to {to_email}: {e}")

#     try:
#         smtp_conn.quit()
#     except Exception:
#         pass

#     st.success(f"Confirmation emails sent to {confirmations_sent} pending participants.")
#     if error_msgs:
#         st.write("Errors encountered:")
#         for err in error_msgs:
#             st.write(err)

# FUUUCK

# def send_confirmation_emails():
#     df = get_schedule_df()
#     participants = get_participants_list()
    
#     # Build a mapping from participant name to email
#     participant_emails = {}
#     for p in participants:
#         clean_name = p["Name"].strip()
#         email = p.get("Email", "").strip()
#         if email:
#             participant_emails[clean_name] = email
    
#     # Identify pending entries (cells starting with "[P]")
#     pending_entries = []
#     for idx, row in df.iterrows():
#         meeting_date = row.get("Date")
#         if isinstance(meeting_date, dt.date):
#             meeting_date_str = meeting_date.strftime("%Y-%m-%d")
#         else:
#             meeting_date_str = str(meeting_date)
#         for role in ["Presenter 1", "Presenter 2"]:
#             cell_val = row.get(role, "")
#             if isinstance(cell_val, str) and cell_val.strip().startswith("[P]"):
#                 pending_entries.append({
#                     "date": meeting_date_str,
#                     "role": role,
#                     "pending_name": cell_val.strip(),            # e.g. "[P] Alessandro"
#                     "clean_name": cell_val.replace("[P]", "").strip()  # e.g. "Alessandro"
#                 })
    
#     if not pending_entries:
#         return "No pending confirmation entries found."
    
#     try:
#         smtp_conn = get_smtp_connection()
#     except Exception as e:
#         return f"Error initializing SMTP connection: {e}"
    
#     sender = st.secrets["sender_email"]
#     app_url = st.secrets["app_url"]
#     organizer = st.secrets["organizer_name"]
#     confirmations_sent = 0
#     error_msgs = []
    
#     for entry in pending_entries:
#         to_email = participant_emails.get(entry["clean_name"], "")
#         print("Sending email to:", to_email)
        
#         if not to_email:
#             error_msgs.append(f"No email found for {entry['clean_name']}.")
#             continue
        
#         encrypted_name = encrypt_name(entry["pending_name"])
#         confirmation_link = (
#             f"{app_url}/?confirmation=1"
#             f"&date={entry['date']}"
#             f"&role={entry['role'].replace(' ', '_')}"
#             f"&name={encrypted_name}"
#         )
        
#         email_subject = "[Confirmation Required] ML Subgroup"
        
#         with open("email_template.txt", "r") as template_file:
#             email_template = template_file.read()

#         email_message_text = email_template.format(
#             name_presenter=entry["clean_name"],
#             date=meeting_date.strftime('%B %d, %Y'),
#             confirmation_link=confirmation_link,
#             name_organizer=organizer
#         )

#         try:
#             send_email_via_smtp(smtp_conn, sender, to_email, email_subject, email_message_text)
#             confirmations_sent += 1
#         except Exception as e:
#             error_msgs.append(f"Error sending email to {to_email}: {e}")
    
#     smtp_conn.quit()
#     result_message = f"Confirmation emails sent to {confirmations_sent} pending participants."
#     if error_msgs:
#         result_message += "\nErrors:\n" + "\n".join(error_msgs)
#     return result_message
