from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField
from wtforms.validators import DataRequired, Email, Length, Regexp, ValidationError, NumberRange
from email_validator import validate_email, EmailNotValidError
import pymysql
import pycountry
import re
from flask import request

def validar_correo(form, field):
    try:
        validate_email(field.data, check_deliverability=True)
    except EmailNotValidError as e:
        raise ValidationError("El correo electrónico no es válido: " + str(e))

def validar_rfc(form, field):
    rfc = field.data.upper()
    if not Regexp(r'^[A-ZÑ&]{3,4}\d{6}[A-Z\d]{3}$').__call__(form, field):
        raise ValidationError("El RFC no tiene un formato válido.")

def validar_curp(form, field):
    curp = field.data.upper()
    if not Regexp(r'^[A-Z]{4}\d{6}[HM]{1}[A-Z]{5}[A-Z0-9]\d$').__call__(form, field):
        raise ValidationError("El CURP no tiene un formato válido.")

def validar_correo_unico(form, field):
    connection = pymysql.connect(host='localhost', user='lend', password='lend', database='LendEase')
    with connection.cursor() as cursor:
        cursor.execute("SELECT id_so FROM Solicitante WHERE correo_so = %s", (field.data,))
        result = cursor.fetchone()
        if result:
            raise ValidationError("Este correo ya está registrado. Por favor, usa otro.")
    connection.close()

class RegistroSolicitanteForm(FlaskForm):
    nombre = StringField('Nombre', validators=[
        DataRequired(message="Por favor, ingresa tu nombre."),
        Regexp(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$', message="El nombre solo puede contener letras y espacios.")
    ])
    apellido_paterno = StringField('Apellido Paterno', validators=[
        DataRequired(message="Por favor, ingresa tu apellido paterno."),
        Regexp(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$', message="El apellido paterno solo puede contener letras y espacios.")
    ])
    apellido_materno = StringField('Apellido Materno', validators=[
        DataRequired(message="Por favor, ingresa tu apellido materno."),
        Regexp(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$', message="El apellido materno solo puede contener letras y espacios.")
    ])
    correo = StringField('Correo electrónico', validators=[
        DataRequired(message="Por favor, ingresa tu correo electrónico."),
        validar_correo,
        validar_correo_unico
    ])
    contrasena = PasswordField('Contraseña', validators=[
        DataRequired(message="Por favor, ingresa una contraseña."),
        Length(min=6, message="La contraseña debe tener al menos 6 caracteres.")
    ])
    genero = SelectField('Género', choices=[('', 'Selecciona'), ('M', 'Masculino'), ('F', 'Femenino'), ('O', 'Otro')], validators=[
        DataRequired(message="Por favor, selecciona tu género.")
    ])
    edad = IntegerField('Edad', validators=[
        DataRequired(message="Por favor, ingresa tu edad."),
        NumberRange(min=18, max=100, message="La edad debe ser un número entre 18 y 100.")
    ])

    pais = SelectField('País', choices=[], validators=[
        DataRequired(message="Por favor, selecciona tu país.")
    ])
    estado = SelectField('Estado/Provincia', choices=[], validators=[
        DataRequired(message="Por favor, selecciona tu estado o provincia.")
    ])

    def __init__(self, *args, **kwargs):
        super(RegistroSolicitanteForm, self).__init__(*args, **kwargs)
        self.pais.choices = [(country.alpha_2, country.name) for country in pycountry.countries]
        self.pais.choices.insert(0, ('', 'Selecciona un país'))

        country_code = self.pais.data or request.form.get('pais', '').upper()

        if country_code:
            subdivisions = [sub for sub in pycountry.subdivisions if sub.country_code == country_code]
            self.estado.choices = [(sub.code, sub.name) for sub in subdivisions]
            self.estado.choices.insert(0, ('', 'Selecciona un estado/provincia'))
        else:
            self.estado.choices = [('', 'Selecciona un estado/provincia')]

    municipio = StringField('Municipio', validators=[
        DataRequired(message="Por favor, ingresa tu municipio.")
    ])
    colonia = StringField('Colonia', validators=[
        DataRequired(message="Por favor, ingresa tu colonia.")
    ])
    calle = StringField('Calle', validators=[
        DataRequired(message="Por favor, ingresa tu calle.")
    ])
    numero_int = StringField('Número Interior', validators=[
        Regexp(r'^\d*$', message="El número interior debe ser numérico.")
    ])
    numero_ext = StringField('Número Exterior', validators=[
        DataRequired(message="Por favor, ingresa tu número exterior."),
        Regexp(r'^\d+$', message="El número exterior debe ser numérico.")
    ])
    rfc = StringField('RFC', validators=[
        DataRequired(message="Por favor, ingresa tu RFC."),
        Length(min=13, max=13, message="El RFC debe tener 13 caracteres."),
        validar_rfc
    ])
    curp = StringField('CURP', validators=[
        DataRequired(message="Por favor, ingresa tu CURP."),
        Length(min=18, max=18, message="El CURP debe tener 18 caracteres."),
        validar_curp
    ])
    submit = SubmitField('Registrar')
    
class ProcesoSolicitudForm(FlaskForm):
    empresa = StringField('Empresa', validators=[
        DataRequired(message="Por favor, ingresa el nombre de la empresa."), 
        Length(min=3, max=40, message="El nombre de la empresa debe tener entre 3 y 40 caracteres.")
    ])
    
    puesto = StringField('Puesto', validators=[
        DataRequired(message="Por favor, ingresa tu puesto."), 
        Length(min=3, max=30, message="El puesto debe tener entre 3 y 30 caracteres.")
    ])
    
    antiguedad = StringField('Antigüedad', validators=[
        DataRequired(message="Por favor, ingresa tu antigüedad en el formato 'X años, Y meses'."),
        Regexp(
            r'^\s*\d+\s+años?,\s+\d+\s+meses?\s*$',
            message="El formato de antigüedad debe ser 'X años, Y meses'.",
            flags=re.IGNORECASE
        )
    ])
    
    sueldo = IntegerField('Sueldo Mensual', validators=[
        DataRequired(message="El sueldo es requerido."),
        NumberRange(min=0, message="El sueldo debe ser un número positivo.")
    ])
    
    nomina = SelectField('Tipo de Nómina', choices=[
        ('', 'Selecciona'), ('semanal', 'Semanal'), ('quincenal', 'Quincenal'), ('mensual', 'Mensual')
    ], validators=[DataRequired(message="Por favor, selecciona el tipo de nómina.")])
    
    importe = IntegerField('Importe del Crédito', validators=[
        DataRequired(message="El importe es requerido."),
        NumberRange(min=0, message="El importe debe ser un número positivo.")
    ])
    
    periodicidad = SelectField('Periodicidad de Pago', choices=[
        ('', 'Selecciona'), ('semanal', 'Semanal'), ('quincenal', 'Quincenal'), ('mensual', 'Mensual')
    ], validators=[DataRequired(message="Por favor, selecciona la periodicidad de pago.")])
    
    cantidad_pago = IntegerField('Cantidad de Pago', validators=[
        DataRequired(message="La cantidad de pago es requerida."),
        NumberRange(min=0, message="La cantidad de pago debe ser un número positivo.")
    ])
    submit = SubmitField('Enviar Solicitud')

class RegistroAdministradorForm(FlaskForm):
    correo = StringField('Correo Electrónico', validators=[DataRequired(), Email(), Length(max=50)])
    contrasena = PasswordField('Contraseña', validators=[DataRequired(), Length(min=8, message="La contraseña debe tener al menos 8 caracteres.")])
    llave_unica = StringField('Llave de Único Uso', validators=[DataRequired(), Length(min=6, max=20, message="La llave debe tener entre 6 y 20 caracteres.")])
    submit = SubmitField('Registrar')

class LoginForm(FlaskForm):
    correo = StringField('Correo Electrónico', validators=[DataRequired(), Email()])
    contrasena = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')