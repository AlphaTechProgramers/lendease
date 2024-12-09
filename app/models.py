from flask_login import UserMixin
from app import login_manager
import pymysql

def get_db_connection():
    connection = pymysql.connect(
        host='localhost',
        user='lend',
        password='lend',
        db='LendEase',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )
    return connection

def obtener_solicitudes_pendientes():
    try:
        connection = get_db_connection()
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
            SELECT c.Id_cr AS id_cr, 
                   s.correo_so AS solicitante_email,
                   c.importe_cr, 
                   c.periodicidad_cr, 
                   c.cantidad_pago_cr, 
                   c.estado_cr, 
                   c.Id_so
            FROM Credito c
            JOIN Solicitante s ON c.Id_so = s.Id_so
            WHERE c.estado_cr IN ('pendiente')
            """)
            solicitudes_pendientes = cursor.fetchall()
            print(f"Solicitudes obtenidas: {solicitudes_pendientes}")
            return solicitudes_pendientes
    except Exception as e:
        print(f"Error en la consulta: {e}")
        return []
    finally:
        connection.close()


class User(UserMixin):
    def __init__(self, id, email, role):
        self.id = id
        self.email = email
        self.role = role
