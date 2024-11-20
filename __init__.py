from flask import Flask
from flask_mail import Mail
from flask_login import LoginManager
from config import Config

mail = Mail()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializar extensiones
    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Registrar blueprints
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from .solicitante import solicitante as solicitante_blueprint
    app.register_blueprint(solicitante_blueprint)

    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)

    from .gerente import gerente as gerente_blueprint
    app.register_blueprint(gerente_blueprint)

    return app
