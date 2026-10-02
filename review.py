# ОБЩАЯ ОЦЕНКА

# Код рабочий, структура логичная, класс Calculator разделён на методы,
# каждый метод отвечает за свою задачу. Читаемость хорошая, отступы
# соблюдены, имена переменных в целом понятны. Однако есть несколько
# серьёзных проблем с безопасностью и ряд замечаний по логике и
# архитектуре, которые стоит исправить.



# 1. КРИТИЧНЫЕ ПРОБЛЕМЫ


# 1.1. ИСПОЛЬЗОВАНИЕ eval() - УЯЗВИМОСТЬ И ХРУПКОСТЬ

# В трёх местах используется встроенная функция eval():
#
#     Строка 144:  self.current_expression = str(eval(self.total_expression))
#     Строка 165:  self.current_expression = str(eval(f"{self.current_expression}**2"))
#     Строка 170:  self.current_expression = str(eval(f"{self.current_expression}**0.5"))
#
# Функция eval() выполняет произвольный Python-код, а не только
# арифметические выражения. Это создаёт уязвимость: если пользователь
# каким-то образом передаст в поле ввода строку вида
#     __import__('os').system('rm -rf /')
# она будет выполнена. В текущей реализации ввод ограничен кнопками, но
# метод bind_keys() привязывает клавиатуру, а строка current_expression
# может содержать произвольные символы.
#
# РЕКОМЕНДАЦИЯ:
# Заменить eval() на безопасный вычислитель на основе модуля ast.
# Пример:
#
#     import ast
#     import operator
#
#     ALLOWED_BINOPS = {
#         ast.Add: operator.add,
#         ast.Sub: operator.sub,
#         ast.Mult: operator.mul,
#         ast.Div: operator.truediv,
#         ast.Pow: operator.pow,
#     }
#     ALLOWED_UNARYOPS = {
#         ast.UAdd: operator.pos,
#         ast.USub: operator.neg,
#     }
#
#     def safe_eval(expression):
#         def _eval(node):
#             if isinstance(node, ast.Constant):
#                 return node.value
#             if isinstance(node, ast.BinOp):
#                 op = ALLOWED_BINOPS.get(type(node.op))
#                 if op is None:
#                     raise ValueError("Недопустимый оператор")
#                 return op(_eval(node.left), _eval(node.right))
#             if isinstance(node, ast.UnaryOp):
#                 op = ALLOWED_UNARYOPS.get(type(node.op))
#                 if op is None:
#                     raise ValueError("Недопустимый унарный оператор")
#                 return op(_eval(node.operand))
#             raise ValueError("Недопустимое выражение")
#         tree = ast.parse(expression, mode="eval")
#         return _eval(tree.body)


# 1.2. ОШИБКА В МЕТОДАХ square() И sqrt() ПРИ ПУСТОМ ВЫРАЖЕНИИ

# Строки 165 и 170:
#
#     self.current_expression = str(eval(f"{self.current_expression}**2"))
#     self.current_expression = str(eval(f"{self.current_expression}**0.5"))
#
# Если current_expression пустое (например, сразу после clear()),
# получится строка "**2" или "**0.5", и eval() выбросит SyntaxError.
# Это приведёт к аварийному завершению программы.
#
# РЕКОМЕНДАЦИЯ:
# Проверять выражение на пустоту перед вычислением и оборачивать в try/except.


# 1.3. ДВОЙНОЕ НАЖАТИЕ ОПЕРАТОРА

# Строки 130-136:
#
#     def append_operator(self, operator):
#         self.current_expression += operator
#         self.total_expression += self.current_expression
#         ...
#
# Если пользователь нажмёт "5", затем "+", затем ещё раз "+", в
# current_expression окажется строка "5++". При следующем вводе цифры
# получится "5++3", и eval() не сможет это вычислить.
#
# РЕКОМЕНДАЦИЯ:
# Перед добавлением оператора проверять, что последний символ
# current_expression - не оператор.


# 1.4. ОБРАБОТКА ПУСТОГО ВЫРАЖЕНИЯ В evaluate()

# Строки 141-149:
#
#     def evaluate(self):
#         self.total_expression += self.current_expression
#         self.update_total_label()
#         try:
#             self.current_expression = str(eval(self.total_expression))
#             self.total_expression = ""
#         except Exception as e:
#             self.current_expression = "Error"
#         finally:
#             self.update_label()
#
# Если нажать "=" сразу после "C", total_expression пустое, eval("")
# выбросит SyntaxError. Программа не упадёт, но пользователь увидит
# "Error" там, где ничего не должно происходить.
#
# РЕКОМЕНДАЦИЯ:
# Добавить проверку в начале метода: если выражение пустое - просто выйти.



# 2. ЛОГИЧЕСКИЕ И UX-ПРОБЛЕМЫ


# 2.1. total_expression СБРАСЫВАЕТСЯ ПОСЛЕ ВЫЧИСЛЕНИЯ

# Строка 145: self.total_expression = ""
# После нажатия "=" пользователь теряет историю ввода. В верхней строке
# (total_label) должно остаться выражение вида "5 + 3 =", чтобы было
# понятно, что именно считалось.
#
# РЕКОМЕНДАЦИЯ:
# Не сбрасывать total_expression, либо явно отображать его с знаком "=".


# 2.2. ОБРЕЗКА РЕЗУЛЬТАТА ТОЛЬКО НА УРОВНЕ ОТОБРАЖЕНИЯ

# Строка 178: self.label.config(text=self.current_expression[:11])
# Отображение обрезается до 11 символов, но само значение остаётся
# длинным. При последующих операциях это может привести к
# неожиданным результатам.
#
# РЕКОМЕНДАЦИЯ:
# Либо ограничивать длину самого значения, либо использовать
# научную нотацию для больших чисел.


# 2.3. МЕТОДЫ square() И sqrt() РАБОТАЮТ ТОЛЬКО С ТЕКУЩИМ ВЫРАЖЕНИЕМ

# Они не учитывают total_expression. Например: пользователь ввёл "5 +",
# затем "3" и нажал "x²". Возведётся только "3", а не всё выражение.
# Это может быть как задумано, так и ошибкой - поведение стоит
# явно задокументировать.


# 2.4. ДЕЛЕНИЕ НА НОЛЬ НЕ ОБРАБАТЫВАЕТСЯ ЯВНО

# eval("1/0") выбросит ZeroDivisionError, сработает общий except
# Exception, и пользователь увидит "Error". Работает, но лучше
# обрабатывать ZeroDivisionError отдельно с понятным сообщением.


# 2.5. ПРИВЯЗКА КЛАВИШ

# Метод bind_keys() привязывает цифры, операторы и Return. Однако:
#     - Нет привязки Escape для очистки (clear).
#     - Нет привязки BackSpace для удаления последнего символа.
#     - Оператор "/" на некоторых раскладках конфликтует с системными
#       сочетаниями.
# Эти привязки - стандартные ожидания пользователя калькулятора.
#
# РЕКОМЕНДАЦИЯ:
# Добавить:
#     self.window.bind("<Escape>", lambda e: self.clear())
#     self.window.bind("<BackSpace>", lambda e: self.backspace())


# 2.6. ПОВТОРНЫЙ ВВОД ПРИ УДЕРЖАНИИ ENTER

# Строка 82:
#     self.window.bind("<Return>", lambda event: self.evaluate())
# Если пользователь зажмёт Enter, evaluate() сработает многократно.



# 3. АРХИТЕКТУРНЫЕ УЛУЧШЕНИЯ


# 3.1. МАГИЧЕСКИЕ ЧИСЛА

# Строки 23, 66, 178:
#     self.window.geometry("375x667")
#     frame = tk.Frame(self.window, height=221, bg=LIGHT_GRAY)
#     self.label.config(text=self.current_expression[:11])
# Числа 375, 667, 221, 11 - магические. Их стоит вынести в константы
# в начале файла для удобства изменения и читаемости.


# 3.2. МЕТОД create_display_labels ВОЗВРАЩАЕТ КОРТЕЖ

# Метод, судя по названию, должен создавать один объект, но возвращает
# кортеж из двух меток. Это неочевидно. Лучше либо переименовать метод
# (например, build_display_labels), либо возвращать словарь.


# 3.3. ДУБЛИРОВАНИЕ ЛОГИКИ В square() И sqrt()

# Строки 165-172 - почти идентичный код, отличается только степенью.
#
# РЕКОМЕНДАЦИЯ:
# Вынести в один вспомогательный метод:
#
#     def _apply_unary(self, op):
#         try:
#             self.current_expression = str(eval(f"({self.current_expression}){op}"))
#         except Exception:
#             self.current_expression = "Error"
#         self.update_label()
#
#     def square(self):
#         self._apply_unary("**2")
#
#     def sqrt(self):
#         self._apply_unary("**0.5")


# 3.4. ИЗБЫТОЧНЫЙ finally В evaluate()

# Строка 148: finally: self.update_label()
# Блок finally здесь не нужен, так как update_label() вызывается в
# любом случае - и при успехе, и при ошибке. Достаточно вынести его
# после try/except.


# 3.5. ХРАНЕНИЕ ВЫРАЖЕНИЯ В ВИДЕ СТРОКИ

# current_expression хранится как строка, что нормально для калькулятора,
# но все преобразования выполняются через str(eval(...)). Это хрупко.
# Лучше возвращать из вычислителя число и форматировать его отдельно.


# 3.6. СМЕШЕНИЕ ЛОГИКИ И ИНТЕРФЕЙСА

# Класс Calculator одновременно:
#     - создаёт виджеты (UI),
#     - обрабатывает события,
#     - выполняет вычисления.
# Для учебного проекта допустимо, но при развитии стоит разделить на
# CalculatorModel (логика) и CalculatorView (Tkinter).


# 4. МЕЛКИЕ ЗАМЕЧАНИЯ

# 4.1. Строка 24: self.window.resizable(0, 0)
# Устаревший стиль. Лучше: self.window.resizable(False, False).

# 4.2. Окно не центрируется на экране - открывается в левом верхнем углу.

# 4.3. Нет иконки приложения - мелочь, но улучшает вид.

# 4.4. Строка 148: except Exception as e - переменная e не используется.
# Можно заменить на except Exception: или добавить логирование.


# ИТОГОВЫЙ ЧЕК-ЛИСТ
#
#   Приоритет   | Проблема                                | Действие
#   ------------|-----------------------------------------|-------------------------
#   Критично    | eval()                                  | Заменить на ast
#   Критично    | sqrt/square на пустом выражении         | try/except + проверка
#   Критично    | Двойные операторы "5++"                 | Валидация
#   Важно       | total_expression сбрасывается после "=" | Оставлять историю
#   Важно       | Нет BackSpace / Escape                  | Добавить привязки
#   Важно       | Деление на ноль                         | Явная обработка
#   Желательно  | Магические числа                        | Вынести в константы
#   Желательно  | Дублирование square/sqrt                | Объединить
#   Желательно  | Смешение UI и логики                    | Разделить слои
#
# ПРИМЕР ИСПРАВЛЕННОГО evaluate()
#
#   def evaluate(self):
#       if not self.current_expression:
#           return
#       self.total_expression += self.current_expression
#       self.update_total_label()
#       try:
#           result = safe_eval(self.total_expression)
#           self.current_expression = self._format_result(result)
#       except ZeroDivisionError:
#           self.current_expression = "Деление на ноль"
#       except Exception:
#           self.current_expression = "Ошибка"
#       self.update_label()
#
#   def _format_result(self, value):
#       if isinstance(value, float) and value.is_integer():
#           return str(int(value))
#       return str(value)