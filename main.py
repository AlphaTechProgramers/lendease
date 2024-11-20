from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from config import Config
from models import get_db_connection
from forms import RegistroSolicitanteForm, ProcesoSolicitudForm, RegistroAdministradorForm, LoginForm
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
import uuid, pycountry

app = Flask(__name__)
app.config.from_object(Config)
app.config['MAIL_SERVER'] = 'smtp.example.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'tu_correo@example.com'
app.config['MAIL_PASSWORD'] = 'tu_contraseña'
mail = Mail(app)

# Configuración de Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login' 

@app.template_filter('currency')
def currency_format(value):
    """Convierte un número en formato de moneda."""
    return "${:,.2f}".format(value)

@app.route('/get_subdivisions/<country_code>')
def get_subdivisions(country_code):
    country_code = country_code.upper()
    subdivisions = [sub for sub in pycountry.subdivisions if sub.country_code == country_code]
    subdivisions_list = [(sub.code, sub.name) for sub in subdivisions]
    return jsonify(subdivisions_list)


@app.route('/editar_perfil', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    return render_template('editar_perfil.html')

class User(UserMixin):
    def __init__(self, id, email, role):
        self.id = id
        self.email = email
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT Id_so, correo_so FROM Solicitante WHERE Id_so = %s", (user_id,))
        user = cursor.fetchone()
        if user:
            return User(id=user["Id_so"], email=user["correo_so"], role="solicitante")
        
        cursor.execute("SELECT Id_ad, correo_ad FROM Administrador WHERE Id_ad = %s", (user_id,))
        admin = cursor.fetchone()
        if admin:
            return User(id=admin["Id_ad"], email=admin["correo_ad"], role="administrador")
        
        cursor.execute("SELECT Id_ge, correo_ge FROM Gerente WHERE Id_ge = %s", (user_id,))
        gerente = cursor.fetchone()
        if gerente:
            return User(id=gerente["Id_ge"], email=gerente["correo_ge"], role="gerente")
    connection.close()
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/registro_solicitante', methods=['GET', 'POST'])
def registro_solicitante():
    if current_user.is_authenticated:
        flash('Ya has iniciado sesión. No puedes registrarte nuevamente.', 'danger')
        return redirect(url_for('index'))  # Redirige a la página principal o al dashboard

    form = RegistroSolicitanteForm()
    if form.validate_on_submit():
        try:
            hashed_password = generate_password_hash(form.contrasena.data)
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute('''INSERT INTO Solicitante 
                    (nombre_so, apellido_paterno_so, apellido_materno_so, correo_so, contrasena_so, genero_so, edad_so, 
                    pais_so, estado_so, municipio_so, colonia_so, calle_so, numero_int_so, numero_ext_so, CURP_so, RFC_so)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                    (form.nombre.data, form.apellido_paterno.data, form.apellido_materno.data, form.correo.data, hashed_password, 
                    form.genero.data, form.edad.data, form.pais.data, form.estado.data, form.municipio.data, form.colonia.data, 
                    form.calle.data, form.numero_int.data, form.numero_ext.data, form.curp.data, form.rfc.data))
                connection.commit()

                # Obtener el ID del nuevo usuario
                cursor.execute('SELECT Id_so FROM Solicitante WHERE correo_so = %s', (form.correo.data,))
                user_data = cursor.fetchone()
                
                user = User(id=user_data["Id_so"], email=form.correo.data, role="solicitante")  # Usamos Id_so

            login_user(user)  # Iniciar sesión automáticamente
            flash('Registro completado con éxito. Bienvenido!', 'success')
            return redirect(url_for('solicitante_dashboard'))  # Redirigir al dashboard del solicitante
        except Exception as e:
            flash('Hubo un error en el registro. Por favor, intenta nuevamente.', 'danger')
            return redirect(url_for('registro_solicitante'))
    
    return render_template('registro_solicitante.html', form=form)


@app.route('/proceso_solicitud', methods=['GET', 'POST'])
@login_required
def proceso_solicitud():
    if current_user.role != 'solicitante':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))

    form = ProcesoSolicitudForm()
    if form.validate_on_submit():
        print("El formulario se ha validado correctamente.")
        print("Datos del formulario:", form.data)
        try:
            connection = get_db_connection()
            print("Conexión a la base de datos establecida.")
            with connection.cursor() as cursor:
                print("Intentando insertar en la tabla Trabajo...")
                cursor.execute('''
                    INSERT INTO Trabajo (empresa_tr, sueldo_tr, tipo_nomina_tr, puesto_tr, antiguedad, Id_so)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (form.empresa.data, form.sueldo.data, form.nomina.data, form.puesto.data, form.antiguedad.data, current_user.id))
                print("Inserción en Trabajo completada.")

                print("Intentando insertar en la tabla Credito...")
                cursor.execute('''
                    INSERT INTO Credito (importe_cr, periodicidad_cr, cantidad_pago_cr, estado_cr, interes_cr, Id_so)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (form.importe.data, form.periodicidad.data, form.cantidad_pago.data, 'pendiente', 0.05, current_user.id))
                print("Inserción en Credito completada.")

            connection.commit()
            print("Transacción de la base de datos confirmada.")
            flash('Solicitud enviada con éxito', 'success')
            return redirect(url_for('solicitante_dashboard'))
        except Exception as e:
            connection.rollback()
            flash('Ocurrió un error al enviar la solicitud. Por favor, intenta nuevamente.', 'danger')
            print(f"Error al enviar solicitud: {e}")
        finally:
            connection.close()
            print("Conexión a la base de datos cerrada.")
    else:
        print("La validación del formulario falló.")
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error en el campo {getattr(form, field).label.text}: {error}", 'danger')
                print(f"Error en el campo {getattr(form, field).label.text}: {error}")

    return render_template('proceso_solicitud.html', form=form)



@app.route('/registro_administrador', methods=['GET', 'POST'])
def registro_administrador():
    form = RegistroAdministradorForm()
    if form.validate_on_submit():
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Verificar la llave única y que no haya sido usada
            cursor.execute('SELECT * FROM Claves WHERE contenido_cl = %s AND usada_cl = FALSE', (form.llave_unica.data,))
            clave = cursor.fetchone()
            if clave:
                hashed_password = generate_password_hash(form.contrasena.data)  # Encriptar la contraseña
                cursor.execute('''INSERT INTO Administrador (correo_ad, contrasena_ad, Id_ge)
                                  VALUES (%s, %s, %s)''', (form.correo.data, hashed_password, clave['Id_ge']))
                
                # Marcar la llave como usada
                cursor.execute('UPDATE Claves SET usada_cl = TRUE WHERE id_cl = %s', (clave['id_cl'],))
                
                connection.commit()
                flash('Administrador registrado con éxito', 'success')
                return redirect(url_for('login'))
            else:
                flash('Llave única incorrecta o ya utilizada', 'danger')
        connection.close()
    return render_template('registro_administrador.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('Ya estás logueado. Redirigiendo...', 'info')
        return redirect(url_for('index'))  # O redirigir al dashboard
    
    form = LoginForm()
    if form.validate_on_submit():
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Buscar al solicitante
            cursor.execute('SELECT Id_so, correo_so, contrasena_so FROM Solicitante WHERE correo_so = %s', (form.correo.data,))
            user = cursor.fetchone()
            if user:
                print("Datos del usuario:", user)  # Depuración: Imprimir los datos del usuario
                try:
                    if check_password_hash(user["contrasena_so"], form.contrasena.data):
                        login_user(User(id=user["Id_so"], email=user["correo_so"], role="solicitante"))
                        print("Redirigiendo a solicitante_dashboard")  # Debugging
                        return redirect(url_for('solicitante_dashboard'))
                except KeyError as e:
                    print(f"KeyError: {e} - Verifica los nombres de las columnas en la base de datos.")
            
            # Buscar al administrador si no es solicitante
            cursor.execute('SELECT Id_ad, correo_ad, contrasena_ad FROM Administrador WHERE correo_ad = %s', (form.correo.data,))
            admin = cursor.fetchone()
            if admin:
                print("Datos del administrador:", admin)  # Depuración: Imprimir los datos del administrador
                try:
                    if check_password_hash(admin["contrasena_ad"], form.contrasena.data):
                        login_user(User(id=admin["Id_ad"], email=admin["correo_ad"], role="administrador"))
                        print("Redirigiendo a admin_dashboard")  # Debugging
                        return redirect(url_for('admin_dashboard'))
                except KeyError as e:
                    print(f"KeyError: {e} - Verifica los nombres de las columnas en la base de datos.")

            # Buscar al gerente si no es solicitante ni administrador
            cursor.execute('SELECT Id_ge, correo_ge, contrasena_ge FROM Gerente WHERE correo_ge = %s', (form.correo.data,))
            gerente = cursor.fetchone()
            if gerente:
                if check_password_hash(gerente["contrasena_ge"], form.contrasena.data):
                    login_user(User(id=gerente["Id_ge"], email=gerente["correo_ge"], role="gerente"))
                    return redirect(url_for('gerente_dashboard'))
        
        connection.close()
        flash('Credenciales incorrectas o error en el servidor.', 'error')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('index'))
    
from flask_login import login_required, current_user

@app.route('/solicitante_dashboard')
@login_required
def solicitante_dashboard():
    connection = get_db_connection()
    with connection.cursor() as cursor:
        # Obtener las solicitudes de crédito del usuario
        cursor.execute('''
            SELECT Id_cr AS id, importe_cr AS importe, estado_cr AS estado
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


@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/gerente_dashboard')
@login_required
def gerente_dashboard():
    return render_template('gerente_dashboard.html')


@app.route('/admisiones', methods=['GET', 'POST'])
@login_required
def admisiones():
    if current_user.role != 'administrador':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    connection = get_db_connection()
    with connection.cursor() as cursor:
        # Obtener todas las solicitudes pendientes
        cursor.execute('''
            SELECT * FROM Solicitante WHERE estado = 'pendiente'
        ''')
        solicitudes = cursor.fetchall()
    
    connection.close()
    return render_template('admisiones.html', solicitudes=solicitudes)

@app.route('/aprobar_solicitud/<int:Id_so>', methods=['POST'])
@login_required
def aprobar_solicitud(Id_so):
    if current_user.role != 'administrador':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    connection = get_db_connection()
    with connection.cursor() as cursor:
        # Actualizar el estado de la solicitud
        cursor.execute('UPDATE Solicitante SET estado = %s WHERE Id_so = %s', ('aprobado', Id_so))
        
        # Obtener los datos del solicitante
        cursor.execute('SELECT correo_so FROM Solicitante WHERE Id_so = %s', (Id_so,))
        solicitante = cursor.fetchone()
        
        # Enviar correo electrónico con datos de inicio de sesión
        if solicitante:
            msg = Message('Solicitud Aprobada - LendEase',
                          sender='no-reply@lendease.com',
                          recipients=[solicitante['correo_so']])
            msg.body = f"""Hola,

Tu solicitud ha sido aprobada. Puedes iniciar sesión usando tus credenciales:

Usuario: {solicitante['correo_so']}
Contraseña: [Proporcionar una contraseña temporal o instrucciones para establecerla]

Gracias por confiar en LendEase.

Saludos,
Equipo LendEase
"""
            mail.send(msg)
    
    connection.commit()
    connection.close()
    flash('Solicitud aprobada y correo enviado.', 'success')
    return redirect(url_for('admisiones'))

@app.route('/rechazar_solicitud/<int:Id_so>', methods=['POST'])
@login_required
def rechazar_solicitud(Id_so):
    if current_user.role != 'administrador':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('index'))
    
    connection = get_db_connection()
    with connection.cursor() as cursor:
        # Actualizar el estado de la solicitud
        cursor.execute('UPDATE Solicitante SET estado = %s WHERE Id_so = %s', ('rechazado', Id_so))
        
        # Obtener los datos del solicitante
        cursor.execute('SELECT correo_so FROM Solicitante WHERE Id_so = %s', (Id_so,))
        solicitante = cursor.fetchone()
        
        # Enviar correo electrónico notificando el rechazo
        if solicitante:
            msg = Message('Solicitud Rechazada - LendEase',
                          sender='no-reply@lendease.com',
                          recipients=[solicitante['correo_so']])
            msg.body = f"""Hola,

Lamentamos informarte que tu solicitud ha sido rechazada. Por favor, revisa los requisitos y vuelve a intentarlo.

Saludos,
Equipo LendEase
"""
            mail.send(msg)
    
    connection.commit()
    connection.close()
    flash('Solicitud rechazada y correo enviado.', 'info')
    return redirect(url_for('admisiones'))

# Error 404 - Página no encontrada
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True)
