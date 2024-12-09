from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from app.forms import ProcesoSolicitudForm
from app.models import obtener_solicitudes_pendientes, get_db_connection

gerente_bp = Blueprint('gerente', __name__)
@gerente_bp.route('/gerente_dashboard')
@login_required
def gerente_dashboard():
    if current_user.role != 'gerente':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))
    
    # Obtener las solicitudes pendientes
    solicitudes_pendientes = obtener_solicitudes_pendientes()

    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT c.Id_cr AS id_cr,
                   s.correo_so AS solicitante_email,
                   c.importe_cr,
                   c.periodicidad_cr,
                   c.cantidad_pago_cr,
                   c.estado_cr,
                   c.Id_so
            FROM Credito c
            JOIN Solicitante s ON c.Id_so = s.Id_so
            WHERE c.estado_cr = 'para reestructurar'
        ''')
        reestructuraciones = cursor.fetchall()
    connection.close()

    # Depuración: imprimir lo que obtuviste
    print(f"Solicitudes pendientes: {solicitudes_pendientes}")
    print(f"Reestructuraciones: {reestructuraciones}")

    return render_template('gerente_dashboard.html', solicitudes_pendientes=solicitudes_pendientes, reestructuraciones=reestructuraciones)

@gerente_bp.route('/aprobar_solicitud/<int:Id_so>', methods=['POST'])
@login_required
def aprobar_solicitud(Id_so):
    if current_user.role != 'gerente':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))

    connection = get_db_connection()
    cursor = connection.cursor()
    
    try:
        # Cambiar estado a 'en revisión' antes de aprobar
        cursor.execute("""
            UPDATE Credito
            SET estado_cr = 'en revisión'
            WHERE Id_so = %s AND estado_cr = 'pendiente';
        """, (Id_so,))
        connection.commit()
        
        # Luego aprobar
        cursor.execute("""
            UPDATE Credito
            SET estado_cr = 'aprobado'
            WHERE Id_so = %s AND estado_cr = 'en revisión';
        """, (Id_so,))
        connection.commit()

        flash('Solicitud aprobada exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al aprobar la solicitud: {e}', 'danger')
        connection.rollback()
    finally:
        connection.close()

    return redirect(url_for('gerente.gerente_dashboard'))

@gerente_bp.route('/rechazar_solicitud/<int:Id_so>', methods=['POST'])
@login_required
def rechazar_solicitud(Id_so):
    if current_user.role != 'gerente':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))

    comentario = request.form.get('comentario')  # Recoger comentario del formulario
    connection = get_db_connection()
    cursor = connection.cursor()
    
    try:
        # Cambiar estado a 'rechazado' y registrar comentario
        cursor.execute("""
            UPDATE Credito
            SET estado_cr = 'rechazado', motivo_rechazo_cr = %s
            WHERE Id_so = %s AND estado_cr = 'pendiente';
        """, (comentario, Id_so))
        # Registrar en el historial
        cursor.execute("""
            INSERT INTO HistorialEstadosCredito (credito_id, estado_anterior, estado_nuevo, comentario)
            SELECT Id_cr, estado_cr, 'rechazado', %s
            FROM Credito WHERE Id_so = %s AND estado_cr = 'pendiente';
        """, (comentario, Id_so))
        connection.commit()

        flash('Solicitud rechazada exitosamente.', 'success')
    except Exception as e:
        connection.rollback()
        flash(f'Error al rechazar la solicitud: {e}', 'danger')
    finally:
        connection.close()

    return redirect(url_for('gerente.gerente_dashboard'))

@gerente_bp.route('/gerente_reestructuraciones')
@login_required
def gerente_reestructuraciones():
    if current_user.role != 'gerente':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('index'))

    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT Id_cr, importe_cr, periodicidad_cr, cantidad_pago_cr, estado_cr, Id_so
            FROM Credito
            WHERE estado_cr = 'para reestructurar';
        ''')
        reestructuraciones = cursor.fetchall()
    
    connection.close()
    return render_template('gerente_reestructuraciones.html', reestructuraciones=reestructuraciones)

@gerente_bp.route('/aprobar_reestructuracion/<int:Id_cr>', methods=['POST'])
@login_required
def aprobar_reestructuracion(Id_cr):
    if current_user.role != 'gerente':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Aprobar reestructuración y registrar transición
        cursor.execute("""
            UPDATE Credito
            SET estado_cr = 'reestructurada'
            WHERE Id_cr = %s AND estado_cr = 'para reestructurar';
        """, (Id_cr,))
        connection.commit()

        flash('Reestructuración aprobada exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al aprobar la reestructuración: {e}', 'danger')
        connection.rollback()
    finally:
        connection.close()

    return redirect(url_for('gerente.gerente_reestructuraciones'))


@gerente_bp.route('/rechazar_reestructuracion/<int:Id_cr>', methods=['POST'])
@login_required
def rechazar_reestructuracion(Id_cr):
    if current_user.role != 'gerente':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE Credito
            SET estado_cr = 'rechazado'
            WHERE Id_cr = %s AND estado_cr = 'para reestructurar'
        """, (Id_cr,))
        connection.commit()
        flash('Reestructuración rechazada exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al rechazar la reestructuración: {e}', 'danger')
    finally:
        connection.close()

    return redirect(url_for('gerente.gerente_reestructuraciones'))

@gerente_bp.route('/historial/<int:credito_id>')
@login_required
def ver_historial(credito_id):
    if current_user.role != 'gerente':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))

    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT estado_anterior, estado_nuevo, fecha, comentario
            FROM HistorialEstadosCredito
            WHERE credito_id = %s
            ORDER BY fecha DESC;
        ''', (credito_id,))
        historial = cursor.fetchall()
    connection.close()

    return render_template('historial.html', historial=historial)
