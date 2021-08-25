import numpy as np


def is_close(a, b, tolerance=1e-6):
    """Проверить числа на приблизительное равенство"""
    return abs(a-b) <= tolerance


def is_equilibrium(xi, yi, mat_a, mat_b, mat_e, mat_f, m, n):
    """Являются ли стратегии xi, yi равновесными

    :param xi: i-ая стратегия x
    :param yi: i-ая стратегия y
    :param mat_a: Неединичная часть блочной матрицы A0 (транспонированная A1)
    :param mat_b: Неединичная часть блочной матрицы B0 (B1)
    :param mat_e: Единичная часть блочной матрицы A0
    :param mat_f: Единичная часть блочной матрицы B0
    :param m: Размер игры (кол-во строк)
    :param n: Размер игры (кол-во столбцов)
    """
    for j in range(n):
        if not is_close(np.matmul(mat_e[:, j], yi)*(np.matmul(mat_b[:, j], xi) - 1), 0):  # NoQA
            return False

    return all(
        is_close(
            np.matmul(mat_f[:, i], xi) * (np.matmul(mat_a[:, i], yi) - 1), 0
        )
        for i in range(m)
    )


def simplex_method(mat, pivot, pivot_row, pivot_col):
    """Симплекс-преобразование для замены базиса

    :param mat: Матрица для преобразования
    :param pivot: Разрешающий элемент
    :param pivot_row: Строка, в которой находится разрешающий элемент
    :param pivot_col: Столбец, в котором находится разрешающий элемент
    :return: Преобразованная матрица mat
    """
    # Строка с разрешающим элементом делится на разрешающий элемент
    mat[pivot_row] /= pivot

    # Из остальных строк вычитается строка с разрешающим элементом,
    # умноженная на коэффициент
    for i in range(mat.shape[0]):
        if i != pivot_row:
            coef = mat[i][pivot_col]
            mat[i] -= np.multiply(mat[pivot_row], coef)

    return mat


def calculate_epsilon_row(mat, v0):
    """Рассчитать строку с эпсилонами

    :param mat: Матрица для расчета (транспонированная A1 или B1)
    :param v0: Вектор начального решения (x0 или y0)
    """
    return np.array([np.matmul(mat[:, i], v0) - 1 for i in range(mat.shape[1])])


def calculate_lambda_column(mat, epsilons):
    """Рассчитать столбец с лямбдами

    :param mat: Матрица для расчета (A1* или B1* после симплекс-метода)
    :param epsilons: Строка с эпсилонами и присоединенным
     к ней вектором начального решения
    """
    rows = mat.shape[0]
    cols = mat.shape[1]
    lambdas = np.array([])

    for i in range(rows):
        lambdas1, lambdas2 = np.array([]), np.array([])
        row = mat[i]

        for j in range(cols):
            element = row[j]
            # Две формулы рассчета для положительных и отрицательных элементов
            if element < 0:
                lambdas1 = np.append(lambdas1, - epsilons[j] / element)
            elif element > 0:
                lambdas2 = np.append(lambdas2, - epsilons[j] / element)

        lambda1 = np.amin(lambdas1) if lambdas1.size > 0 else None
        lambda2 = np.amax(lambdas2) if lambdas2.size > 0 else None

        if lambda1:
            lambdas = np.append(lambdas, lambda1)
        elif lambda2:
            lambdas = np.append(lambdas, lambda2)
        else:
            lambdas = np.append(lambdas, 0)

    return lambdas


def get_possible_solutions(v0, lambdas, basis):
    """Получить возможные вектора решений

    :param v0: Вектор начального решения
    :param lambdas: Столбец лямбд для матрицы
    :param basis: Базисная часть матрицы после замены базиса
    """
    return np.array([v0 + lambdas[i]*basis[i] for i in range(basis.shape[0])])


def calculate_answer(d, x, y):
    """Посчитать цены игры при использовании оптимальных стратегий

    :param d: Коэффициент, использованный для начального
     преобразования A0, B0 -> положительные A1, B1
    :param x: Равновесная стратегия x
    :param y: Равновесная стратегия y
    :return: Цена игры A, Цена игры B
    """
    a_winning = d - 1.0 / np.sum(y)
    b_winning = d - 1.0 / np.sum(x)

    return a_winning, b_winning


def get_equilibrium_strategies(a1, b1, a_pivot_row, m, n):
    """Найти равновесные стратегии для текущей итерации

    :param a1: Положительная матрица A1
    :param b1: Положительная матрица B1
    :param a_pivot_row: Номер текущей итерации (с нуля), соответствующий
     номеру строки в матрице A0, в которой ищется разрешающий элемент
    :param m: Размер игры (кол-во строк)
    :param n: Размер игры (кол-во столбцов)
    :return: x, y - равновесные стратегии
    """

    '''ШАГ 2. Определение начальных значений векторов стратегий x0,y0'''
    a1_transposed = np.transpose(a1)

    # Получить единичные матрицы размеров m и n
    f, e = np.identity(m), np.identity(n)
    # Получить блочные матрицы A0 и B0, присоединением единичных
    a0 = np.concatenate((a1_transposed, e), axis=1)
    b0 = np.concatenate((b1, f), axis=1)

    # Получить разрешающие элементы в A0, B0 и их индексы
    a_pivot = np.amin(a1_transposed[a_pivot_row])
    a_pivot_col = np.argmin(a1_transposed[a_pivot_row])

    # Строка матрицы B0, в которой ищется разрешающий элемент,
    # имеет номер, равный номеру столбца разрешающего элемента в A0
    b_pivot_row = a_pivot_col
    b_pivot = np.amin(b1[b_pivot_row])
    b_pivot_col = np.argmin(b1[b_pivot_row])

    # Получить начальные значения x0 и y0
    y0 = np.zeros(n)
    y0[a_pivot_row] = 1.0 / a_pivot
    x0 = np.zeros(m)
    x0[a_pivot_col] = 1.0 / b_pivot

    '''ШАГ 3. Проверка условий равновесия'''
    if is_equilibrium(x0, y0, a1_transposed, b1, e, f, m, n):
        return x0, y0

    '''ШАГ 4. Замена базисов'''
    a0_simplexed = simplex_method(a0, a_pivot, a_pivot_row, a_pivot_col)
    a_epsilons = np.concatenate((calculate_epsilon_row(a1_transposed, y0), y0))
    a_lambdas = calculate_lambda_column(a0_simplexed, a_epsilons)

    b0_simplexed = simplex_method(b0, b_pivot, b_pivot_row, b_pivot_col)
    b_epsilons = np.concatenate((calculate_epsilon_row(b1, x0), x0))
    b_lambdas = calculate_lambda_column(b0_simplexed, b_epsilons)

    '''ШАГ 5. Определение оптимальных стратегий и цен игры'''
    # Новые базисы
    new_e = a0_simplexed[:, -a0_simplexed.shape[0]:]
    new_f = b0_simplexed[:, -b0_simplexed.shape[0]:]

    y_solutions = get_possible_solutions(y0, a_lambdas, new_e)
    x_solutions = get_possible_solutions(x0, b_lambdas, new_f)

    # Поиск равновесного решения
    for i in range(x_solutions.shape[0]):
        for j in range(y_solutions.shape[0]):

            if is_equilibrium(x_solutions[i], y_solutions[j],
                              a1_transposed, b1, e, f, m, n):
                return x_solutions[i], y_solutions[j]

    # Если на текущей итерации не найдено равновесного решения
    return None


def calc_game_winnings(a, b):
    """Расчитать выигрыши игроков методом Лемке-Хоусона

    :param a: Матрица выигрышей игрока A
    :type a: list of list
    :param b: Матрица выигрышей игрока B
    :type b: list of list
    :return: Цена игры A, цена игры B
    :rtype: float, float
    """
    a, b = np.array(a), np.array(b)

    # Размер игры
    m, n = a.shape[0], a.shape[1]

    '''ШАГ 1. Вычисление матриц A1 и B1'''
    d = max(np.amax(a), np.amax(b)) + 1
    d_matrix = np.full((m, n), d)

    a1 = d_matrix - a
    b1 = d_matrix - b

    for k in range(n):
        equilibrium_strategies = get_equilibrium_strategies(a1, b1, k, m, n)

        if equilibrium_strategies:
            return calculate_answer(
                d, equilibrium_strategies[0], equilibrium_strategies[1]
            )
