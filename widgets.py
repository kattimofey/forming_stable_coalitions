import abc
import os
import sys
import time

import numpy as np
from PyQt5 import QtCore, uic
from PyQt5.QtGui import QIcon, QDoubleValidator, QRegExpValidator
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QWidget, QDesktopWidget, QTableWidget,\
    QTableWidgetItem, QMessageBox, QItemDelegate, QLineEdit

from const import PRECISION, DECIMALS_COUNT, LEMKE_TITLE, START_TITLE,\
    TASK_TITLE, FIRST_STEP_TITLE, SECOND_STEP_TITLE, THIRD_STEP_TITLE, \
    FOURTH_STEP_TITLE, FINAL_TITLE, QUIT_TITLE, QUIT_MSG, ERROR_TITLE,\
    ERROR_MSG, EMPTY_FIELDS_TITLE, EMPTY_FIELDS_MSG, INFO_TITLE, INFO_MSG, \
    FINISH_TITLE, FINISH_MSG, PASTE_ERROR_TITLE, PASTE_ERROR_MSG, CALC_HINT,\
    YES, NO, GAME_1vs23, GAME_12vs3, GAME_13vs2, ALL_GAMES, ESSENTIAL, \
    NOT_ESSENTIAL, GAMES_UNSTABLE, TRANSPARENT_BUTTON_STYLE,\
    DEFAULT_COLUMN_WIDTH, DEFAULT_ROW_HEIGHT, SHOW_TIME
from data import VARIANTS
from lemke_algorithm import calc_game_winnings


DOUBLE_VALIDATOR = QDoubleValidator(decimals=DECIMALS_COUNT)
RUSSIAN_LETTERS_VALIDATOR = QRegExpValidator(QtCore.QRegExp('[А-я]+'))


def is_close(a, b, tolerance=PRECISION):
    """Проверить два числа на приблизительное равенство"""
    return round(abs(a-b), DECIMALS_COUNT) <= tolerance


def transpose(mat):
    """Транспонировать матрицу

    :param mat: Матрица
    :type mat: list of list
    """
    return np.array(mat).transpose().tolist()


def str_to_float(string):
    """Проеобразовать str к float с заменой ',' -> '.'

    :param string: Строка для преобразования (содержащая цифры и разделитель)
    :type string: str
    :return: Число с плавающей точкой или None для пустой строки
    :rtype: float or None
    """
    if not string:
        return None
    return float(string.replace(',', '.'))


# Делегат для установки валидатора на поля таблиц
class TableDelegate(QItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setValidator(DOUBLE_VALIDATOR)
        return editor


class MainWidget(QWidget):
    """Основной класс, от которого наследуются окна"""
    __metaclass__ = abc.ABCMeta

    variant = None  # Номер варианта работы (str)
    surname = None  # Фамилия студента
    group = None  # Группа студента
    start_time = None  # Время начала теста

    errors = 0
    errors_on_step = {
        1: 0,
        2: 0,
        3: 0,
        4: 0,
    }

    prev_window = None
    next_window = None

    # Для хранения скопированных в буфер таблиц
    tmp_table = None

    # Текущая устойчивая конфигурация
    current_stable_game = None

    # Еще не рассмотренные коалиции при поиске устойчивой
    remained_games = [GAME_12vs3, GAME_13vs2, GAME_1vs23]

    # Выигрыши игроков в биматричных играх
    bimatrix_h = {}

    # Выигрыши в некооперативной игре (пользовательские)
    no_coop_winnings_user = {}

    # Хар. функции кооперативных игр (пользовательские)
    coop_winnings_user = {}

    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon('lib/images/tool_icon.png'))
        with open('lib/styles/base_style.qss', "r") as f:
            self.setStyleSheet(f.read())

    def prev(self):
        """Переключить на преыдущее окно"""
        pass

    def next(self):
        """Переключить на следующее окно"""
        pass

    def disable(self):
        """Деактивировать окно"""
        pass

    def open_lemke_method(self):
        """Открыть окно с методом Лемке-Хоусона"""
        LemkeWindow(self)

    def init_base_elements(self):
        """Инициализировать основные элементы окна"""
        self.prevButton.clicked.connect(self.prev)
        self.nextButton.clicked.connect(self.next)
        self.calcButton.clicked.connect(self.open_calc)
        self.lemkeButton.clicked.connect(self.open_lemke_method)
        self.calcButton.setToolTip(CALC_HINT)
        self.calcButton.setStyleSheet(TRANSPARENT_BUTTON_STYLE)
        self.errorsLine.setText(str(self.errors))

    def hide_base_elements(self):
        """Скрыть основные элементы окна"""
        self.errorsLabel.hide()
        self.errorsLine.hide()
        self.lemkeButton.hide()
        self.calcButton.hide()

    def move_center(self):
        """Переместить окно в центр экрана"""
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def move_top_left(self):
        """Переместить окно в левый верхний угол"""
        self.move(0, 0)

    def disable_base_buttons(self):
        """Отключить основные кнопки"""
        self.lemkeButton.setDisabled(True)
        self.nextButton.setDisabled(True)
        self.prevButton.setDisabled(True)

    def enable_base_buttons(self):
        """Включить основные кнопки"""
        self.lemkeButton.setEnabled(True)
        self.nextButton.setEnabled(True)
        self.prevButton.setEnabled(True)

    def show_success_icon(self):
        """Показать иконку об успешной проверке"""
        self.disable_base_buttons()
        self.okLabel.raise_()
        QTest.qWait(SHOW_TIME)
        self.okLabel.lower()
        self.enable_base_buttons()

    def show_instead(self, window):
        """Показать окно window вместо текущего

        :param window: Окно, которое будет показано
        :type window: QWidget object
        """
        self.hide()
        window.setGeometry(self.geometry())
        window.showNormal()

    def update_errors(self, step):
        """Увеличить число ошибок и отобразить новое число

        :param step: Номер шага, на котором была допущена ошибка
        :type step: int
        """
        MainWidget.errors += 1
        MainWidget.errors_on_step[step] += 1
        self.errorsLine.setText(str(self.errors))

    def hide_with_success(self):
        """Спрятать окно, предварительно отобразив иконку об упешной проверке"""
        self.disable()
        self.show_success_icon()
        self.hide()

    @staticmethod
    def open_calc():
        """Открыть калькулятор"""
        os.system('calc.exe')

    @staticmethod
    def check_user_matrix(mat1, mat2, matrix, user_matrix):
        """Проверить правильность матрицы, введенной пользователем
        (также считает и формирует правильную матрицы - matrix)

        :param mat1: Матрица 1 для вычисления матрицы matrix
        :param mat2: Матрица 2 для вычисления матрицы matrix
        :param matrix: Правильная матрица
        :param user_matrix: Матрица, введенная пользователем
        :return: True, если матрица пользователя верная, иначе - False
        """
        k = 0
        for row1 in mat1:
            for row2 in mat2:
                # Расчет k-ой строки для сравнения
                k_row = [row1[i] + row2[i] for i in range(2)]

                # Проверка k-ой строки
                for idx, elem in enumerate(k_row):
                    if not is_close(elem, user_matrix[k][idx]):
                        return False

                matrix.append(k_row)
                k += 1

        return True

    # ToDo: Вынести в кастомный класс MyTableWidget
    @staticmethod
    def check_table_filling(table):
        """Проверить полностью ли заполнена таблица

        :param table: Таблица для проверки
        :type table: QTableWidget object
        :return: True, если таблица заполнена, иначе - False
        """
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                if table.item(row, col) is None or \
                        not table.item(row, col).text():
                    return False

        return True

    # ToDo: Вынести в кастомный класс MyTableWidget
    @staticmethod
    def table_to_matrix(table):
        """Преобразовать таблицу к матрице

        :param table: Таблица, которую требуется преобразовать
        :type table: QTableWidget object
        :return: Матрица
        :rtype: list of list
        """
        matrix = []
        for row in range(table.rowCount()):
            matrix.append([])
            for col in range(table.columnCount()):
                matrix[row].append(str_to_float(table.item(row, col).text()))

        return matrix

    # ToDo: Вынести в кастомный класс MyTableWidget
    @staticmethod
    def set_cells_size(table, col_width=DEFAULT_COLUMN_WIDTH,
                       row_height=DEFAULT_ROW_HEIGHT):
        """Задать размер клеток таблицы

        :param table: Таблица, для которой требуется задать размер клеток
        :type table: QTableWidget object
        :param col_width: Ширина столбцов
        :param row_height: Высота строк
        """
        for i in range(table.columnCount()):
            table.setColumnWidth(i, col_width)

        for i in range(table.rowCount()):
            table.setRowHeight(i, row_height)

    # ToDo: Вынести в кастомный класс MyTableWidget
    @staticmethod
    def set_table_text_alignment(table, alignment=QtCore.Qt.AlignCenter):
        """Задать выравнивание текста в таблице

        :param table: Таблица, для которой требуется задать выравнивание
        :type table: QTableWidget object
        :param alignment: Тип выравнивания
        :type alignment: int
        """
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                table.item(row, col).setTextAlignment(alignment)

    # ToDo: Вынести в кастомный класс MyTableWidget
    @staticmethod
    def copy_table(table):
        """Копировать таблицу в буфер

        :param table: Таблица, которую требуется копировать
        :type table: QTableWidget object
        """
        MainWidget.tmp_table = QTableWidget(table.rowCount(),
                                            table.columnCount())

        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                text = table.item(row, col).text() if \
                    table.item(row, col) else ''

                MainWidget.tmp_table.setItem(row, col, QTableWidgetItem(text))

    # ToDo: Вынести в кастомный класс MyTableWidget
    def paste_to_table(self, table, set_alignment=True):
        """Вставить таблицу из буфера в таблицу table

        :param table: Таблица, в которую требуется вставить
        :type table: QTableWidget object
        :param set_alignment: True, если нужно задать выравнивание после вставки
        """
        if not self.tmp_table:
            return

        if not (self.tmp_table.rowCount() == table.rowCount() and
                self.tmp_table.columnCount() == table.columnCount()):
            QMessageBox.information(
                self, PASTE_ERROR_TITLE, PASTE_ERROR_MSG, QMessageBox.Ok
            )
            return

        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                table.setItem(
                    row, col,
                    QTableWidgetItem(self.tmp_table.item(row, col).text())
                )

        if set_alignment:
            self.set_table_text_alignment(table)

    def closeEvent(self, event):
        if not event.spontaneous():
            event.accept()
        else:
            reply = QMessageBox.question(
                self, QUIT_TITLE, QUIT_MSG, QMessageBox.Yes, QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                event.accept()
                sys.exit()
            else:
                event.ignore()


class LemkeWindow(MainWidget):
    """Окно с методом Лемке-Хоусона"""
    def __init__(self, calling_window):
        super().__init__()
        self.ui = uic.loadUi('lib/ui/lemke.ui', self)
        self.initUI(calling_window)

    def initUI(self, calling_window):
        self.setWindowTitle(LEMKE_TITLE)
        self.setGeometry(calling_window.geometry())
        self.setFixedSize(1000, 420)
        self.init_copy_paste_buttons()

        self.resizeButton_2x2.clicked.connect(lambda: self.resize_tables(2, 2))
        self.resizeButton_2x4.clicked.connect(lambda: self.resize_tables(2, 4))
        self.resizeButton_4x2.clicked.connect(lambda: self.resize_tables(4, 2))

        self.clearButton.clicked.connect(self.clear)
        self.solveButton.clicked.connect(self.solve)

        delegate = TableDelegate()
        self.tableA.setItemDelegate(delegate)
        self.tableB.setItemDelegate(delegate)

        self.resize_tables(2, 2)  # По умолчанию размер 2x2
        self.show()

    def init_copy_paste_buttons(self):
        """Инициализировать кнопки для копирования/вставки таблиц"""
        self.copyButton_A.clicked.connect(
            lambda: self.copy_table(self.tableA)
        )
        self.pasteButton_A.clicked.connect(
            lambda: self.paste_to_table(self.tableA, set_alignment=False)
        )
        self.copyButton_B.clicked.connect(
            lambda: self.copy_table(self.tableB)
        )
        self.pasteButton_B.clicked.connect(
            lambda: self.paste_to_table(self.tableB, set_alignment=False)
        )

        self.copyButton_A.setStyleSheet(TRANSPARENT_BUTTON_STYLE)
        self.pasteButton_A.setStyleSheet(TRANSPARENT_BUTTON_STYLE)
        self.copyButton_B.setStyleSheet(TRANSPARENT_BUTTON_STYLE)
        self.pasteButton_B.setStyleSheet(TRANSPARENT_BUTTON_STYLE)

    def resize_tables(self, rows, cols):
        """Изменить размер таблиц

        :param rows: Количество строк
        :param cols: Количество столбцов
        """
        self.tableA.setRowCount(rows)
        self.tableA.setColumnCount(cols)
        self.tableB.setRowCount(rows)
        self.tableB.setColumnCount(cols)
        self.set_cells_size(self.tableA)
        self.set_cells_size(self.tableB)

    def clear(self):
        """Очистить таблицы и прошлые результаты"""
        self.tableA.clear()
        self.tableB.clear()
        self.h_aLine.setText('')
        self.h_bLine.setText('')

    def solve(self):
        """Решить биматричную игру"""
        if not (self.check_table_filling(self.tableA) and
                self.check_table_filling(self.tableB)):
            QMessageBox.information(
                self, EMPTY_FIELDS_TITLE, EMPTY_FIELDS_MSG, QMessageBox.Ok
            )
            return

        h_a, h_b = calc_game_winnings(self.table_to_matrix(self.tableA),
                                      self.table_to_matrix(self.tableB))

        self.h_aLine.setText('{0:.2f}'.format(h_a))
        self.h_bLine.setText('{0:.2f}'.format(h_b))

    def closeEvent(self, event):
        event.accept()


class StartWindow(MainWidget):
    """Начальное окно с выбором варианта"""
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi('lib/ui/start.ui', self)
        self.initUI()

        self.anim_group = QtCore.QParallelAnimationGroup()
        self.left_anim = QtCore.QPropertyAnimation(self.leftHandLabel,
                                                   b'geometry')
        self.right_anim = QtCore.QPropertyAnimation(self.rightHandLabel,
                                                    b'geometry')
        self.animation_start()

    def initUI(self):
        self.setWindowTitle(START_TITLE)
        self.setFixedSize(1000, 600)
        self.move_center()

        for variant_number in VARIANTS.keys():
            self.variantsBox.addItem(variant_number)

        self.surnameLine.setValidator(RUSSIAN_LETTERS_VALIDATOR)
        self.startButton.clicked.connect(self.start)
        self.show()

    def animation_start(self, duration=1500):
        """Запустить анимацию"""
        self.left_anim.setDuration(duration)
        self.left_anim.setStartValue(QtCore.QRect(-450, 240, 401, 261))
        self.left_anim.setEndValue(QtCore.QRect(-80, 240, 401, 261))

        self.right_anim.setDuration(duration)
        self.right_anim.setStartValue(QtCore.QRect(1000, 220, 391, 281))
        self.right_anim.setEndValue(QtCore.QRect(670, 220, 391, 281))

        self.anim_group.addAnimation(self.left_anim)
        self.anim_group.addAnimation(self.right_anim)
        self.anim_group.start()

    @staticmethod
    def generate_password(surname):
        """Сгенерировать пароль на основе фамилии

        :param surname: Фамилия
        :return: '<Последняя_буква_фамилии>астра<Первая_буква_фамилии>'
        """
        return '{}астра{}'.format(surname[-1], surname[0]).lower()

    def start(self):
        """Начать выполнение теста"""
        group = self.groupLine.text()
        surname = self.surnameLine.text()

        if not (group and surname):
            QMessageBox.information(
                self, EMPTY_FIELDS_TITLE, EMPTY_FIELDS_MSG, QMessageBox.Ok
            )
            return

        if self.passwordLine.text().lower() == self.generate_password(surname):
            MainWidget.variant = self.variantsBox.currentText()
            MainWidget.surname = surname
            MainWidget.group = group
            MainWidget.start_time = time.time()
            self.close()

            TaskWindow()
            FirstStepWindow()

    def closeEvent(self, event):
        event.accept()


class TaskWindow(MainWidget):
    """Окно с заданием"""
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi('lib/ui/task.ui', self)
        with open('lib/styles/task_style.qss', "r") as f:
            self.setStyleSheet(f.read())
        self.initUI()

    def initUI(self):
        self.setWindowTitle(TASK_TITLE.format(self.variant))
        self.setFixedSize(880, 740)
        self.move_top_left()
        self.init_copy_paste_buttons()
        self.load_variant()
        self.show()

    def init_copy_paste_buttons(self):
        """Инициализировать кнопки для копирования/вставки таблиц"""
        self.copyButton_1vs2_1.clicked.connect(
            lambda: self.copy_table(self.table_1vs2_1)
        )
        self.copyButton_1vs2_2.clicked.connect(
            lambda: self.copy_table(self.table_1vs2_2)
        )
        self.copyButton_1vs3_1.clicked.connect(
            lambda: self.copy_table(self.table_1vs3_1)
        )
        self.copyButton_1vs3_2.clicked.connect(
            lambda: self.copy_table(self.table_1vs3_2)
        )
        self.copyButton_2vs3_1.clicked.connect(
            lambda: self.copy_table(self.table_2vs3_1)
        )
        self.copyButton_2vs3_2.clicked.connect(
            lambda: self.copy_table(self.table_2vs3_2)
        )

    def load_variant(self):
        """Загрузить вариант работы"""
        data = VARIANTS[self.variant]

        # Заполнение всех таблиц для игр: 1vs2, 1vs3, 2vs3
        for row in range(2):
            for col in range(2):
                # Таблицы 1 vs 2
                self.table_1vs2_1.setItem(
                    row, col, QTableWidgetItem(str(data['1vs2'][0][row][col]))
                )
                self.table_1vs2_2.setItem(
                    row, col, QTableWidgetItem(str(data['1vs2'][1][row][col]))
                )

                # Таблицы 1 vs 3
                self.table_1vs3_1.setItem(
                    row, col, QTableWidgetItem(str(data['1vs3'][0][row][col]))
                )
                self.table_1vs3_2.setItem(
                    row, col, QTableWidgetItem(str(data['1vs3'][1][row][col]))
                )

                # Таблицы 2 vs 3
                self.table_2vs3_1.setItem(
                    row, col, QTableWidgetItem(str(data['2vs3'][0][row][col]))
                )
                self.table_2vs3_2.setItem(
                    row, col, QTableWidgetItem(str(data['2vs3'][1][row][col]))
                )

        # Задать размеры клеток таблиц
        self.set_cells_size(self.table_1vs2_1)
        self.set_cells_size(self.table_1vs2_2)
        self.set_cells_size(self.table_1vs3_1)
        self.set_cells_size(self.table_1vs3_2)
        self.set_cells_size(self.table_2vs3_1)
        self.set_cells_size(self.table_2vs3_2)

        # Задать выравнивание текста в таблицах
        self.set_table_text_alignment(self.table_1vs2_1)
        self.set_table_text_alignment(self.table_1vs2_2)
        self.set_table_text_alignment(self.table_1vs3_1)
        self.set_table_text_alignment(self.table_1vs3_2)
        self.set_table_text_alignment(self.table_2vs3_1)
        self.set_table_text_alignment(self.table_2vs3_2)

    def closeEvent(self, event):
        if event.spontaneous():
            event.ignore()
        else:
            event.accept()


class FirstStepWindow(MainWidget):
    """Окно с первым шагом: Определение индивидуальных выигрышей"""
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi('lib/ui/first_step.ui', self)
        self.initUI()

    def initUI(self):
        self.setWindowTitle(FIRST_STEP_TITLE)
        self.setFixedSize(1000, 600)
        self.move_center()
        self.init_base_elements()
        self.prevButton.hide()

        self.v1Line.setValidator(DOUBLE_VALIDATOR)
        self.v2Line.setValidator(DOUBLE_VALIDATOR)
        self.v3Line.setValidator(DOUBLE_VALIDATOR)
        self.vNLine.setValidator(DOUBLE_VALIDATOR)

        self.show()
        QMessageBox.information(self, INFO_TITLE, INFO_MSG, QMessageBox.Ok)

    def disable(self):
        self.hide_base_elements()
        self.v1Line.setDisabled(True)
        self.v2Line.setDisabled(True)
        self.v3Line.setDisabled(True)
        self.vNLine.setDisabled(True)

    def check_solution(self, v1_user, v2_user, v3_user, vN_user):
        """Проверка решения

        :param v1_user: Индивидуальный выигрыш 1 игрока (пользовательское)
        :param v2_user: Индивидуальный выигрыш 2 игрока (пользовательское)
        :param v3_user: Индивидуальный выигрыш 3 игрока (пользовательское)
        :param vN_user: Характеристическая функция игры (пользовательское)
        :return: True, если все ответы верные, иначе - False
        """
        data = VARIANTS[self.variant]

        h1_1vs2, h2_1vs2 = calc_game_winnings(data['1vs2'][0], data['1vs2'][1])
        h1_1vs3, h3_1vs3 = calc_game_winnings(data['1vs3'][0], data['1vs3'][1])
        h2_2vs3, h3_2vs3 = calc_game_winnings(data['2vs3'][0], data['2vs3'][1])

        v1 = (h1_1vs2 + h1_1vs3) / 2
        v2 = (h2_1vs2 + h2_2vs3) / 2
        v3 = (h3_1vs3 + h3_2vs3) / 2
        vN = v1 + v2 + v3

        if not is_close(v1, v1_user):
            return False
        if not is_close(v2, v2_user):
            return False
        if not is_close(v3, v3_user):
            return False
        if not is_close(vN, vN_user, tolerance=PRECISION*3):
            return False

        # Сохранить информацию для дальнейших шагов
        MainWidget.bimatrix_h = dict(
            h1_1vs2=h1_1vs2, h2_1vs2=h2_1vs2,
            h1_1vs3=h1_1vs3, h3_1vs3=h3_1vs3,
            h2_2vs3=h2_2vs3, h3_2vs3=h3_2vs3,
        )
        MainWidget.no_coop_winnings_user = dict(
            v1=v1_user, v2=v2_user, v3=v3_user, vN=vN_user,
        )

        return True

    def next(self):
        if self.next_window:
            self.show_instead(self.next_window)
            return

        v1 = str_to_float(self.v1Line.text())
        v2 = str_to_float(self.v2Line.text())
        v3 = str_to_float(self.v3Line.text())
        vN = str_to_float(self.vNLine.text())

        if any(item is None for item in [v1, v2, v3, vN]):
            QMessageBox.information(
                self, EMPTY_FIELDS_TITLE, EMPTY_FIELDS_MSG, QMessageBox.Ok
            )
            return

        if not self.check_solution(v1, v2, v3, vN):
            self.update_errors(step=1)
            QMessageBox.critical(self, ERROR_TITLE, ERROR_MSG, QMessageBox.Ok)
        else:
            self.hide_with_success()
            self.next_window = SecondStepWindowOne(self)


class SecondStepWindowOne(MainWidget):
    """Окно со вторым шагом №1: Рассмотрение коалиции 1 и 2 игроков"""
    def __init__(self, prev_window):
        super().__init__()
        self.ui = uic.loadUi('lib/ui/second_step_one.ui', self)
        self.prev_window = prev_window
        self.initUI()

    def initUI(self):
        self.setWindowTitle(SECOND_STEP_TITLE)
        self.setGeometry(self.prev_window.geometry())
        self.setFixedSize(1000, 600)
        self.init_base_elements()
        self.init_copy_paste_buttons()

        self.v12Line.setValidator(DOUBLE_VALIDATOR)
        self.v3Line.setValidator(DOUBLE_VALIDATOR)
        self.vNLine.setValidator(DOUBLE_VALIDATOR)

        delegate = TableDelegate()
        self.tableA12.setItemDelegate(delegate)
        self.tableA3.setItemDelegate(delegate)
        self.set_cells_size(self.tableA12)
        self.set_cells_size(self.tableA3)

        self.show()

    def init_copy_paste_buttons(self):
        """Инициализировать кнопки для копирования/вставки таблиц"""
        self.copyButton_A12.clicked.connect(
            lambda: self.copy_table(self.tableA12)
        )
        self.pasteButton_A12.clicked.connect(
            lambda: self.paste_to_table(self.tableA12)
        )
        self.copyButton_A3.clicked.connect(
            lambda: self.copy_table(self.tableA3)
        )
        self.pasteButton_A3.clicked.connect(
            lambda: self.paste_to_table(self.tableA3)
        )

        self.copyButton_A12.setStyleSheet(TRANSPARENT_BUTTON_STYLE)
        self.pasteButton_A12.setStyleSheet(TRANSPARENT_BUTTON_STYLE)
        self.copyButton_A3.setStyleSheet(TRANSPARENT_BUTTON_STYLE)
        self.pasteButton_A3.setStyleSheet(TRANSPARENT_BUTTON_STYLE)

    def disable(self):
        self.hide_base_elements()
        self.tableA12.setDisabled(True)
        self.tableA3.setDisabled(True)
        self.v12Line.setDisabled(True)
        self.v3Line.setDisabled(True)
        self.vNLine.setDisabled(True)
        self.variantsBox.setDisabled(True)

    def check_solution(self, v12_user, v3_user, vN_user,
                       is_essential_user, matrix_a12_user, matrix_a3_user):
        """Проверка решения

        :param v12_user: Выигрыш коалиции 1 и 2 игроков (пользовательское)
        :param v3_user: Выигрыш 3 игрока в данной игре (пользовательское)
        :param vN_user: Характеристическая функция игры (пользовательское)
        :param is_essential_user: Существенность игры (пользовательское)
        :param matrix_a12_user: Матрица для коалиции 1 и 2 игроков
        (пользовательское)
        :param matrix_a3_user: Матрица для 3 игрока (пользовательское)
        :return: True, если все ответы верные, иначе - False
        """
        data = VARIANTS[self.variant]
        game_1vs3 = data['1vs3']
        game_2vs3 = data['2vs3']

        # Правильные матрицы для сравнения с ответом, формируются при проверке
        matrix_a12, matrix_a3 = [], []

        if not self.check_user_matrix(game_1vs3[0], game_2vs3[0],
                                      matrix_a12, matrix_a12_user):
            return False
        if not self.check_user_matrix(game_1vs3[1], game_2vs3[1],
                                      matrix_a3, matrix_a3_user):
            return False

        v12, v3 = calc_game_winnings(matrix_a12, matrix_a3)
        vN = v12 + v3

        if not is_close(v12, v12_user):
            return False
        if not is_close(v3, v3_user):
            return False
        if not is_close(vN, vN_user, tolerance=PRECISION*2):
            return False

        is_essential = YES if vN_user > self.no_coop_winnings_user['vN'] else NO
        if is_essential != is_essential_user:
            return False

        # Сохранить информацию для дальнейших шагов
        MainWidget.coop_winnings_user['12vs3'] = dict(
            v12=v12_user, v3=v3_user, vN=vN_user,
        )
        MainWidget.coop_winnings_user['12vs3']['is_essential'] = \
            True if is_essential == YES else False

        return True

    def next(self):
        if self.next_window:
            self.show_instead(self.next_window)
            return

        v12 = str_to_float(self.v12Line.text())
        v3 = str_to_float(self.v3Line.text())
        vN = str_to_float(self.vNLine.text())
        is_essential = self.variantsBox.currentText() or None

        if all(item is not None for item in [v12, v3, vN, is_essential]) and \
           self.check_table_filling(self.tableA12) and \
           self.check_table_filling(self.tableA3):
                matrix_a12 = self.table_to_matrix(self.tableA12)
                matrix_a3 = self.table_to_matrix(self.tableA3)
        else:
            QMessageBox.information(
                self, EMPTY_FIELDS_TITLE, EMPTY_FIELDS_MSG, QMessageBox.Ok
            )
            return

        solved = self.check_solution(
            v12, v3, vN, is_essential, matrix_a12, matrix_a3
        )
        if not solved:
            self.update_errors(step=2)
            QMessageBox.critical(self, ERROR_TITLE, ERROR_MSG, QMessageBox.Ok)
        else:
            self.hide_with_success()
            self.next_window = SecondStepWindowTwo(self)

    def prev(self):
        self.show_instead(self.prev_window)


class SecondStepWindowTwo(MainWidget):
    """Окно со вторым шагом №2: Рассмотрение коалиции 1 и 3 игроков"""
    def __init__(self, prev_window):
        super().__init__()
        self.ui = uic.loadUi('lib/ui/second_step_two.ui', self)
        self.prev_window = prev_window
        self.initUI()

    def initUI(self):
        self.setWindowTitle(SECOND_STEP_TITLE)
        self.setGeometry(self.prev_window.geometry())
        self.setFixedSize(1000, 600)
        self.init_base_elements()
        self.init_copy_paste_buttons()

        self.v13Line.setValidator(DOUBLE_VALIDATOR)
        self.v2Line.setValidator(DOUBLE_VALIDATOR)
        self.vNLine.setValidator(DOUBLE_VALIDATOR)

        delegate = TableDelegate()
        self.tableA13.setItemDelegate(delegate)
        self.tableA2.setItemDelegate(delegate)
        self.set_cells_size(self.tableA13)
        self.set_cells_size(self.tableA2)

        self.show()

    def init_copy_paste_buttons(self):
        """Инициализировать кнопки для копирования/вставки таблиц"""
        self.copyButton_A13.clicked.connect(
            lambda: self.copy_table(self.tableA13)
        )
        self.pasteButton_A13.clicked.connect(
            lambda: self.paste_to_table(self.tableA13)
        )
        self.copyButton_A2.clicked.connect(
            lambda: self.copy_table(self.tableA2)
        )
        self.pasteButton_A2.clicked.connect(
            lambda: self.paste_to_table(self.tableA2)
        )

        self.copyButton_A13.setStyleSheet(TRANSPARENT_BUTTON_STYLE)
        self.pasteButton_A13.setStyleSheet(TRANSPARENT_BUTTON_STYLE)
        self.copyButton_A2.setStyleSheet(TRANSPARENT_BUTTON_STYLE)
        self.pasteButton_A2.setStyleSheet(TRANSPARENT_BUTTON_STYLE)

    def disable(self):
        self.hide_base_elements()
        self.tableA13.setDisabled(True)
        self.tableA2.setDisabled(True)
        self.v13Line.setDisabled(True)
        self.v2Line.setDisabled(True)
        self.vNLine.setDisabled(True)
        self.variantsBox.setDisabled(True)

    def check_solution(self, v13_user, v2_user, vN_user,
                       is_essential_user, matrix_a13_user, matrix_a2_user):
        """Проверка решения

        :param v13_user: Выигрыш коалиции 1 и 3 игроков (пользовательское)
        :param v2_user: Выигрыш 2 игрока в данной игре (пользовательское)
        :param vN_user: Характеристическая функция игры (пользовательское)
        :param is_essential_user: Существенность игры (пользовательское)
        :param matrix_a13_user: Таблица для коалиции 1 и 3 игроков
        (пользовательское)
        :param matrix_a2_user: Таблица для 2 игрока (пользовательское)
        :return: True, если все ответы верные, иначе - False
        """
        data = VARIANTS[self.variant]
        game_1vs2 = data['1vs2']
        # Получить из игры "2 против 3" -> "3 против 2"
        game_3vs2 = [transpose(mat) for mat in reversed(data['2vs3'])]

        # Правильные матрицы для сравнения с ответом, формируются при проверке
        matrix_a13, matrix_a2 = [], []

        if not self.check_user_matrix(game_1vs2[0], game_3vs2[0],
                                      matrix_a13, matrix_a13_user):
            return False
        if not self.check_user_matrix(game_1vs2[1], game_3vs2[1],
                                      matrix_a2, matrix_a2_user):
            return False

        v13, v2 = calc_game_winnings(matrix_a13, matrix_a2)
        vN = v13 + v2

        if not is_close(v13, v13_user):
            return False
        if not is_close(v2, v2_user):
            return False
        if not is_close(vN, vN_user, tolerance=PRECISION*2):
            return False

        is_essential = YES if vN_user > self.no_coop_winnings_user['vN'] else NO
        if is_essential != is_essential_user:
            return False

        # Сохранить информацию для дальнейших шагов
        MainWidget.coop_winnings_user['13vs2'] = dict(
            v13=v13_user, v2=v2_user, vN=vN_user,
        )
        MainWidget.coop_winnings_user['13vs2']['is_essential'] = \
            True if is_essential == YES else False

        return True

    def next(self):
        if self.next_window:
            self.show_instead(self.next_window)
            return

        v13 = str_to_float(self.v13Line.text())
        v2 = str_to_float(self.v2Line.text())
        vN = str_to_float(self.vNLine.text())
        is_essential = self.variantsBox.currentText() or None

        if all(item is not None for item in [v13, v2, vN, is_essential]) and \
           self.check_table_filling(self.tableA13) and \
           self.check_table_filling(self.tableA2):
                matrix_a13 = self.table_to_matrix(self.tableA13)
                matrix_a2 = self.table_to_matrix(self.tableA2)
        else:
            QMessageBox.information(
                self, EMPTY_FIELDS_TITLE, EMPTY_FIELDS_MSG, QMessageBox.Ok
            )
            return

        solved = self.check_solution(
            v13, v2, vN, is_essential, matrix_a13, matrix_a2
        )
        if not solved:
            self.update_errors(step=2)
            QMessageBox.critical(self, ERROR_TITLE, ERROR_MSG, QMessageBox.Ok)
        else:
            self.hide_with_success()
            self.next_window = SecondStepWindowThree(self)

    def prev(self):
        self.show_instead(self.prev_window)


class SecondStepWindowThree(MainWidget):
    """Окно со вторым шагом №3: Рассмотрение коалиции 2 и 3 игроков"""
    def __init__(self, prev_window):
        super().__init__()
        self.ui = uic.loadUi('lib/ui/second_step_three.ui', self)
        self.prev_window = prev_window
        self.initUI()

    def initUI(self):
        self.setWindowTitle(SECOND_STEP_TITLE)
        self.setGeometry(self.prev_window.geometry())
        self.setFixedSize(1000, 600)
        self.init_base_elements()
        self.init_copy_paste_buttons()

        self.v1Line.setValidator(DOUBLE_VALIDATOR)
        self.v23Line.setValidator(DOUBLE_VALIDATOR)
        self.vNLine.setValidator(DOUBLE_VALIDATOR)

        delegate = TableDelegate()
        self.tableA1.setItemDelegate(delegate)
        self.tableA23.setItemDelegate(delegate)
        self.set_cells_size(self.tableA1)
        self.set_cells_size(self.tableA23)

        self.show()

    def init_copy_paste_buttons(self):
        """Инициализировать кнопки для копирования/вставки таблиц"""
        self.copyButton_A1.clicked.connect(
            lambda: self.copy_table(self.tableA1)
        )
        self.pasteButton_A1.clicked.connect(
            lambda: self.paste_to_table(self.tableA1)
        )
        self.copyButton_A23.clicked.connect(
            lambda: self.copy_table(self.tableA23)
        )
        self.pasteButton_A23.clicked.connect(
            lambda: self.paste_to_table(self.tableA23)
        )

        self.copyButton_A1.setStyleSheet(TRANSPARENT_BUTTON_STYLE)
        self.pasteButton_A1.setStyleSheet(TRANSPARENT_BUTTON_STYLE)
        self.copyButton_A23.setStyleSheet(TRANSPARENT_BUTTON_STYLE)
        self.pasteButton_A23.setStyleSheet(TRANSPARENT_BUTTON_STYLE)

    def disable(self):
        self.hide_base_elements()
        self.tableA1.setDisabled(True)
        self.tableA23.setDisabled(True)
        self.v1Line.setDisabled(True)
        self.v23Line.setDisabled(True)
        self.vNLine.setDisabled(True)
        self.variantsBox.setDisabled(True)

    def check_solution(self, v1_user, v23_user, vN_user,
                       is_essential_user, matrix_a1_user, matrix_a23_user):
        """Проверка решения

        :param v1_user: Выигрыш 1 игрока в данной игре (пользовательское)
        :param v23_user: Выигрыш коалиции 2 и 3 игроков (пользовательское)
        :param vN_user: Характеристическая функция игры (пользовательское)
        :param is_essential_user: Существенность игры (пользовательское)
        :param matrix_a1_user: Таблица для 1 игрока (пользовательское)
        :param matrix_a23_user: Таблица для коалиции 2 и 3 игроков
        (пользовательское)
        :return: True, если все ответы верные, иначе - False
        """
        data = VARIANTS[self.variant]

        # Все значения проверяются на симметричной игре "2,3 против 1"
        game_2vs1 = [transpose(mat) for mat in reversed(data['1vs2'])]
        game_3vs1 = [transpose(mat) for mat in reversed(data['1vs3'])]

        # Правильные матрицы для сравнения с ответом, формируются при проверке
        matrix_a1, matrix_a23 = [], []

        if not self.check_user_matrix(game_2vs1[0], game_3vs1[0],
                                      matrix_a23, transpose(matrix_a23_user)):
            return False
        if not self.check_user_matrix(game_2vs1[1], game_3vs1[1],
                                      matrix_a1, transpose(matrix_a1_user)):
            return False

        '''Т.к. перед проверкой матрицы транспонировались, то нужно
        транспонировать matrix_a1 и matrix_a23 обратно для корректного расчета
        цен игр'''
        v1, v23 = calc_game_winnings(transpose(matrix_a1),
                                     transpose(matrix_a23))
        vN = v1 + v23

        if not is_close(v1, v1_user):
            return False
        if not is_close(v23, v23_user):
            return False
        if not is_close(vN, vN_user, tolerance=PRECISION*2):
            return False

        is_essential = YES if vN_user > self.no_coop_winnings_user['vN'] else NO
        if is_essential != is_essential_user:
            return False

        # Сохранить информацию для дальнейших шагов
        MainWidget.coop_winnings_user['1vs23'] = dict(
            v1=v1_user, v23=v23_user, vN=vN_user,
        )
        MainWidget.coop_winnings_user['1vs23']['is_essential'] = \
            True if is_essential == YES else False

        return True

    def next(self):
        if self.next_window:
            self.show_instead(self.next_window)
            return

        v1 = str_to_float(self.v1Line.text())
        v23 = str_to_float(self.v23Line.text())
        vN = str_to_float(self.vNLine.text())
        is_essential = self.variantsBox.currentText() or None

        if all(item is not None for item in [v1, v23, vN, is_essential]) and \
           self.check_table_filling(self.tableA1) and \
           self.check_table_filling(self.tableA23):
                matrix_a1 = self.table_to_matrix(self.tableA1)
                matrix_a23 = self.table_to_matrix(self.tableA23)
        else:
            QMessageBox.information(
                self, EMPTY_FIELDS_TITLE, EMPTY_FIELDS_MSG, QMessageBox.Ok
            )
            return

        solved = self.check_solution(
            v1, v23, vN, is_essential,  matrix_a1,  matrix_a23
        )
        if not solved:
            self.update_errors(step=2)
            QMessageBox.critical(self, ERROR_TITLE, ERROR_MSG, QMessageBox.Ok)
        else:
            self.hide_with_success()
            self.next_window = ThirdStepWindow(self)

    def prev(self):
        self.show_instead(self.prev_window)


class ThirdStepWindow(MainWidget):
    """Окно с третьим шагом: Выбор устойчивой конфигурации"""
    def __init__(self, prev_window):
        super().__init__()
        self.ui = uic.loadUi('lib/ui/third_step.ui', self)
        self.prev_window = prev_window
        self.initUI()

    def initUI(self):
        self.setWindowTitle(THIRD_STEP_TITLE)
        self.setGeometry(self.prev_window.geometry())
        self.setFixedSize(1000, 600)
        self.init_base_elements()

        self.vLine_12vs3.setText(str(self.coop_winnings_user['12vs3']['vN']))
        self.vLine_13vs2.setText(str(self.coop_winnings_user['13vs2']['vN']))
        self.vLine_1vs23.setText(str(self.coop_winnings_user['1vs23']['vN']))

        if not self.coop_winnings_user['12vs3']['is_essential']:
            self.essentialityLabel_12vs3.setText(NOT_ESSENTIAL)
        if not self.coop_winnings_user['13vs2']['is_essential']:
            self.essentialityLabel_13vs2.setText(NOT_ESSENTIAL)
        if not self.coop_winnings_user['1vs23']['is_essential']:
            self.essentialityLabel_1vs23.setText(NOT_ESSENTIAL)

        self.remove_considered_games()
        self.show()

    def disable(self):
        self.hide_base_elements()
        self.variantsBox.setDisabled(True)

    def remove_considered_games(self):
        """Удалить (не показывать) уже рассмотренные игры"""
        considered_games = [
            game for game in ALL_GAMES if game not in self.remained_games
        ]

        for game in considered_games:
            if game == GAME_12vs3:
                self.titleLabel_12vs3.hide()
                self.vLabel_12vs3.hide()
                self.vLine_12vs3.hide()
                self.essentialityLabel_12vs3.hide()
                self.variantsBox.removeItem(
                    self.variantsBox.findText(GAME_12vs3))

            elif game == GAME_13vs2:
                self.titleLabel_13vs2.hide()
                self.vLabel_13vs2.hide()
                self.vLine_13vs2.hide()
                self.essentialityLabel_13vs2.hide()
                self.variantsBox.removeItem(
                    self.variantsBox.findText(GAME_12vs3))

            elif game == GAME_1vs23:
                self.titleLabel_1vs23.hide()
                self.vLabel_1vs23.hide()
                self.vLine_1vs23.hide()
                self.essentialityLabel_1vs23.hide()
                self.variantsBox.removeItem(
                    self.variantsBox.findText(GAME_12vs3))

    def check_solution(self, stable_game_user):
        """Проверить решение

        :param stable_game_user: Устойчивая конфигурация (пользовательское)
        :return: True, если ответ верный, иначе - False
        """
        stable_game = GAMES_UNSTABLE
        max_winning = -sys.maxsize - 1

        for game in self.remained_games:
            if game == GAME_12vs3:
                is_essential = self.coop_winnings_user['12vs3']['is_essential']
                vN_user = self.coop_winnings_user['12vs3']['vN']

                if is_essential and vN_user > max_winning:
                    stable_game = GAME_12vs3
                    max_winning = vN_user

            elif game == GAME_13vs2:
                is_essential = self.coop_winnings_user['13vs2']['is_essential']
                vN_user = self.coop_winnings_user['13vs2']['vN']

                if is_essential and vN_user > max_winning:
                    stable_game = GAME_13vs2
                    max_winning = vN_user

            else:  # if game == GAME_1vs23:
                is_essential = self.coop_winnings_user['1vs23']['is_essential']
                vN_user = self.coop_winnings_user['1vs23']['vN']

                if is_essential and vN_user > max_winning:
                    stable_game = GAME_1vs23
                    max_winning = vN_user

        if stable_game != stable_game_user:
            return False

        # Сохранить устойчивую конфигурацию, далее она будет рассматриваться
        MainWidget.current_stable_game = stable_game
        return True

    def next(self):
        if self.next_window:
            self.show_instead(self.next_window)
            return

        stable_game = self.variantsBox.currentText()
        if not stable_game:
            QMessageBox.information(
                self, EMPTY_FIELDS_TITLE, EMPTY_FIELDS_MSG, QMessageBox.Ok
            )
            return

        if not self.check_solution(stable_game):
            self.update_errors(step=3)
            QMessageBox.critical(self, ERROR_TITLE, ERROR_MSG, QMessageBox.Ok)
        else:
            self.hide_with_success()

            # Если все конфигурации неустойчивы - завершить тест
            if self.current_stable_game == GAMES_UNSTABLE:
                ResultsWindow(self)
            else:
                self.next_window = FourthStepWindow(self)

    def prev(self):
        self.show_instead(self.prev_window)


class FourthStepWindow(MainWidget):
    """Окно с четвертым шагом: Распределение дележей между игроками"""
    def __init__(self, prev_window):
        super().__init__()
        self.ui = uic.loadUi('lib/ui/fourth_step.ui', self)
        self.prev_window = prev_window
        self.initUI()

    def initUI(self):
        self.setWindowTitle(FOURTH_STEP_TITLE +
                            ' ({})'.format(self.current_stable_game))
        self.setGeometry(self.prev_window.geometry())
        self.setFixedSize(1000, 600)
        self.init_base_elements()

        self.v1Line.setText(str(self.no_coop_winnings_user['v1']))
        self.v2Line.setText(str(self.no_coop_winnings_user['v2']))
        self.v3Line.setText(str(self.no_coop_winnings_user['v3']))

        self.mu1Line.setValidator(DOUBLE_VALIDATOR)
        self.mu2Line.setValidator(DOUBLE_VALIDATOR)
        self.mu3Line.setValidator(DOUBLE_VALIDATOR)

        self.show()

    def disable(self):
        self.hide_base_elements()
        self.mu1Line.setDisabled(True)
        self.mu2Line.setDisabled(True)
        self.mu3Line.setDisabled(True)
        self.rationalityBox.setDisabled(True)

    def check_mus(self, mu1, mu2, mu3, mu1_user, mu2_user, mu3_user,
                  is_rational_user):
        """Проверить рассчитанные значения мю"""
        if not is_close(mu1, mu1_user):
            return False
        if not is_close(mu2, mu2_user):
            return False
        if not is_close(mu3, mu3_user):
            return False

        if mu1_user > self.no_coop_winnings_user['v1'] and \
           mu2_user > self.no_coop_winnings_user['v2'] and \
           mu3_user > self.no_coop_winnings_user['v3']:
            is_rational = YES
        else:
            is_rational = NO

        if is_rational != is_rational_user:
            return False

        return True

    def check_solution(self, mu1_user, mu2_user, mu3_user, is_rational_user):
        """Проверить расчитанный дележ с учетом индивидуальных выигрышей
         игроков в некооперативной игре

        :param mu1_user: Дележ на игрока 1 (пользовательское)
        :param mu2_user: Дележ на игрока 2 (пользовательское)
        :param mu3_user: Дележ на игрока 3 (пользовательское)
        :param is_rational_user: Выполняется ли условие индивидуальной
        рациональности (пользовательское)
        :type is_rational_user: str ('Да', 'Нет')
        :return: True, если все ответы верные, иначе - False
        """
        if self.current_stable_game == GAME_12vs3:
            v12 = self.coop_winnings_user['12vs3']['v12']
            v1 = self.no_coop_winnings_user['v1']
            v2 = self.no_coop_winnings_user['v2']

            mu1 = (v12 * v1) / (v1 + v2)
            mu2 = (v12 * v2) / (v1 + v2)
            mu3 = self.coop_winnings_user['12vs3']['v3']

        elif self.current_stable_game == GAME_13vs2:
            v13 = self.coop_winnings_user['13vs2']['v13']
            v1 = self.no_coop_winnings_user['v1']
            v3 = self.no_coop_winnings_user['v3']

            mu1 = (v13 * v1) / (v1 + v3)
            mu2 = self.coop_winnings_user['13vs2']['v2']
            mu3 = (v13 * v3) / (v1 + v3)

        else:  # if self.current_stable_game == GAME_1vs23
            v23 = self.coop_winnings_user['1vs23']['v23']
            v2 = self.no_coop_winnings_user['v2']
            v3 = self.no_coop_winnings_user['v3']

            mu1 = self.coop_winnings_user['1vs23']['v1']
            mu2 = (v23 * v2) / (v2 + v3)
            mu3 = (v23 * v3) / (v2 + v3)

        return self.check_mus(mu1, mu2, mu3, mu1_user, mu2_user, mu3_user,
                              is_rational_user)

    def next(self):
        if self.next_window:
            self.show_instead(self.next_window)
            return

        mu1_user = str_to_float(self.mu1Line.text())
        mu2_user = str_to_float(self.mu2Line.text())
        mu3_user = str_to_float(self.mu3Line.text())
        is_rational_user = self.rationalityBox.currentText() or None

        # Проверка заполнения всех полей
        if any(item is None for item in [mu1_user, mu2_user, mu3_user,
                                         is_rational_user]):
            QMessageBox.information(
                self, EMPTY_FIELDS_TITLE, EMPTY_FIELDS_MSG, QMessageBox.Ok
            )
            return

        solved = self.check_solution(
            mu1_user, mu2_user, mu3_user, is_rational_user
        )
        if not solved:
            self.update_errors(step=4)
            QMessageBox.critical(self, ERROR_TITLE, ERROR_MSG, QMessageBox.Ok)
        else:
            self.hide_with_success()

            # Если дележ рациональный - завершить тест
            if is_rational_user == YES:
                ResultsWindow(self)
            # Иначе, возврат к прошлому шагу и рассмотрение других коалиций
            else:
                self.remained_games.remove(self.current_stable_game)
                self.next_window = ThirdStepWindow(self)

    def prev(self):
        self.show_instead(self.prev_window)


class ResultsWindow(MainWidget):
    """Окно с результатами теста"""
    def __init__(self, prev_window):
        super().__init__()
        self.ui = uic.loadUi('lib/ui/results.ui', self)
        self.prev_window = prev_window
        self.initUI()

    def get_elapsed_time(self):
        start = self.start_time
        end = time.time()

        hours, rem = divmod(end - start, 3600)
        minutes, seconds = divmod(rem, 60)

        return '{:0>2}:{:0>2}:{:0>2}'.format(int(hours),
                                             int(minutes), int(seconds))

    def initUI(self):
        self.setWindowTitle(FINAL_TITLE)
        self.setGeometry(self.prev_window.geometry())
        self.setFixedSize(1000, 600)
        self.timerLine.setText(self.get_elapsed_time())

        self.errorsLine_step1.setText(str(self.errors_on_step[1]))
        self.errorsLine_step2.setText(str(self.errors_on_step[2]))
        self.errorsLine_step3.setText(str(self.errors_on_step[3]))
        self.errorsLine_step4.setText(str(self.errors_on_step[4]))
        self.errorsLine.setText(str(self.errors))

        self.studentInfoLine.setText('{}, {}'.format(self.surname, self.group))
        self.variantLine.setText('Вариант {}'.format(self.variant))
        self.endButton.clicked.connect(self.close)
        self.show()

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, FINISH_TITLE, FINISH_MSG, QMessageBox.Yes, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            event.accept()
            sys.exit()
        else:
            event.ignore()
