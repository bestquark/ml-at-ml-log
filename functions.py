import datetime

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import base64
import streamlit as st

def get_next_wednesday(after_date):
    # Wednesday is weekday() == 2
    days_ahead = 2 - after_date.weekday()
    if days_ahead <= 0:  # Target day already passed this week
        days_ahead += 7
    return after_date + datetime.timedelta(days=days_ahead)

def highlight_empty(val):
    return 'background-color: goldenrod' if val in ["EMPTY", ""," "] else ''

def highlight_random(val):
    # make light blue if val starts with [P]
    color = 'background-color: darkblue' if val.startswith("[P]") else ''
    color = 'background-color: darkred' if val.startswith("[C]") else color
    color = 'background-color: darkblue' if val.startswith("[R]") else color
    return color

def get_fernet():
    # Retrieve the encryption key string from secrets.toml
    encryption_key_str = st.secrets["encryption_key"]["value"]
    encryption_key_bytes = encryption_key_str.encode("utf-8")
    # Use a constant salt (must be the same for encryption and decryption)
    salt = b"mlatml_salt"
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    derived_key = base64.urlsafe_b64encode(kdf.derive(encryption_key_bytes))
    return Fernet(derived_key)

def encrypt_name(name: str) -> str:
    f = get_fernet()
    encrypted = f.encrypt(name.encode("utf-8"))
    return encrypted.decode("utf-8")

def decrypt_name(encrypted_name: str) -> str:
    f = get_fernet()
    decrypted = f.decrypt(encrypted_name.encode("utf-8"))
    return decrypted.decode("utf-8")