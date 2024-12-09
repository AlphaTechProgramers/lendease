from app.routes.auth_routes import auth_bp
from app.routes.main_routes import main_bp
from app.routes.admin_routes import admin_bp
from app.routes.gerente_routes import gerente_bp

blueprints = [auth_bp, main_bp, admin_bp, gerente_bp]
