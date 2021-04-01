import os
import sys
import pickle
import logging

from ast import literal_eval
from configobj import ConfigObj

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# load configurations
if os.path.isfile("config.ini"):
    config_obj = ConfigObj("config.ini")
else:
    print("config.ini does not exist. using default.ini")
    config_obj = ConfigObj("default.ini")

# google_api_config
token_path = config_obj["google_api_config"]["token_path"]
credentials_path = config_obj["google_api_config"]["credentials_path"]

# google_api_parameters
scopes = []
if bool(config_obj["google_api_parameters"]["include_gdrive"]):
    scopes.append("https://www.googleapis.com/auth/drive")
if bool(config_obj["google_api_parameters"]["include_gsheets"]):
    scopes.append("https://www.googleapis.com/auth/spreadsheets")
if bool(config_obj["google_api_parameters"]["include_gmail"]):
    scopes.append("https://www.googleapis.com/auth/gmail.compose")
if bool(config_obj["google_api_parameters"]["include_gdoc"]):
    scopes.append("https://www.googleapis.com/auth/documents")

# user can also add other scopes
other_scopes = config_obj["google_api_parameters"]["other_scopes"]
if other_scopes:
    scopes = scopes + other_scopes

# connect to apis
creds = None
if os.path.exists(token_path):
    with open(token_path, "rb") as token:
        creds = pickle.load(token)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
if not creds or not creds.has_scopes(scopes):
    try:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
    except:
        print("Unexpected error:", sys.exc_info()[0])
    creds = flow.run_local_server(port=0)
    with open(token_path, "wb") as token:
        pickle.dump(creds, token)

# default gmail sender
default_sender = config_obj['gmail_parameter']['default_sender']

# make sure the credentials are not empty.
assert creds != None, "credential is not found. Check your configuration!"
