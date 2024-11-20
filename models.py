import pymysql.cursors

def get_db_connection():
    connection = pymysql.connect(
        host='localhost',
        user='lend',
        password='lend',
        database='LendEase',
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection