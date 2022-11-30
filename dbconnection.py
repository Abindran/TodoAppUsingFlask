import mysql.connector as sql

connection = sql.connect(
    host="localhost",
    user="root",
    password="",
    database="todo_test"
)