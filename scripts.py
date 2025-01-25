import json
import psycopg2

# Параметры подключения к PostgreSQL:
DB_NAME = "olymp"
DB_USER = "admin"
DB_PASS = "228337"
DB_HOST = "localhost"
DB_PORT = "5432"

# Путь к вашему JSON-файлу:
JSON_FILE = "olymp.tasks.json"

def main():
    # 1. Открываем JSON-файл
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    # 2. Устанавливаем соединение с PostgreSQL
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor()

    # 3. Подготавливаем SQL-запрос для вставки данных
    #    Обратите внимание на поля в таблице и их порядок
    insert_query = """
    INSERT INTO api_task (
        _id,
        type,
        question,
        options,
        correct_answer,
        points,
        link,
        description,
        flag
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    # 4. Итерируемся по списку заданий и вставляем в таблицу
    for item in tasks:
        _id = item.get("_id")
        type_ = item.get("type")
        question = item.get("question")
        # 'options' в JSON – это список. В PostgreSQL можно хранить как TEXT,
        # либо как JSON/ARRAY (зависит от типа колонки). Допустим, что у нас TEXT,
        # и мы сохраним его в формате JSON-строки.
        options = json.dumps(item.get("options", []))
        
        # Сопоставляем 'correctAnswer' из JSON с 'correct_answer' в БД
        correct_answer = item.get("correctAnswer")

        points = item.get("points")
        # Для полей, которых может не быть, сохраним пустую строку или null
        link = item.get("link", "")          
        description = item.get("description", "")
        flag = item.get("flag", None)  # если флаг не указан, будет null

        # Выполняем вставку
        cursor.execute(
            insert_query,
            (
                _id,
                type_,
                question,
                options,
                correct_answer,
                points,
                link,
                description,
                flag
            )
        )

    # 5. Фиксируем изменения и закрываем соединение
    conn.commit()
    cursor.close()
    conn.close()
    print("Данные успешно импортированы!")

if __name__ == "__main__":
    main()
