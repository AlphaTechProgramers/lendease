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
    
    connection = get_db_connection()
    with connection.cursor() as cursor:
        # Solicitudes pendientes
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
            WHERE c.estado_cr = 'pendiente';
        ''')
        solicitudes_pendientes = cursor.fetchall()

        # Solicitudes en revisión
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
            WHERE c.estado_cr = 'en revisión';
        ''')
        solicitudes_en_revision = cursor.fetchall()

        # Reestructuraciones
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
            WHERE c.estado_cr = 'para reestructurar';
        ''')
        reestructuraciones = cursor.fetchall()
    connection.close()

    return render_template(
        'gerente_dashboard.html', 
        solicitudes_pendientes=solicitudes_pendientes,
        solicitudes_en_revision=solicitudes_en_revision,
        reestructuraciones=reestructuraciones
    )

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
    return render_template('gerente_restructuraciones.html', reestructuraciones=reestructuraciones)

@gerente_bp.route('/aprobar_reestructuracion/<int:Id_cr>/<int:Id_so>', methods=['POST'])
@login_required
def aprobar_reestructuracion(Id_cr, Id_so):
    if current_user.role != 'gerente':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Aprobar reestructuración y registrar transición
        cursor.execute("""
            UPDATE Credito
            SET estado_cr = 'aprobado'
            WHERE Id_cr = %s AND estado_cr = 'para reestructurar';
        """, (Id_cr,))
        if cursor.rowcount == 0:
            flash('No se encontró el crédito a actualizar o ya no está en estado "para restructurar"".', 'danger')
            connection.rollback()
            return redirect(url_for('gerente.gerente_dashboard'))
        connection.commit()

                

        flash('Reestructuración aprobada exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al aprobar la reestructuración: {e}', 'danger')
        connection.rollback()
    finally:
        connection.close()

    return redirect(url_for('gerente.gerente_dashboard'))


@gerente_bp.route('/rechazar_reestructuracion/<int:Id_cr>/<int:Id_so>', methods=['POST'])
@login_required
def rechazar_reestructuracion(Id_cr, Id_so):
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

    return redirect(url_for('gerente.gerente_dashboard'))

@gerente_bp.route('/detalle_solicitante/<int:Id_so>', methods=['GET'])
@login_required
def detalle_solicitante(Id_so):
    if current_user.role != 'gerente':  # Si usas roles
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.index'))
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Consulta para obtener los detalles del solicitante
            cursor.execute('''
                SELECT 
                    s.Id_so,
                    s.nombre_so,
                    s.apellido_paterno_so,
                    s.apellido_materno_so,
                    s.genero_so,
                    s.edad_so,
                    s.CURP_so,
                    s.RFC_so,
                    s.pais_so,
                    s.estado_so,
                    s.municipio_so,
                    s.colonia_so,
                    s.calle_so,
                    s.numero_ext_so,
                    t.empresa_tr,
                    t.puesto_tr,
                    t.sueldo_tr,
                    t.tipo_nomina_tr,
                    t.antiguedad,
                    c.Id_cr,
                    c.importe_cr,
                    c.periodicidad_cr,
                    c.cantidad_pago_cr,
                    c.estado_cr,
                    c.interes_cr,
                    c.motivo_rechazo_cr
                FROM 
                    Solicitante s
                LEFT JOIN 
                    Trabajo t ON s.Id_so = t.Id_so
                LEFT JOIN 
                    Credito c ON s.Id_so = c.Id_so
                WHERE 
                    s.Id_so = %s;
            ''', (Id_so,))
            
            detalle_solicitante = cursor.fetchall()

        if not detalle_solicitante:
            flash('No se encontraron detalles para el solicitante especificado.', 'danger')
            return redirect(url_for('main.index'))
    
    finally:
        connection.close()

    return render_template('detalle_solicitante.html', detalle_solicitante=detalle_solicitante)



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

@gerente_bp.route('/detalles_credito/<int:credito_id>')
@login_required
def detalles_credito(credito_id):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT c.Id_cr, c.importe_cr, c.periodicidad_cr, c.cantidad_pago_cr, c.estado_cr,
                   p.monto_pago, p.fecha_vencimiento, p.fecha_pago, p.estado_pago
            FROM Credito c
            LEFT JOIN Pagos p ON c.Id_cr = p.Id_cr
            WHERE c.Id_cr = %s
        ''', (credito_id,))
        detalles = cursor.fetchall()
    connection.close()

    return render_template('detalles_credito.html', detalles=detalles)
