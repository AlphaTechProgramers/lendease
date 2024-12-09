from flask import Flask
from config import Config
from flask_login import LoginManager
from flask_mail import Mail

login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # Ajusta según tu ruta de inicio de sesión
mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializar extensiones
    login_manager.init_app(app)
    mail.init_app(app)

    # Registrar Blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.main_routes import main_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.gerente_routes import gerente_bp
    # ... otros blueprints

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(gerente_bp, url_prefix='/gerente')
    # ... registrar otros blueprints

    # Filtros de plantilla
    @app.template_filter('currency')
    def currency_format(value):
        """Convierte un número en formato de moneda."""
        return "${:,.2f}".format(value)

    return app

from app import models
