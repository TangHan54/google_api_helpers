# Google API Helpers

### Gmail Helpers
```
from google_api_helpers.gmail_helpers import Mail

mail = Mail()

mail.send_gmail(
    sender = '',
    to = ['test@gmail.com'],
    cc = [],
    bcc = [],
    subject = 'test',
    message_text = 'test content',
    attachments = ['file1.csv']
)
```
### Drive Helpers
```
from google_api_helpers.gdrive_helpers import Drive

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s-%(levelname)s-%(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("test_gdrive_api_v2.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

drive = Drive()

### folder operation
# create a folder
created_folder_id = drive.create_folder("test_folder")
# search a folder by name
found_folder_name, found_folder_id = drive.search("test_folder")
# search a folder by id
found_folder_name, found_folder_id = drive.search(file_id=created_folder_id)
# delete a folder (choose either one)
drive.delete(file_name = "test_folder")
drive.delete(file_id = created_folder_id)
# upload a folder with its files
folder_id = drive.uplaod_folder('tests')

### subfolder operation
# create a subfolder
created_subfolder_id = drive.create_folder("test_subfolder", parents=[created_folder_id])
# search a subfolder by name
found_subfolder_name, found_subfolder_id = drive.search("test_subfolder")
# search a subfolder by id
found_subfolder_name, found_subfolder_id = drive.search(file_id=created_subfolder_id)
# delete a subfolder (choose either one)
drive.delete(file_name = "test_subfolder")
drive.delete(file_id = created_subfolder_id)

### file operation
# *** IMPORTANT: There could be duplicated file names. use file id instead of file name!

# upload a file to root
root_file_id = drive.upload_file(local_file_path='test.csv', drive_file_name='test.csv', mimetype='text/csv')
# upload a file to a folder
folder_file_id = drive.upload_file(local_file_path='test.csv', drive_file_name='test.csv', parents = [created_subfolder_id])
# upload files to the same folder
success_ids, failed_files = drive.upload_files(file_paths=['test.csv','test2.csv','test3.doc'],parents=[created_subfolder_id])
# search a file
found_file_name, found_file_id = drive.search(file_id=root_file_id)
# delete a file
drive.delete(file_id=root_file_id, query_string="mimeType='text/csv'")

# empty trash
drive.empty_trash()
```