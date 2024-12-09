from flask import Blueprint, render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.forms import ProcesoSolicitudForm, ReestructuracionCreditoForm
from app.models import get_db_connection
import pycountry

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/editar_perfil', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    return render_template('editar_perfil.html')

@main_bp.route('/solicitante_dashboard')
@login_required
def solicitante_dashboard():
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT Id_cr AS id, importe_cr, estado_cr, motivo_rechazo_cr
            FROM Credito
            WHERE Id_so = %s
        ''', (current_user.id,))
        solicitudes = cursor.fetchall()
        
        # Obtener los datos personales del usuario
        cursor.execute('''
            SELECT nombre_so, apellido_paterno_so, apellido_materno_so, genero_so, edad_so, pais_so, estado_so, municipio_so, colonia_so, calle_so, numero_int_so, numero_ext_so, CURP_so, RFC_so
            FROM Solicitante
            WHERE Id_so = %s
        ''', (current_user.id,))
        datos_personales = cursor.fetchone()
    
    connection.close()
    return render_template('solicitante_dashboard.html', solicitudes=solicitudes, datos_personales=datos_personales)

@main_bp.route('/proceso_solicitud', methods=['GET', 'POST'])
@login_required
def proceso_solicitud():
    # Verificación de solicitud activa
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute('''
                SELECT COUNT(*) AS cuenta
                FROM Credito
                WHERE Id_so = %s AND estado_cr IN ('pendiente', 'aprobado', 'para reestructurar')
            ''', (current_user.id,))
            result = cursor.fetchone()
            solicitud_activa = result['cuenta'] if result else 0

        if solicitud_activa > 0:
            flash('Ya tienes una solicitud activa. No puedes hacer otra hasta que se resuelva la actual.', 'danger')
            return redirect(url_for('main.solicitante_dashboard'))
    finally:
        connection.close()

    form = ProcesoSolicitudForm()
    if form.validate_on_submit():
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO Trabajo (empresa_tr, sueldo_tr, tipo_nomina_tr, puesto_tr, antiguedad, Id_so)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (form.empresa.data, form.sueldo.data, form.nomina.data, form.puesto.data, form.antiguedad.data, current_user.id))

                cursor.execute('''
                    INSERT INTO Credito (importe_cr, periodicidad_cr, cantidad_pago_cr, estado_cr, interes_cr, Id_so)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (form.importe.data, form.periodicidad.data, form.cantidad_pago.data, 'pendiente', 0.05, current_user.id))

            connection.commit()
            flash('Solicitud enviada con éxito', 'success')
            return redirect(url_for('main.solicitante_dashboard'))
        except Exception as e:
            connection.rollback()
            flash('Ocurrió un error al enviar la solicitud. Por favor, intenta nuevamente.', 'danger')
            print(f"Error al enviar solicitud: {e}")
        finally:
            connection.close()

    return render_template('proceso_solicitud.html', form=form)


@main_bp.route('/restructurar_credito/<int:credito_id>', methods=['GET', 'POST'])
@login_required
def restructurar_credito(credito_id):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        # Obtener la solicitud
        cursor.execute('SELECT * FROM Credito WHERE Id_cr = %s AND Id_so = %s', 
                       (credito_id, current_user.id))
        credito = cursor.fetchone()
        if not credito:
            flash('Crédito no encontrado.', 'danger')
            return redirect(url_for('main.solicitante_dashboard'))
        
        # Solo permitir reestructuración en estados válidos
        if credito['estado_cr'] not in ['pendiente', 'para reestructurar']:
            flash('No puedes reestructurar este crédito.', 'warning')
            return redirect(url_for('main.solicitante_dashboard'))
        
        form = ReestructuracionCreditoForm()
        if form.validate_on_submit():
            try:
                actualizar_estado_credito(
                    credito_id=credito_id,
                    estado_nuevo='en revisión',
                    comentario='Solicitud modificada por el usuario.'
                )
                flash('Solicitud modificada y enviada para revisión.', 'success')
                return redirect(url_for('main.solicitante_dashboard'))
            except ValueError as e:
                flash(str(e), 'danger')
            except Exception as e:
                connection.rollback()
                flash('Error al procesar la solicitud.', 'danger')
    connection.close()
    return render_template('restructurar_credito.html', form=form, credito=credito)


def actualizar_estado_credito(credito_id, estado_nuevo, comentario=None):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        # Obtener el estado actual
        cursor.execute('SELECT estado_cr FROM Credito WHERE Id_cr = %s', (credito_id,))
        credito = cursor.fetchone()
        if not credito:
            raise ValueError('El crédito no existe.')
        
        estado_anterior = credito['estado_cr']
        if estado_anterior == estado_nuevo:
            raise ValueError('El crédito ya está en el estado solicitado.')
        
        # Actualizar el estado
        cursor.execute('''
            UPDATE Credito
            SET estado_cr = %s
            WHERE Id_cr = %s
        ''', (estado_nuevo, credito_id))
        
        # Registrar el historial
        cursor.execute('''
            INSERT INTO HistorialEstadosCredito (credito_id, estado_anterior, estado_nuevo, comentario)
            VALUES (%s, %s, %s, %s)
        ''', (credito_id, estado_anterior, estado_nuevo, comentario))
        
        connection.commit()
    connection.close()

@main_bp.route('/solicitar_reestructuracion/<int:credito_id>', methods=['GET', 'POST'])
@login_required
def solicitar_reestructuracion(credito_id):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        # Obtener el crédito aprobado
        cursor.execute('''
            SELECT * FROM Credito WHERE Id_cr = %s AND Id_so = %s
        ''', (credito_id, current_user.id))
        credito = cursor.fetchone()
        if not credito or credito['estado_cr'] != 'aprobado':
            flash('Solo puedes solicitar la reestructuración de créditos aprobados.', 'danger')
            return redirect(url_for('main.solicitante_dashboard'))
        
        form = ReestructuracionCreditoForm()
        if form.validate_on_submit():
            try:
                actualizar_estado_credito(
                    credito_id=credito_id,
                    estado_nuevo='para reestructurar',
                    comentario='Solicitud de reestructuración enviada.'
                )
                flash('Solicitud de reestructuración enviada para revisión.', 'success')
                return redirect(url_for('main.solicitante_dashboard'))
            except ValueError as e:
                flash(str(e), 'danger')
            except Exception as e:
                connection.rollback()
                flash('Error al procesar la solicitud.', 'danger')
    connection.close()
    return render_template('solicitar_reestructuracion.html', form=form, credito=credito)

@main_bp.route('/historial_credito/<int:credito_id>')
@login_required
def historial_credito(credito_id):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT estado_anterior, estado_nuevo, fecha, comentario
            FROM HistorialEstadosCredito
            WHERE credito_id = %s
            ORDER BY fecha DESC
        ''', (credito_id,))
        historial = cursor.fetchall()
    connection.close()
    return render_template('historial_credito.html', historial=historial)


@main_bp.route('/get_subdivisions/<country_code>')
def get_subdivisions(country_code):
    country_code = country_code.upper()
    subdivisions = [sub for sub in pycountry.subdivisions if sub.country_code == country_code]
    subdivisions_list = [(sub.code, sub.name) for sub in subdivisions]
    return jsonify(subdivisions_list)
