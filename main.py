import os.path
import re
import sys
import datetime
import webbrowser

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from PySide6.QtCore import Qt
from PySide6.QtWidgets import *

from platformdirs import user_desktop_dir

import pandas as pd

from collections import defaultdict
import asyncio
import aiofiles
from qasync import *

SCOPES = ["https://www.googleapis.com/auth/drive"]
FILE_ID = "1NWb-HJxqwAPqQKzNxqZGQg8DRV0N5UwLBe0pT4FFKqM"
FILE_NAME = "APC"


class Window(QWidget):
    def __init__(self, loop=None):
        super().__init__()
        self.setWindowTitle("APC")
        self.resize(400, 300)

        self.setStyleSheet("""
        QLineEdit,QDateEdit {
            border: 1px solid #bbb;
            outline: none;
            font-size: 14px;
            border-radius: 4px;
            padding: 4px 8px;
        }
        
        QLineEdit:focus,QDateEdit:focus {
            border: 1px solid #03a9fc;
        }
        
        QPushButton {
            border: none;
            outline: none;
            font-size: 14px;
            background-color: #03a9fc;
            color: #fff;
            border-radius: 4px;
            padding: 4px 8px;
        }
        
        QPushButton:hover {
            border: none;
            outline: none;
            font-size: 14px;
            background-color: #3fb6f2;
            color: #fff;
            border-radius: 4px;
            padding: 4px 8px;
        }
        
        QPushButton:pressed {
            border: none;
            outline: none;
            font-size: 14px;
            background-color: #0c7bb3;
            color: #fff;
            border-radius: 4px;
            padding: 4px 8px;
        }
        
        QDateEdit::drop-down { 
            width: 0px; border: none;
        }
        """)
        self.UIinit()
        self.loop = loop or asyncio.get_event_loop()

    def UIinit(self):
        self.login_layout = QFormLayout()
        self.login_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel(self, text="APC")
        self.label.setStyleSheet("font-size: 24px; font-weight: 600;")
        self.login_layout.addRow(self.label)

        self.courseId_label = QLabel(self, text="Enter Course ID")

        # コースID入力
        self.courseId_Input = QLineEdit(self)
        self.courseId_Input.setFixedWidth(250)
        self.login_layout.addRow(self.courseId_label, self.courseId_Input)

        # 開始日付入力
        self.startDate_label = QLabel(self, text="Enter Start Date")
        self.startDate_Input = QDateEdit(self)
        self.startDate_Input.setDisplayFormat("d/M/yyyy")
        self.startDate_Input.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.startDate_Input.setFixedWidth(250)
        self.login_layout.addRow(self.startDate_label, self.startDate_Input)

        # ログインボタン
        self.search_course_btn = QPushButton(self, text="Login")
        self.search_course_btn.setFixedWidth(120)
        self.search_course_btn.clicked.connect(self.search_course)
        self.login_layout.addRow(self.search_course_btn)

        self.setLayout(self.login_layout)

    def submitUI(self):
        QWidget().setLayout(self.layout())
        self.submit_layout = QVBoxLayout(self)
        
        self.submit_tab_header = QLabel("ACP")
        self.submit_layout.addWidget(self.submit_tab_header)
        
        self.submit_btns = QWidget()
        self.submit_btns_layout = QGridLayout(self)
        self.submit_btns.setLayout(self.submit_btns_layout)

        self.cleanup_btn = QPushButton(self, text="Clean Up")
        self.submit_btns_layout.addWidget(self.cleanup_btn, 0, 0)
        self.cleanup_btn.clicked.connect(self.cleanup_action)

        self.setup_btn = QPushButton(self, text="Set Up")
        self.setup_btn.clicked.connect(self.setup_action)
        self.submit_btns_layout.addWidget(self.setup_btn, 0, 1)

        self.open_submit_btn = QPushButton(self, text="Submit Deliverables")
        self.submit_btns_layout.addWidget(self.open_submit_btn, 1, 0)
        self.open_submit_btn.clicked.connect(self.o_submit_act)

        self.open_survey_btn = QPushButton(self, text="Open Survey")
        self.submit_btns_layout.addWidget(self.open_survey_btn, 1, 1)
        self.open_survey_btn.clicked.connect(self.o_survey_act)
        
        self.submit_layout.addWidget(self.submit_btns)

        self.submit_tab_message = QLabel("")
        self.submit_layout.addWidget(self.submit_tab_message)

        self.setLayout(self.submit_layout)
        self.update()

    def search_course(self, courseId):
        # print("clicked!")
        df = pd.read_csv(
            f"./{FILE_NAME}",
            encoding="utf-8",
            names=[
                "courseId",
                "startDate",
                "endDate",
                "driveUrl",
                "submitFormUrl",
                "surveyFormUrl",
            ],
        )

        isMatch = False
        self.courseId = None
        self.courseInfo = None

        for idx, DBcourseId in enumerate(df["courseId"]):
            if (
                DBcourseId
                == self.courseId_Input.text()  # CSVに保存されているコースIDと入力されたコースIDが一緒か
                and self.startDate_Input.text()
                == df.iloc[idx].get(
                    "startDate"
                )  # 入力された開始日がCSVのstartDateと一緒か(実質パスワード)
                and datetime.datetime.today()
                < datetime.datetime.strptime(df.iloc[idx].get("endDate"), "%d/%m/%Y")
            ):
                # print(f"{DBcourseId} was matched")
                isMatch = True
                # courseId = DBcourseId
                self.courseInfo = df.iloc[idx]

        if isMatch:
            self.submitUI()

    def cleanup_action(self):
        pass

    @asyncSlot()
    async def setup_action(self):
        # SetUpボタンを押された時の動作
        desktop_path = user_desktop_dir()
        print(f"{desktop_path}/APC")

        # デスクトップにAPCディレクトリがなければ生成
        if not os.path.exists(f"{desktop_path}/APC"):
            os.makedirs(f"{desktop_path}/APC")

        if creds is None:
            dlg = QDialog(self)
            dlg.setWindowTitle("Credentials Not Found!")
            dlg.resize(200, 120)
            dlg_label = QLabel("⚠Credentials.json Not Found.\nCheck it.", dlg)
            dlg.exec()
            return

        try:
            service = build("drive", "v3", credentials=creds)

            # Call the Drive v3 API
            # ディレクトリ内のアイテムをリストアップ、再帰的に数を数える
            print(self.courseInfo.get("driveUrl"))
            extract_id = re.findall(
                r"https://drive.google.com/drive/folders/([0-9a-zA-Z\-]+)\?usp=sharing",
                self.courseInfo.get("driveUrl"),
            )
            print(extract_id[0])

            count_dl_files = await self.count_files_in_folder(service, extract_id[0])
            downloaded_count = 0

            QWidget().setLayout(self.layout())
            self.dl_progress_layout = QVBoxLayout(self)
            self.count_dl = QLabel(f"{downloaded_count}/{count_dl_files}", self)
            self.dl_progress_layout.addWidget(self.count_dl)

            self.dl_progress_bar = QProgressBar(self)
            self.dl_progress_bar.setValue(downloaded_count)
            self.dl_progress_bar.setMaximum(count_dl_files)
            self.dl_progress_layout.addWidget(self.dl_progress_bar)
            self.setLayout(self.dl_progress_layout)
            self.update()

            results = (
                service.files()
                .list(
                    q=f"'{extract_id[0]}' in parents and trashed = false",
                    fields="files(id, name, mimeType)",
                )
                .execute()
            )
            print(results)
            dl_target = results.get("files")

            for item in dl_target:
                if item.get("mimeType") == "application/vnd.google-apps.folder":
                    results = (
                        service.files()
                        .list(
                            q=f"'{item.get("id")}' in parents and trashed = false",
                            fields="files(id, name, mimeType)",
                        )
                        .execute()
                    )

                    for file in results.get("files"):
                        if file.get("aditional_dir"):
                            file["additional_dir"] = (
                                f"{file.get("aditional_dir")}/{item.get("name")}"
                            )
                        else:
                            file["additional_dir"] = f"/{item.get("name")}"

                        dl_target.append(file)
                    continue

                dl_binary = service.files().get_media(fileId=item.get("id")).execute()

                if item.get("additional_dir"):
                    if not os.path.exists(
                        f"{desktop_path}/APC/{item.get("additional_dir")}"
                    ):
                        os.makedirs(f"{desktop_path}/APC/{item.get("additional_dir")}")
                    async with aiofiles.open(
                        f"{desktop_path}/APC/{item.get("additional_dir")}/{item.get("name")}",
                        "wb",
                    ) as w_dlf:
                        await w_dlf.write(dl_binary)
                else:
                    async with aiofiles.open(
                        f"{desktop_path}/APC/{item.get("name")}", "wb"
                    ) as w_dlf:
                        await w_dlf.write(dl_binary)

                downloaded_count += 1
                self.count_dl.setText(f"{downloaded_count}/{count_dl_files}")
                self.dl_progress_bar.setValue(downloaded_count)
                self.update()

        except HttpError as error:
            # TODO(developer) - Handle errors from drive API.
            dlg = QDialog()
            dlg.setWindowTitle("Error !")
            dlg.resize(200, 120)
            dlg_label = QLabel(
                "⚠An error occurred\n while connecting to Google Drive.", dlg
            )
            dlg.exec()
            print(f"An error occurred: {error}")
            exit(-1)

        self.submitUI()
        self.submit_tab_message.setText("Files have been downloaded.")

    async def count_files_in_folder(self, service, root_folder_id):
        query = "trashed = false"

        # We only need 'id', 'mimeType', and 'parents' to build the tree structure
        fields = "nextPageToken, files(id, mimeType, parents)"

        all_items = []
        page_token = None

        print("Fetching files from Google Drive...")
        while True:
            results = (
                service.files()
                .list(
                    q=query,
                    fields=fields,
                    pageSize=1000,  # Maximize page size to reduce API calls
                    pageToken=page_token,
                )
                .execute()
            )

            all_items.extend(results.get("files", []))
            page_token = results.get("nextPageToken", None)
            if not page_token:
                break

        # 2. Map items out into a parent -> children dictionary mapping
        # Maps a parent folder ID to a list of its child objects
        children_map = defaultdict(list)
        for item in all_items:
            parents = item.get("parents", [])
            for p in parents:
                children_map[p].append(item)

        # 3. Use Depth-First Search (DFS) to traverse down from the root_folder_id
        total_file_count = 0
        folders_to_process = [root_folder_id]
        visited_folders = set()  # Prevents infinite loops in shared shortcut scenarios

        print("Calculating recursive totals...")
        while folders_to_process:
            current_folder = folders_to_process.pop()
            if current_folder in visited_folders:
                continue
            visited_folders.add(current_folder)

            # Get all child items for the current folder node
            for child in children_map.get(current_folder, []):
                if child["mimeType"] == "application/vnd.google-apps.folder":
                    # If it's a subfolder, add it to the queue to process its contents
                    folders_to_process.append(child["id"])
                else:
                    # If it's a file, increment the counter
                    total_file_count += 1

        return total_file_count

    def o_submit_act(self):
        webbrowser.open(self.courseInfo.get("submitFormUrl"))
        pass

    def o_survey_act(self):
        webbrowser.open(self.courseInfo.get("surveyFormUrl"))
        pass


async def main():
    App = QApplication(sys.argv)
    loop = QEventLoop(App)
    asyncio.set_event_loop(loop)

    global creds
    creds = None

    if os.path.exists("credentials.json"):
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    else:
        dlg = QDialog()
        dlg.setWindowTitle("Credentials Not Found!")
        dlg.resize(200, 120)
        dlg_label = QLabel("⚠Credentials.json Not Found.\nCheck it.", dlg)
        dlg.exec()
        exit(-1)

    if creds is not None:
        try:
            service = build("drive", "v3", credentials=creds)

            # Call the Drive v3 API
            results = (
                service.files().export(fileId=FILE_ID, mimeType="text/csv").execute()
            )
            # print(results)
            with open("./" + "APC", "wb") as w_f:
                w_f.write(results)

            window = Window(loop)
            window.show()
            with loop:
                loop.run_forever()

        except HttpError as error:
            # TODO(developer) - Handle errors from drive API.
            dlg = QDialog()
            dlg.setWindowTitle("Error !")
            dlg.resize(200, 120)
            dlg_label = QLabel(
                "⚠An error occurred\n while connecting to Google Drive.", dlg
            )
            dlg.exec()
            print(f"An error occurred: {error}")
            exit(-1)

    # sys.exit(App.exec())


if __name__ == "__main__":
    asyncio.run(main())
