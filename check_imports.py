import os
import ast

# Папка с кодом проекта (без venv)
PROJECT_DIR = "/root/moex_trading_bot"

# Множества для найденных имён
imported_items = set()
defined_items = set()

def scan_file(path):
    """Парсит Python-файл и собирает данные об импортах и определениях."""
    with open(path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=path)
        except SyntaxError:
            print(f"⚠ Ошибка синтаксиса в {path}")
            return

    for node in ast.walk(tree):
        # from x import y
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_items.add(alias.name)
        # import x as y
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported_items.add(alias.name.split(".")[0])
        # определения функций
        elif isinstance(node, ast.FunctionDef):
            defined_items.add(node.name)
        elif isinstance(node, ast.AsyncFunctionDef):
            defined_items.add(node.name)
        # определения классов
        elif isinstance(node, ast.ClassDef):
            defined_items.add(node.name)

# Рекурсивно обходим проект
for root, dirs, files in os.walk(PROJECT_DIR):
    # Пропускаем виртуальное окружение
    if "venv" in root:
        continue
    for file in files:
        if file.endswith(".py"):
            scan_file(os.path.join(root, file))

# Считаем, что отсутствует то, что импортируется, но не определяется в коде проекта
missing = sorted(imported_items - defined_items)

print("\n=== Отсутствующие функции/классы в проекте ===")
for name in missing:
    print(name)
