"""
    This Script provides tools to manipulate Google Drive, including the following use cases:
    
        1. search (Done)
        2. create_folder (subfolder) (Done)
        3. delete (Done)
        4. upload_file (files)(to a folder) (Done)
        5. upload_folder (Done)
        6. download_file (files)
        7. download_folder
        8. empty_trash (Done)
        9. archive_file (files)
        10. archive_folder
        11. clean_folder
    Depreciated
        1. trash/untrash (Depreciated for Google Drive API v3)
"""

# -*- coding: utf-8 -*-
from __future__ import print_function

# default libraries
import os
import io
import re
import sys
import time
import pickle
import base64
import datetime

# tools
import numpy as np
import pandas as pd

from os import access, listdir
from os.path import isfile, join

# Google API
from apiclient import errors
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# load conf
from google_api_helpers import creds

# logger
import logging

logger = logging.getLogger(__name__)


class Drive:
    def __init__(self):
        self.service = build("drive", "v3", credentials=creds, cache_discovery=False)

    def list_all_files(self):
        page_token = None
        all_files = []
        while True:
            response = self.service.files().list(q="",
                                                spaces='drive',
                                                fields='nextPageToken, files(id, name)',
                                                pageToken=page_token).execute()
            all_files = all_files + response.get('files', [])
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        return all_files

    def search(
        self,
        file_name: str = None,
        file_id: str = None,
        query_string="mimeType = 'application/vnd.google-apps.folder'",
        empty_trash=False,
    ):
        """
        This function will search for a folder by id or name in Google drive, trash excluded.
        Either file_id or file_name should not be empty.
        This function is for exact match only.

        :param file_id: target folder id, defaults to None
        :type file_id: str, optional
        :param file_name: folder name, defaults to None
        :type file_name: str, optional
        :param query_string: specify query terms. defaults to "mimeType = 'application/vnd.google-apps.folder'" for folder.
            check https://developers.google.com/drive/api/v3/ref-search-terms#operators and https://developers.google.com/drive/api/v3/search-files for reference.
            check https://developers.google.com/drive/api/v3/mime-types?hl=en to get mimeType for sheets/slides/docs and etc.
        :type query_string: str

        :return: file_id, file_name
        :rtype: str, str
        """
        # TODO:multiple files with the same name
        # TODO: add parents
        assert (
            file_id != None or file_name != None
        ), "Either file_id or file_name should not be None."

        def _search(q):
            page_token = None
            while True:
                response = (
                    self.service.files()
                    .list(
                        q=q,
                        spaces="drive",
                        fields="nextPageToken, files(id, name)",
                        pageToken=page_token,
                    )
                    .execute()
                )
                for file in response.get("files", []):
                    found_file_name = file.get("name")
                    found_file_id = file.get("id")
                    if found_file_name == file_name or found_file_id == file_id:
                        logger.info(
                            "The file {} is found with id {}".format(
                                found_file_name, found_file_id
                            )
                        )
                        return found_file_name, found_file_id

                page_token = response.get("nextPageToken", None)
                if page_token is None:
                    break
            return None, None

        # search file exclude trash
        found_file_name, found_file_id = _search(q=query_string + " and trashed=False")
        if not found_file_id:
            logger.info("The file {} does not exist Trash excluded.".format(file_name))
        return found_file_name, found_file_id

    def create_folder(
        self, folder_name: str, allow_exist: bool = True, parents: list = []
    ):
        """
        This function create a folder in Google Drive as {folder_name}.

        The existance of the folder_name will be pre-checked.
        `allow_exist` gives an option whether to continue with the existing folder.
        If True, the program will continue running and use the existing folder.
        If False, the program will stop.

        :param folder_name: target folder name.
        :type folder_name: str
        :param allow_exist: default True. whether to continue with the folder if the folder already exists. If False, the program will be stopped when the folder name already exists.
        :type allow_exist: bool
        :parents: default []. Create a sub_folder under parents.
        :type parents: list, file_id of parent folders if subfolders are created.
        :return: folder_id
        :rtype: str
        """
        _, found_folder_id = self.search(file_name=folder_name)
        if not allow_exist:
            assert (
                found_folder_id == None
            ), "{} already exists! Use another name.".format(folder_name)

        # if the folder already exists
        if found_folder_id:
            logger.info("The folder exists with id {}".format(found_folder_id))
            return found_folder_id

        # create a new folder
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parents:
            file_metadata["parents"] = parents
        try:
            folder = self.service.files().create(body=file_metadata).execute()
        except:
            logger.error("Unexpected error ", exc_info=True)
        folder_id = folder.get("id")
        logger.info("The folder is created with id {}".format(folder_id))
        return folder_id

    def delete(
        self,
        file_name: str = None,
        file_id: str = None,
        query_string="mimeType = 'application/vnd.google-apps.folder'",
    ):
        """
        Permanenly delete a file/folder(including all descendants) without moving it to the trash.

        :param file_name: name of the target file, defaults to None
        :type file_name: str, optional
        :param file_id: id of the target file, defaults to None
        :type file_id: str, optional
        :param query_string: query string to specify query terms, defaults to "mimeType = 'application/vnd.google-apps.folder'" for folder.
        :type query_string: str, optional

        Note: Either file_id or file_name should not be None.
        """
        assert (
            file_id != None or file_name != None
        ), "Either file_id or file_name should not be None."

        if not file_id:
            _, file_id = self.search(file_name=file_name, query_string=query_string)
        else:
            file_name, file_id = self.search(file_id=file_id, query_string=query_string)

        assert (
            file_id != None
        ), "The file intent to delete does not exist. Check the file name, id and mimetype!"
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info("Delete successful.")
        except:
            logger.error("Unexpected Error", exc_info=True)

    def download_folder(self, folder_name: str = None, folder_id: str = None):
        assert (
            folder_id != None or folder_name != None
        ), "Either folder_id or folder_name should not be None."
        # TODO: by downloading files from the folder.
        # write a logger to indicate number of files uploaded, and how long did it take
        # the same for upload a folder.
        pass

    def upload_folder(
        self, local_folder_path: str, target_folder_name: str = None, parents: list = []
    ):
        """
        upload a whole folder with its descendants(files only) to Google drive.

        :param local_folder_path: path to the folder to be uplaoded.
        :type local_folder_path: str
        :param target_folder_name: name of the folder in the drive, defaults to None. If not specified, original name will be used.
        :type target_folder_name: str, optional
        :param parents: list of parent folder id, defaults to []
        :type parents: list, optional
        """
        if not target_folder_name:
            target_folder_name = local_folder_path.split("/")[-1]
        target_folder_id = self.create_folder(
            folder_name=target_folder_name, parents=parents
        )
        files = [
            local_folder_path + "/" + f
            for f in listdir(local_folder_path)
            if isfile(join(local_folder_path, f))
        ]

        _, _ = self.upload_files(files, parents=[target_folder_id])

        logger.info("Folder uploading completed.")
        return target_folder_id

    def upload_file(
        self,
        local_file_path: str,
        drive_file_name: str = None,
        mimetype: str = None,
        parents: list = [],
    ):
        """
        Upload a file to Google Drive.

        :param local_file_path: file path of the local file to be uploaded.
        :type local_file_path: str
        :param drive_file_name: file name to be in the drive. defaults to None.
        :type drive_file_name: str
        :param mimetype: mimeType as of '*/*', defaults to 'csv'
        :type mimetype: str, optional
        :param parents: folder id in list if uploaded to a folder, defaults to []
        :type parents: list, optional
        :return: file id
        :rtype: str
        """
        if not drive_file_name:
            drive_file_name = local_file_path.split("/")[0]
        file_metadata = {
            "name": drive_file_name,
        }
        if mimetype:
            media = MediaFileUpload(local_file_path, mimetype=mimetype, resumable=True)
        else:
            media = MediaFileUpload(local_file_path, resumable=True)
        if parents:
            file_metadata["parents"] = parents
        file = (
            self.service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        file_id = file.get("id")
        logger.info("The file is upload successful with id {}".format(file_id))
        return file_id

    def upload_files(
        self,
        file_paths: list,
        drive_file_names: list = None,
        mimetype: str = None,
        parents: list = [],
    ):
        """
        Upload a list of files to Google Drive.
        Files must be uploaded to the same folder.
        If the name to be in the drive is not specified, the original name of file will be used.

        :param file_paths: [description]
        :type file_paths: list
        :param drive_file_names: [description], defaults to None
        :type drive_file_names: list, optional
        :param parents: [description], defaults to []
        :type parents: list, optional
        """
        # TODO: uploading file with wrong mimetype will lead to wrong compiling in drive.
        if not drive_file_names:
            logger.info(
                "The target name of files are not provided. Will keep the same as local files."
            )
        elif len(file_paths) != len(drive_file_names):
            logger.warn(
                "The number of files and number of names do not match. Names are kept as the same as local files"
            )
            drive_file_names = None

        if not drive_file_names:
            drive_file_names = [file_path.split("/")[-1] for file_path in file_paths]

        file_ids = []
        failed_files = []
        for f, n in zip(file_paths, drive_file_names):
            try:
                file_id = self.upload_file(
                    local_file_path=f,
                    drive_file_name=n,
                    mimetype=mimetype,
                    parents=parents,
                )
                file_ids.append(file_id)
            except:
                logger.error("Unable to upload file {}. ".format(f), exc_info=True)
                failed_files.append(f)

        if len(file_ids) > 0:
            logger.info("Successfully uploaded {} files".format(len(file_ids)))
        if len(failed_files) > 0:
            logger.warn("{} files failed uploading.".format(len(failed_files)))
        return file_ids, failed_files

    def empty_trash(self):
        self.service.files().emptyTrash().execute()

    def download_file(
        self,
        file_id: str,
        file_name: str,
        download_to: str = os.path.join(os.path.expanduser("~"), "Downloads"),
    ):
        request = self.service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print("Download %d%%." % int(status.progress() * 100))

        with open(download_to + "/" + file_name, "wb") as f:
            f.write(fh.getbuffer())
        logger.info("Completed downloading {}".format(file_name))

    def download_files(self, file_ids: list, download_to: str):
        pass

    def share_file_access(self, target_email_address, file_id:str, access_role:str="writer"):
        def _callback(request_id, response, exception):
            if exception:
                # Handle error
                print(exception)
            else:
                print("Permission Id: %s" % response.get('id'))

        batch = self.service.new_batch_http_request(callback=_callback)
        user_permission = {
            'type': 'user',
            'role': access_role,
            'emailAddress': target_email_address
        }
        batch.add(self.service.permissions().create(
                fileId=file_id,
                body=user_permission,
                fields='id',
        ))
        batch.execute()