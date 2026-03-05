"""
Script para criar o primeiro usuário autoridade (dashboard).
Uso: python -m scripts.criar_usuario_autoridade
Ou: criar manualmente na base de dados após ter uma Autoridade criada.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_session_local, init_db
from app.models.models import UsuarioAutoridade, Autoridade
from app.utils.password_utils import hash_password


def main():
    init_db()
    db = get_session_local()()
    try:
        # Verificar se já existe algum usuário autoridade
        if db.query(UsuarioAutoridade).first():
            print("Já existe pelo menos um usuário autoridade. Nada a fazer.")
            return
        # Opcional: criar uma autoridade padrão se não existir
        auth = db.query(Autoridade).first()
        if not auth:
            auth = Autoridade(
                nome="Comando Geral",
                tipo="outro",
                ativo=True,
            )
            db.add(auth)
            db.commit()
            db.refresh(auth)
            print(f"Autoridade padrão criada: id={auth.id}")
        # Criar usuário autoridade (altere email e senha)
        email = os.environ.get("SOS_ADMIN_EMAIL", "admin@sosangola.ao")
        password = os.environ.get("SOS_ADMIN_PASSWORD", "admin123")
        user = UsuarioAutoridade(
            id_autoridade=auth.id,
            email=email,
            password_hash=hash_password(password),
            nome="Administrador",
            ativo=True,
            is_superuser=True,
        )
        db.add(user)
        db.commit()
        print(f"Usuário autoridade criado: {email}")
        print("Faça login no dashboard com este email e a senha definida.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
