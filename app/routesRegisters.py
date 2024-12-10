from flask import Flask, render_template, request, redirect, session, url_for, flash

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

@app.route('/registro/paso-1', methods=['GET', 'POST'])
def registro_paso_1():
    if request.method == 'POST':
        session['nombre'] = request.form['nombre']
        session['apellido_paterno'] = request.form['apellido_paterno']
        session['apellido_materno'] = request.form['apellido_materno']
        return redirect(url_for('registro_paso_2'))
    return render_template('registro_paso_1.html')

@app.route('/registro/paso-2', methods=['GET', 'POST'])
def registro_paso_2():
    if request.method == 'POST':
        session['estado'] = request.form['estado']
        session['municipio'] = request.form['municipio']
        return redirect(url_for('registro_paso_3'))
    return render_template('registro_paso_2.html')

@app.route('/registro/paso-3', methods=['GET', 'POST'])
def registro_paso_3():
    if request.method == 'POST':
        session['rfc'] = request.form['rfc']
        session['curp'] = request.form['curp']
        flash("Registro completado con éxito", "success")
        session.clear()  # Limpia la sesión después de completar el registro
        return redirect(url_for('home'))
    return render_template('registro_paso_3.html')

@app.route('/')
def home():
    return render_template('home.html')
