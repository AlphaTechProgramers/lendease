from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User, get_db_connection
from app.forms import LoginForm, RegistroSolicitanteForm, RegistroAdministradorForm
from app import login_manager

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('Ya estás logueado. Redirigiendo...', 'info')
        return redirect(url_for('main.index'))  # O redirigir al dashboard
    
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
                        return redirect(url_for('main.solicitante_dashboard'))
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
                        return redirect(url_for('admin.admin_dashboard'))
                except KeyError as e:
                    print(f"KeyError: {e} - Verifica los nombres de las columnas en la base de datos.")

            # Buscar al gerente si no es solicitante ni administrador
            cursor.execute('SELECT Id_ge, correo_ge, contrasena_ge FROM Gerente WHERE correo_ge = %s', (form.correo.data,))
            gerente = cursor.fetchone()
            if gerente:
                if check_password_hash(gerente["contrasena_ge"], form.contrasena.data):
                    login_user(User(id=gerente["Id_ge"], email=gerente["correo_ge"], role="gerente"))
                    return redirect(url_for('gerente.gerente_dashboard'))
        
        connection.close()
        flash('Credenciales incorrectas o error en el servidor.', 'error')
    return render_template('login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('main.index'))
    
@auth_bp.route('/registro_solicitante', methods=['GET', 'POST'])
def registro_solicitante():
    if current_user.is_authenticated:
        flash('Ya has iniciado sesión. No puedes registrarte nuevamente.', 'danger')
        return redirect(url_for('main.index'))

    form = RegistroSolicitanteForm()

    # Validación de formulario
    if form.validate_on_submit():
        try:
            hashed_password = generate_password_hash(form.contrasena.data)
            connection = get_db_connection()
            with connection.cursor() as cursor:
                cursor.execute('''INSERT INTO Solicitante 
                    (nombre_so, apellido_paterno_so, apellido_materno_so, correo_so, contrasena_so, genero_so, edad_so, 
                    pais_so, estado_so, municipio_so, colonia_so, calle_so, numero_int_so, numero_ext_so, CURP_so, RFC_so)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                    (form.nombre.data, form.apellido_paterno.data, form.apellido_materno.data, form.correo.data,
                     hashed_password, form.genero.data, form.edad.data, form.pais.data, form.estado.data, 
                     form.municipio.data, form.colonia.data, form.calle.data, form.numero_int.data, 
                     form.numero_ext.data, form.curp.data, form.rfc.data))
                connection.commit()

                # Obtener el ID del nuevo usuario
                cursor.execute('SELECT Id_so FROM Solicitante WHERE correo_so = %s', (form.correo.data,))
                user_data = cursor.fetchone()

            # Crear usuario y loguearlo automáticamente
            user = User(id=user_data["Id_so"], email=form.correo.data, role="solicitante")
            login_user(user)
            flash('Registro completado con éxito. Bienvenido!', 'success')
            return redirect(url_for('main.solicitante_dashboard'))
        except pymysql.MySQLError as e:
            flash(f'Error en la base de datos: {str(e)}', 'danger')
        except Exception as e:
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')

    # Manejo de errores en los campos
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{form[field].label.text}: {error}", 'danger')

    return render_template('registro_solicitante.html', form=form)


@auth_bp.route('/registro_administrador', methods=['GET', 'POST'])
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