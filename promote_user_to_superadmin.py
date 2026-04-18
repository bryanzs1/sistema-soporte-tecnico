import os
import sys

from app import create_app, db
from app.models import User


def main():
    username = sys.argv[1] if len(sys.argv) > 1 else 'admin'
    config_name = (
        'config.ProductionConfig'
        if os.environ.get('FLASK_ENV') == 'production'
        else 'config.DevelopmentConfig'
    )

    app = create_app(config_name)

    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f'No se encontró el usuario: {username}')
            return 1

        previous_role = user.role
        user.role = 'superadmin'
        db.session.commit()

        print(
            f'Usuario {username} actualizado correctamente: '
            f'{previous_role} -> {user.role}'
        )
        return 0


if __name__ == '__main__':
    raise SystemExit(main())