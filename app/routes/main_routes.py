from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from app.forms import ProcesoSolicitudForm, ReestructuracionCreditoForm
from app.models import get_db_connection
import pycountry
from datetime import date, timedelta
from functools import wraps

# Crear Blueprint
main_bp = Blueprint('main', __name__)

# Decorador para manejo automático de conexión a la base de datos
def with_db_connection(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        connection = get_db_connection()
        try:
            return func(connection, *args, **kwargs)
        finally:
            connection.close()
    return wrapper

# Ruta principal
@main_bp.route('/')
def index():
    return render_template('index.html')

# Ruta para editar perfil
@main_bp.route('/editar_perfil', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    return render_template('editar_perfil.html')

@main_bp.route('/solicitante_dashboard')
@login_required
@with_db_connection
def solicitante_dashboard(connection):
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT Id_cr AS id, importe_cr, estado_cr, motivo_rechazo_cr
            FROM Credito
            WHERE Id_so = %s
        ''', (current_user.id,))
        solicitudes = cursor.fetchall()

        cursor.execute('''
            SELECT nombre_so, apellido_paterno_so, apellido_materno_so, genero_so, edad_so, pais_so, estado_so,
                   municipio_so, colonia_so, calle_so, numero_int_so, numero_ext_so, CURP_so, RFC_so
            FROM Solicitante
            WHERE Id_so = %s
        ''', (current_user.id,))
        datos_personales = cursor.fetchone()

    return render_template('solicitante_dashboard.html', solicitudes=solicitudes, datos_personales=datos_personales)


@main_bp.route('/proceso_solicitud', methods=['GET', 'POST'])
@login_required
@with_db_connection
def proceso_solicitud(connection):
    form = ProcesoSolicitudForm()

    with connection.cursor() as cursor:
        # Excluir créditos aprobados de la verificación
        cursor.execute('''
            SELECT COUNT(*) AS cuenta
            FROM Credito
            WHERE Id_so = %s AND estado_cr IN ('pendiente', 'para reestructurar')
        ''', (current_user.id,))
        solicitud_activa = cursor.fetchone()['cuenta']

    if solicitud_activa > 0:
        flash('Ya tienes una solicitud activa. No puedes hacer otra hasta que se resuelva la actual.', 'danger')
        return redirect(url_for('main.solicitante_dashboard'))

    # Procesar la nueva solicitud si no hay restricciones
    if form.validate_on_submit():
        try:
            with connection.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO Credito (importe_cr, periodicidad_cr, cantidad_pago_cr, estado_cr, interes_cr, Id_so)
                    VALUES (%s, %s, %s, 'pendiente', 0.05, %s)
                ''', (form.importe.data, form.periodicidad.data, form.cantidad_pago.data, current_user.id))
            
            connection.commit()
            flash('Solicitud enviada con éxito.', 'success')
            return redirect(url_for('main.solicitante_dashboard'))
        except Exception as e:
            connection.rollback()
            flash(f'Error al enviar la solicitud: {e}', 'danger')

    return render_template('proceso_solicitud.html', form=form)


@main_bp.route('/restructurar_credito/<int:credito_id>', methods=['GET', 'POST'])
@login_required
@with_db_connection
def restructurar_credito(connection, credito_id):
    with connection.cursor() as cursor:
        cursor.execute('SELECT Id_cr AS id, estado_cr FROM Credito WHERE Id_cr = %s AND Id_so = %s', (credito_id, current_user.id))
        credito = cursor.fetchone()

    if not credito:
        flash('Crédito no encontrado.', 'danger')
        return redirect(url_for('main.solicitante_dashboard'))

    form = ReestructuracionCreditoForm()
    if form.validate_on_submit():
        try:
            actualizar_estado_credito(connection, credito_id, 'en revisión', 'Solicitud modificada por el usuario.')
            flash('Solicitud modificada y enviada para revisión.', 'success')
            return redirect(url_for('main.solicitante_dashboard'))
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f'Error al procesar la solicitud: {e}', 'danger')

    return render_template('restructurar_credito.html', form=form, credito=credito)

@main_bp.route('/solicitar_reestructuracion/<int:credito_id>', methods=['GET', 'POST'])
@login_required
@with_db_connection
def solicitar_reestructuracion(connection, credito_id):
    with connection.cursor() as cursor:
        # Recupera el crédito para verificar estado
        cursor.execute('SELECT Id_cr, estado_cr FROM Credito WHERE Id_cr = %s AND Id_so = %s', (credito_id, current_user.id))
        credito = cursor.fetchone()

    if not credito:
        flash('No se encontró el crédito especificado.', 'danger')
        return redirect(url_for('main.solicitante_dashboard'))

    # Verifica que el estado sea 'aprobado'
    if credito['estado_cr'].lower() != 'aprobado':  # Manejamos case-insensitive
        flash(f'Solo puedes solicitar la reestructuración de créditos aprobados. Estado actual: {credito["estado_cr"]}.', 'danger')
        return redirect(url_for('main.solicitante_dashboard'))

    form = ReestructuracionCreditoForm()
    if form.validate_on_submit():
        try:
            actualizar_estado_credito(connection, credito_id, 'para reestructurar', 'Solicitud de reestructuración enviada.')
            flash('Solicitud de reestructuración enviada para revisión.', 'success')
            return redirect(url_for('main.solicitante_dashboard'))
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f'Error al procesar la solicitud: {e}', 'danger')

    return render_template('solicitar_reestructuracion.html', form=form, credito=credito)


# Actualizar estado del crédito
def actualizar_estado_credito(connection, credito_id, estado_nuevo, comentario=None):
    with connection.cursor() as cursor:
        cursor.execute('SELECT estado_cr FROM Credito WHERE Id_cr = %s', (credito_id,))
        credito = cursor.fetchone()
        if not credito:
            raise ValueError('El crédito no existe.')

        if credito['estado_cr'] == estado_nuevo:
            raise ValueError(f'El crédito ya está en el estado solicitado: {estado_nuevo}.')

        cursor.execute('''
            UPDATE Credito
            SET estado_cr = %s
            WHERE Id_cr = %s
        ''', (estado_nuevo, credito_id))

        cursor.execute('''
            INSERT INTO HistorialEstadosCredito (credito_id, estado_anterior, estado_nuevo, comentario)
            VALUES (%s, %s, %s, %s)
        ''', (credito_id, credito['estado_cr'], estado_nuevo, comentario))
        connection.commit()

@main_bp.route('/mis_pagos/<int:credito_id>')
@login_required
@with_db_connection
def mis_pagos(connection, credito_id):
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT Id_pago, monto_pago, fecha_vencimiento, fecha_pago, estado_pago
            FROM Pagos
            WHERE Id_cr = %s
        ''', (credito_id,))
        pagos = cursor.fetchall()

    if not pagos:
        flash('No hay pagos registrados para este crédito.', 'warning')
    
    return render_template('mis_pagos.html', pagos=pagos, current_credito_id=credito_id)




# Ver historial del crédito
@main_bp.route('/historial_credito/<int:credito_id>')
@login_required
@with_db_connection
def historial_credito(connection, credito_id):
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT estado_anterior, estado_nuevo, fecha, comentario
            FROM HistorialEstadosCredito
            WHERE credito_id = %s
            ORDER BY fecha DESC
        ''', (credito_id,))
        historial = cursor.fetchall()

    return render_template('historial_credito.html', historial=historial)

# Obtener subdivisiones de un país
@main_bp.route('/get_subdivisions/<country_code>')
def get_subdivisions(country_code):
    country_code = country_code.upper()
    subdivisions = [sub for sub in pycountry.subdivisions if sub.country_code == country_code]
    return jsonify([(sub.code, sub.name) for sub in subdivisions])

def generar_cronograma_pagos(credito_id, monto_total, periodicidad, fecha_inicio):
    pagos = []
    num_pagos = {'diario': 30, 'semanal': 4, 'mensual': 12}[periodicidad]
    monto_por_pago = monto_total / num_pagos

    for i in range(num_pagos):
        fecha_vencimiento = fecha_inicio + timedelta(days=(30 * i))
        pagos.append({
            'Id_cr': credito_id,
            'monto_pago': monto_por_pago,
            'fecha_vencimiento': fecha_vencimiento,
            'estado_pago': 'pendiente'
        })
    return pagos

def actualizar_estado_pagos():
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute('''
            UPDATE Pagos
            SET estado_pago = CASE
                WHEN fecha_vencimiento < CURDATE() AND estado_pago = 'pendiente' THEN 'atrasado'
                WHEN fecha_pago IS NOT NULL THEN 'pagado'
                ELSE estado_pago
            END;
        ''')
    connection.commit()

def reestructurar_credito(credito_id, nuevo_monto, nueva_periodicidad):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        # Eliminar pagos pendientes
        cursor.execute('DELETE FROM Pagos WHERE Id_cr = %s AND estado_pago = "pendiente"', (credito_id,))

        # Generar nuevo cronograma
        fecha_inicio = date.today()
        nuevos_pagos = generar_cronograma_pagos(credito_id, nuevo_monto, nueva_periodicidad, fecha_inicio)

        # Insertar nuevos pagos
        for pago in nuevos_pagos:
            cursor.execute('''
                INSERT INTO Pagos (Id_cr, monto_pago, fecha_vencimiento, estado_pago)
                VALUES (%s, %s, %s, %s)
            ''', (pago['Id_cr'], pago['monto_pago'], pago['fecha_vencimiento'], pago['estado_pago']))
    connection.commit()
