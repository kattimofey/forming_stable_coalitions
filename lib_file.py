import numpy as np

from const import PRECISION, DECIMALS_COUNT


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
