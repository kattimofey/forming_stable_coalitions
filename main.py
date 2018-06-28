import sys

from PyQt5.QtWidgets import QApplication

from widgets import StartWindow


if __name__ == '__main__':
    app = QApplication(sys.argv)
    StartWindow()
    sys.exit(app.exec_())
