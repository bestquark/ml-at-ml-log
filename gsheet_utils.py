import streamlit as st

import gspread
from google.oauth2.service_account import Credentials

from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"]

def get_gspread_client():
    # Load service account info from Streamlit secrets
    service_account_info = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    client = gspread.authorize(credentials)
    return client

def get_sheet(sheet_name):
    client = get_gspread_client()
    # Load spreadsheet ID from secrets
    spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]
    spreadsheet = client.open_by_key(spreadsheet_id)
    return spreadsheet.worksheet(sheet_name)

def get_schedule_df():
    ws = get_sheet("Schedule")
    data = ws.get_all_records()
    import pandas as pd
    df = pd.DataFrame(data)
    # Convert 'Date' column to datetime.date if exists
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
    return [row["Name"] for row in data if row.get("Name")]

def save_participants_list(participants):
    ws = get_sheet("Participants")
    data = [["Name"]] + [[p] for p in participants]
    ws.clear()
    ws.update(data)
    
def get_drive_service():
    """
    Initializes and returns a Google Drive service using the service account credentials.
    Assumes that `st.secrets["gcp_service_account"]` contains valid credentials.
    """
    service_account_info = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=credentials)
    return drive_service

def upload_file_to_drive(file_name, file_bytes, mime_type, parent_folder_id=None):
    drive_service = get_drive_service()
    media = MediaInMemoryUpload(file_bytes, mimetype=mime_type)

    # Include parent folder if provided
    file_metadata = {
        'name': file_name,
    }
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
    # Prepare a new row with the provided data.
    # Ensure the order matches your sheet: Date, Title, Description, PDF_Name, PDF_Link
    new_row = [date_str, title, description, pdf_name, pdf_link]
    ws.append_row(new_row)

def delete_material_row(row_index):
    ws = get_sheet("Materials")
    ws.delete_rows(row_index)


def get_all_materials():
    """Fetch all materials data from the 'Materials' worksheet."""
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
