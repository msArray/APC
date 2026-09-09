import os.path
import re
import sys
import datetime
import webbrowser
import shutil

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from PySide6.QtCore import Qt, QMetaObject, QModelIndex, Slot
from PySide6.QtWidgets import *

from platformdirs import user_desktop_dir

import pandas as pd

from collections import defaultdict
import asyncio
import aiofiles
from qasync import *

from file_tree import FileTreeSelectorModel

from docx import Document
import win32com.client

SCOPES = ["https://www.googleapis.com/auth/drive"]
FILE_ID = "1NWb-HJxqwAPqQKzNxqZGQg8DRV0N5UwLBe0pT4FFKqM"
FILE_NAME = "APC"


class Window(QWidget):
    def __init__(self, loop=None):
        super().__init__()
        self.setWindowTitle("APC")
        self.resize(640, 320)

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
        QMetaObject.connectSlotsByName(self)
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
        self.st_seac_h_box = QWidget(self)
        self.st_seac_h_box_layout = QHBoxLayout()
        self.st_seac_h_box_layout.addStretch(1)
        self.st_seac_h_box.setLayout(self.st_seac_h_box_layout)

        self.search_course_btn = QPushButton(self, text="Login")
        self.search_course_btn.setFixedWidth(120)
        self.search_course_btn.clicked.connect(self.search_course)

        self.st_seac_h_box_layout.addWidget(self.search_course_btn)

        self.login_layout.addRow(self.st_seac_h_box)

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

        self.quit_btn = QPushButton(self, text="Quit")
        self.submit_btns_layout.addWidget(self.quit_btn, 2, 0)
        self.quit_btn.clicked.connect(self.quit_act)

        self.submit_tab_message = QLabel("")
        self.submit_layout.addWidget(self.submit_tab_message)

        self.setLayout(self.submit_layout)
        self.update()

    def quit_act(self):
        self.loop.stop()
        sys.exit(0)

    def search_course(self):
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
        QWidget().setLayout(self.layout())
        self.cleanup_layout = QVBoxLayout(self)
        apc = QLabel("APC")
        apc.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.cleanup_layout.addWidget(apc)
        warn_msg = QLabel("Warning: Files will be Deleted")
        warn_msg.setStyleSheet("font-size: 22px; font-weight: bold;")
        self.cleanup_layout.addWidget(warn_msg)
        warn_detail = QLabel(
            "・All APC files and files stored in the Downloads folder will be permanently deleted.\n・If you need to keep any of these files, please back them up before proceeding.\n・Deleted files may not be recoverable.",
        )
        self.cleanup_layout.addWidget(warn_detail)

        self.cleanfiles_btn = QPushButton("Clean Files")
        self.cleanfiles_btn.clicked.connect(self.clean_files)
        self.cleanup_layout.addWidget(self.cleanfiles_btn)
        self.setLayout(self.cleanup_layout)

    def clean_files(self):
        desktop_path = user_desktop_dir()
        # デスクトップにAPCディレクトリがあれば削除
        if os.path.exists(f"{desktop_path}/APC"):
            shutil.rmtree(f"{desktop_path}/APC")
        
        self.submitUI()
        self.submit_tab_message.setText("APC Directory was deleted")

    @asyncSlot()
    async def setup_action(self):
        # SetUpボタンを押された時の動作
        desktop_path = user_desktop_dir()

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

            # ダウンロード済みファイル数　完了数/予定数
            QWidget().setLayout(self.layout())
            self.dl_progress_layout = QVBoxLayout(self)
            self.count_dl = QLabel(f"{downloaded_count}/{count_dl_files}", self)
            self.dl_progress_layout.addWidget(self.count_dl)

            # プログレスバー
            self.dl_progress_bar = QProgressBar(self)
            self.dl_progress_bar.setValue(downloaded_count)
            self.dl_progress_bar.setMaximum(count_dl_files)
            self.dl_progress_layout.addWidget(self.dl_progress_bar)
            self.setLayout(self.dl_progress_layout)
            self.update()

            # Google APIから対象ディレクトリ直下のファイルを取得する。
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

            # ターゲットのファイルから、ディレクトリならその中のものをすべてdl_targetに入れファイルならダウンロード
            # フォルダの中にあるファイルはadditional_dirにディレクトリ構造を追加
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

                # ダウンロード数、プログレスバーの更新
                downloaded_count += 1
                self.count_dl.setText(f"{downloaded_count}/{count_dl_files}")
                self.dl_progress_bar.setValue(downloaded_count)
                self.update()
        # Google Drive http エラー
        # 多分、ネットがつながらないときとか
        except HttpError as error:
            # エラー時はダイアログを出して終了
            dlg = QDialog()
            dlg.setWindowTitle("Error !")
            dlg.resize(200, 120)
            dlg_label = QLabel(
                "⚠An error occurred\n while connecting to Google Drive.", dlg
            )
            dlg.exec()
            print(f"An error occurred: {error}")
            exit(-1)

        # submitUIに切り替え、ダウンロード完了メッセージ表示
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

    @asyncSlot()
    async def o_submit_act(self):
        QWidget().setLayout(self.layout())
        # ヘッダー
        self.sb_tab_layout = QVBoxLayout(self)
        self.sb_tab_header = QLabel(self, text="APC")
        self.sb_tab_layout.addWidget(self.sb_tab_header)

        # ファイルツリー
        desktop_path = user_desktop_dir()
        self.file_tree_model = FileTreeSelectorModel(rootpath=f"{desktop_path}/APC/")

        self.f_tree_view = QTreeView()

        self.f_tree_view.setObjectName("Deliverables")
        self.f_tree_view.setAnimated(False)
        self.f_tree_view.setIndentation(20)
        self.f_tree_view.setSortingEnabled(True)
        self.f_tree_view.setColumnWidth(200, 120)

        # Attach Model to View
        self.f_tree_view.setModel(self.file_tree_model)
        self.f_tree_view.setRootIndex(self.file_tree_model.parent_index)
        self.sb_tab_layout.addWidget(self.f_tree_view)
        # 下のContinue ボタン
        self.sb_continue_btn = QPushButton(self, text="Continue")
        self.sb_continue_btn.clicked.connect(self.enter_uid)
        self.sb_tab_layout.addWidget(self.sb_continue_btn)

        self.setLayout(self.sb_tab_layout)
        # webbrowser.open(self.courseInfo.get("submitFormUrl"))

    def enter_uid(self):
        QWidget().setLayout(self.layout())
        self.sb_uid_layout = QVBoxLayout(self)
        w = QWidget()
        v = QHBoxLayout(self)
        w.setLayout(v)
        self.ent_uid_label = QLabel(self, text="Enter Username")
        v.addWidget(self.ent_uid_label)

        # ユーザー名の入力
        self.uid_Input = QLineEdit(self)
        self.uid_Input.setFixedWidth(250)
        v.addWidget(self.uid_Input)
        self.sb_uid_layout.addWidget(w)

        # 下のContinue ボタン
        self.sb_uid_continue_btn = QPushButton(self, text="Continue")
        self.sb_uid_continue_btn.clicked.connect(self.create_submit)
        self.sb_uid_layout.addWidget(self.sb_uid_continue_btn)

        self.setLayout(self.sb_uid_layout)

    def create_submit(self):
        ### Wordファイルの作成
        paths = self.file_tree_model.getCheckedFilepaths()
        uid = self.uid_Input.text()

        uid = re.sub(r'[\\/:*?"<>|]', "_", uid)

        if not uid:
            QMessageBox.warning(
                self,
                "Error",
                "UIDを入力してください。",
            )
            return
        desktop_path = user_desktop_dir()
        output_dir = os.path.join(desktop_path, "APC")
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(
            output_dir,
            f"Submission - {uid}.docx",
        )

        if os.path.exists(output_path):
            try:
                # 削除できれば、Word等では使用されていない
                os.remove(output_path)

            except PermissionError:
                QMessageBox.warning(
                    self,
                    "File is in use",
                    (
                        "The Word document is currently open.\n\n"
                        f"{output_path}\n\n"
                        "Please close the document in Microsoft Word "
                        "and try again."
                    ),
                )
                return

        word = win32com.client.Dispatch("Word.Application")
        word.Visible = True

        doc = word.Documents.Add()

        doc.ActiveWindow.Caption = f"Submission - {uid}"

        # Wordのカーソル
        selection = word.Selection

        # 文書先頭にカーソルを置く
        selection.SetRange(doc.Content.Start, doc.Content.Start)

        # 1行目
        selection.TypeText("Embedded Files:")

        # Enter → 2行目へ
        selection.TypeParagraph()

        # この時点でカーソルは2行目
        for file_path in paths:
            file_path = os.path.abspath(file_path)

            # File埋め込み
            ole = selection.InlineShapes.AddOLEObject(
                ClassType="Package",
                FileName=file_path,
                LinkToFile=False,
                DisplayAsIcon=True,
                IconLabel=os.path.basename(file_path),
            )

            # アイコン表示は前回正常だった設定を維持
            ole.OLEFormat.DisplayAsIcon = True
            ole.OLEFormat.IconLabel = os.path.basename(file_path)

            # カーソルを今追加したOLEの「直後」へ移動
            selection.SetRange(ole.Range.End, ole.Range.End)

        # 最後に次の行へ
        if paths:
            selection.TypeParagraph()

        doc.SaveAs2(f"{desktop_path}\\APC\\Submission - {uid}.docx")

        # 送信フォーム開いたりするページの作成
        QWidget().setLayout(self.layout())
        l = QVBoxLayout()
        dtlbl_h = QLabel(self, text=f"Steps to submit Deliverables:")
        dtlbl_h.setStyleSheet("""
        QLabel {
            font-size: 22px;
            font-weight: bold;
        }                      
        """)
        dtlbl_1 = QLabel(self, text=f"1. Sign into FormSG with SingPass")
        dtlbl_2 = QLabel(
            self,
            text=f'2. Drag and drop/Attached generated word document in APC file(<a href="{desktop_path}\\APC\\Submission - {uid}.docx">{desktop_path}\\APC\\Submission - {uid}.docx</a>)',
        )
        dtlbl_3 = QLabel(self, text=f'3. Click "Submit"')
        l.addWidget(dtlbl_h)
        l.addWidget(dtlbl_1)
        l.addWidget(dtlbl_2)
        l.addWidget(dtlbl_3)

        footer_btns = QWidget(self)
        footer_btns_layout = QHBoxLayout(footer_btns)
        go_back = QPushButton(self, text="Go Back")
        go_back.clicked.connect(self.submitUI)
        footer_btns_layout.addWidget(go_back)
        open_formsg = QPushButton(self, text="Open FormSG")
        open_formsg.clicked.connect(self.open_formsg_link)
        footer_btns_layout.addWidget(open_formsg)

        l.addWidget(footer_btns)

        self.setLayout(l)

    def open_formsg_link(self):
        webbrowser.open(self.courseInfo.get("submitFormUrl"))

    @Slot(QModelIndex)
    def on_treeView_fileTreeSelector_clicked(self, index):
        print("tree clicked: {}".format(self.model.filePath(index)))
        self.model.traverseDirectory(index, callback=self.model.printIndex)

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
