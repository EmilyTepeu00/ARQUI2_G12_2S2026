"""Autenticacion, roles y perfiles.

Uso desde el bootstrap:

    from src import auth
    auth.init(app)
"""

from src.auth import decorators, security
from src.auth.guard import proteger_app
from src.auth.perfil import perfil_bp
from src.auth.repository import (
    ROL_ADMIN,
    ROL_OPERADOR_1,
    ROL_OPERADOR_2,
    sembrar_usuarios_iniciales,
    usuarios_repo,
)
from src.auth.routes import auth_bp

__all__ = [
    "auth_bp",
    "perfil_bp",
    "decorators",
    "security",
    "usuarios_repo",
    "ROL_ADMIN",
    "ROL_OPERADOR_1",
    "ROL_OPERADOR_2",
    "init",
]


def init(app):
    """Registra los blueprints, el guardia global y siembra los usuarios."""
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(perfil_bp, url_prefix="/api/perfil")
    proteger_app(app)
    sembrar_usuarios_iniciales()
    return app
