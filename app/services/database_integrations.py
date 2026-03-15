from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text

from app.models import TipoBancoDados


def build_database_url(
    tipo: TipoBancoDados,
    host: str | None = None,
    porta: int | None = None,
    database_name: str | None = None,
    username: str | None = None,
    password: str | None = None,
    sqlite_path: str | None = None,
) -> str:
    if tipo == TipoBancoDados.SQLITE:
        if not sqlite_path:
            raise ValueError("sqlite_path é obrigatório para SQLite.")
        return f"sqlite:///{sqlite_path}"

    if not host or not database_name or not username:
        raise ValueError("host, database_name e username são obrigatórios para este banco.")

    safe_user = quote_plus(username)
    safe_password = quote_plus(password or "")
    auth = f"{safe_user}:{safe_password}@"

    if tipo == TipoBancoDados.POSTGRESQL:
        return f"postgresql+psycopg://{auth}{host}:{porta or 5432}/{database_name}"
    if tipo == TipoBancoDados.MYSQL:
        return f"mysql+pymysql://{auth}{host}:{porta or 3306}/{database_name}"
    if tipo == TipoBancoDados.MARIADB:
        return f"mariadb+pymysql://{auth}{host}:{porta or 3306}/{database_name}"
    if tipo == TipoBancoDados.SQLSERVER:
        return f"mssql+pyodbc://{auth}{host}:{porta or 1433}/{database_name}"

    raise ValueError("Tipo de banco de dados não suportado.")


def mask_database_url(database_url: str) -> str:
    if "@" not in database_url or "://" not in database_url:
        return database_url
    scheme, rest = database_url.split("://", maxsplit=1)
    if ":" in rest and "@" in rest:
        creds, tail = rest.split("@", maxsplit=1)
        if ":" in creds:
            user = creds.split(":", maxsplit=1)[0]
            return f"{scheme}://{user}:***@{tail}"
    return database_url


def test_database_connection(database_url: str) -> tuple[bool, str]:
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True, "Conexão com banco validada com sucesso."
    except Exception as exc:
        return False, f"Falha ao conectar: {exc}"


def persist_database_url_in_env(database_url: str, env_path: str = ".env") -> None:
    """
    Atualiza/insere DATABASE_URL no arquivo .env para persistência entre reinícios.
    """
    path = Path(env_path)
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    updated = False
    new_lines: list[str] = []
    for line in lines:
        if line.startswith("DATABASE_URL="):
            new_lines.append(f"DATABASE_URL={database_url}")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"DATABASE_URL={database_url}")

    path.write_text("\n".join(new_lines).strip() + "\n", encoding="utf-8")
