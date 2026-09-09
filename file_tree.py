from PySide6 import QtWidgets, QtCore
import os

class FileTreeSelectorModel(QtWidgets.QFileSystemModel):
    def __init__(self, parent=None, rootpath="/"):
        QtWidgets.QFileSystemModel.__init__(self, None)
        self.root_path = rootpath
        self.checks = {}
        self.nodestack = []
        self.parent_index = self.setRootPath(self.root_path)
        self.root_index = self.index(self.root_path)

        self.setFilter(
            QtCore.QDir.AllEntries
            | QtCore.QDir.Hidden
            | QtCore.QDir.NoDot
            | QtCore.QDir.NoDotAndDotDot
        )
        self.directoryLoaded.connect(self._loaded)

    def _loaded(self, path):
        print("_loaded", self.root_path, self.rowCount(self.parent_index))

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.CheckStateRole:
            return QtWidgets.QFileSystemModel.data(self, index, role)
        else:
            if index.column() == 0:
                return self.checkState(index)

    def flags(self, index):
        return (
            QtWidgets.QFileSystemModel.flags(self, index)
            | QtCore.Qt.ItemIsUserCheckable
        )

    def checkState(self, index):
        return self.checks.get(
            self.filePath(index),
            QtCore.Qt.CheckState.Unchecked
        )

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if role == QtCore.Qt.CheckStateRole and index.column() == 0:
            path = self.filePath(index)
    
            self.checks[path] = value
    
            # ディレクトリが操作された場合
            if self.isDir(index):
                iterator = QtCore.QDirIterator(
                    path,
                    QtCore.QDir.AllEntries
                    | QtCore.QDir.Hidden
                    | QtCore.QDir.NoDotAndDotDot,
                    QtCore.QDirIterator.Subdirectories
                )
    
                while iterator.hasNext():
                    child_path = iterator.next()
                    self.checks[child_path] = value
    
            # 親の状態を再計算
            self.updateParentState(index)
    
            self.layoutChanged.emit()
    
            return True
    
        return super().setData(index, value, role)
    
    def updateParentState(self, index):
        parent = index.parent()

        while parent.isValid():
            parent_path = self.filePath(parent)

            # 親ディレクトリ直下の子を取得
            directory = QtCore.QDir(parent_path)
            entries = directory.entryInfoList(
                QtCore.QDir.AllEntries
                | QtCore.QDir.Hidden
                | QtCore.QDir.NoDotAndDotDot
            )

            states = []

            for entry in entries:
                child_path = entry.absoluteFilePath()

                state = self.checks.get(
                    child_path,
                    QtCore.Qt.Unchecked
                )

                states.append(state)

            if not states:
                parent_state = QtCore.Qt.Unchecked

            elif all(state == QtCore.Qt.Checked for state in states):
                # 全部Checked
                parent_state = QtCore.Qt.Checked

            elif all(state == QtCore.Qt.Unchecked for state in states):
                # 全部Unchecked
                parent_state = QtCore.Qt.Unchecked

            else:
                # Checked / Uncheckedが混在
                parent_state = QtCore.Qt.PartiallyChecked

            self.checks[parent_path] = parent_state

            self.dataChanged.emit(
                parent,
                parent,
                [QtCore.Qt.CheckStateRole]
            )

            # さらに上の親も更新
            parent = parent.parent()

    def traverseDirectory(self, parentindex, callback=None):
        print("traverseDirectory():")
        callback(parentindex)
        if self.hasChildren(parentindex):
            path = self.filePath(parentindex)
            it = QtCore.QDirIterator(path, self.filter() | QtCore.QDir.NoDotAndDotDot)
            while it.hasNext():
                childIndex = self.index(it.next())
                self.traverseDirectory(childIndex, callback=callback)
        else:
            print("no children")

    def printIndex(self, index):
        print("model printIndex(): {}".format(self.filePath(index)))

    def getCheckedFilepaths(self):
        paths = []
        # print(self.checks)

        for key in self.checks:
            if self.checks[key] == 2 and os.path.isfile(key):
                paths.append(key)

        return paths
