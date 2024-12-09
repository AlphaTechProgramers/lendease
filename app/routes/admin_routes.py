from flask import Blueprint, render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.forms import ProcesoSolicitudForm
from app.models import get_db_connection
import pycountry


admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'administrador':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))
    
    # Manejo de solicitudes pendientes
    try:
        connection = get_db_connection()
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("""
            SELECT c.Id_cr AS id_cr, 
                s.correo_so AS solicitante_email,  -- Cambiado 'email' por 'correo_so'
                c.importe_cr, 
                c.periodicidad_cr, 
                c.cantidad_pago_cr, 
                c.estado_cr, 
                c.Id_so
            FROM Credito c
            JOIN Solicitante s ON c.Id_so = s.Id_so
            WHERE c.estado_cr = 'pendiente';
            """)
            solicitudes_pendientes = cursor.fetchall()
            print(f"Solicitudes pendientes obtenidas: {solicitudes_pendientes}")  # Depuración
    except Exception as e:
        print(f"Error al obtener solicitudes pendientes: {e}")
        flash('Ocurrió un error al obtener las solicitudes pendientes.', 'danger')
        solicitudes_pendientes = []
    finally:
        connection.close()
    
    return render_template('admin_dashboard.html', solicitudes_pendientes=solicitudes_pendientes)

@admin_bp.route('/aprobar_solicitud/<int:Id_so>', methods=['POST'])
@login_required
def aprobar_solicitud(Id_so):
    if current_user.role != 'administrador':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))
    
    connection = get_db_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute("""
            UPDATE Credito
            SET estado_cr = 'aprobado'
            WHERE Id_so = %s AND estado_cr = 'pendiente'
        """, (Id_so,))
        connection.commit()
        flash('Solicitud aprobada exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al aprobar la solicitud: {e}', 'danger')
    finally:
        connection.close()
    
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/rechazar_solicitud/<int:Id_so>', methods=['POST'])
@login_required
def rechazar_solicitud(Id_so):
    if current_user.role != 'administrador':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))
    
    connection = get_db_connection()
    cursor = connection.cursor()
    
    try:
        cursor.execute("""
            UPDATE Credito
            SET estado_cr = 'rechazado'
            WHERE Id_so = %s AND estado_cr = 'pendiente'
        """, (Id_so,))
        connection.commit()
        flash('Solicitud rechazada exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al rechazar la solicitud: {e}', 'danger')
    finally:
        connection.close()
    
    return redirect(url_for('admin.admin_dashboard'))
