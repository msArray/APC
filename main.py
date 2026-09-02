import os.path
import webbrowser

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import *

import pandas as pd
import datetime

SCOPES = ["https://www.googleapis.com/auth/drive"]
FILE_ID = "1NWb-HJxqwAPqQKzNxqZGQg8DRV0N5UwLBe0pT4FFKqM"
FILE_NAME = "APC"


class Window(QWidget):
    def __init__(self):
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

    def UIinit(self):
        self.login_layout = QFormLayout()
        self.login_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel(self, text="APC")
        self.label.setStyleSheet("font-size: 24px; font-weight: 600;")
        self.login_layout.addRow(self.label)

        self.courseId_label = QLabel(self, text="Enter Course ID")

        self.courseId_Input = QLineEdit(self)
        self.courseId_Input.setFixedWidth(250)
        self.login_layout.addRow(self.courseId_label, self.courseId_Input)

        self.startDate_label = QLabel(self, text="Enter Start Date")
        self.startDate_Input = QDateEdit(self)
        self.startDate_Input.setDisplayFormat("d/M/yyyy")
        self.startDate_Input.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.startDate_Input.setFixedWidth(250)
        self.login_layout.addRow(self.startDate_label, self.startDate_Input)

        self.search_course_btn = QPushButton(self, text="Login")
        self.search_course_btn.setFixedWidth(120)
        self.search_course_btn.clicked.connect(self.search_course)
        self.login_layout.addRow(self.search_course_btn)
        self.show()

        self.setLayout(self.login_layout)

    def submitUI(self, courseId):
        QWidget().setLayout(self.layout())
        self.submit_layout = QGridLayout(self)

        self.cleanup_btn = QPushButton(self, text="Clean UP")
        self.submit_layout.addWidget(self.cleanup_btn, 0, 0)
        self.cleanup_btn.clicked.connect(self.cleanup_action)

        self.setup_btn = QPushButton(self, text="SetUp")
        self.setup_btn.clicked.connect(self.setup_action)
        self.submit_layout.addWidget(self.setup_btn, 1, 0)

        self.open_submit_btn = QPushButton(self, text="Submit")
        self.submit_layout.addWidget(self.open_submit_btn, 0, 1)
        self.open_submit_btn.clicked.connect(self.o_submit_act)

        self.open_survey_btn = QPushButton(self, text="Survey")
        self.submit_layout.addWidget(self.open_survey_btn, 1, 1)
        self.open_survey_btn.clicked.connect(self.o_survey_act)

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
            # print(
            #     self.startDate_Input.text() == df.iloc[idx].get("startDate"),
            #     self.startDate_Input.text(),
            #     df.iloc[idx].get("startDate"),
            # )
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
                courseId = DBcourseId
                self.courseInfo = df.iloc[idx]

        if isMatch:
            self.submitUI(courseId)

    def cleanup_action(self):
        pass

    def setup_action(self):
        desktop_path = os.path.join(os.path.join(os.environ["USERPROFILE"]), "Desktop")

        if not os.path.exists(f"{desktop_path}/APC"):
            os.makedirs(f"{desktop_path}/APC")

    def o_submit_act(self):
        webbrowser.open(self.courseInfo.get("submitFormUrl"))
        pass

    def o_survey_act(self):
        webbrowser.open(self.courseInfo.get("surveyFormUrl"))
        pass


def main():
    App = QApplication(sys.argv)

    creds = None
    if os.path.exists("credentials.json"):
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    else:
        exit(-1)

    try:
        service = build("drive", "v3", credentials=creds)

        # Call the Drive v3 API
        results = service.files().export(fileId=FILE_ID, mimeType="text/csv").execute()
        # print(results)
        with open("./" + "APC", "wb") as w_f:
            w_f.write(results)

    except HttpError as error:
        # TODO(developer) - Handle errors from drive API.
        print(f"An error occurred: {error}")

    Window()
    sys.exit(App.exec())


if __name__ == "__main__":
    main()
