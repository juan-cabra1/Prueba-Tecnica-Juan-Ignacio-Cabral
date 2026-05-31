from dataclasses import dataclass


@dataclass
class InScopeCase:
    query: str
    expected_codigo: str | None
    description: str


@dataclass
class OutOfScopeCase:
    query: str
    description: str


IN_SCOPE_CASES: list[InScopeCase] = [
    InScopeCase("no puedo conectar a la base de datos", "ERR-DB-001", "DB connection error"),
    InScopeCase("error de conexión con el servidor de datos", "ERR-DB-001", "DB connection error alt phrasing"),
    InScopeCase("código de material duplicado", "ERR-CAT-001", "Duplicate material code"),
    InScopeCase("ya existe un material registrado con este código", "ERR-CAT-001", "Duplicate material alt phrasing"),
    InScopeCase("usuario o contraseña incorrectos", "ERR-AUTH-001", "Auth credentials error"),
    InScopeCase("no puedo iniciar sesión", "ERR-AUTH-001", "Login error alt phrasing"),
    InScopeCase("campos obligatorios incompletos", None, "Missing required fields — no codigo in source"),
    InScopeCase("el catálogo carga lentamente", None, "Slow catalog — no codigo in source"),
]

OUT_OF_SCOPE_CASES: list[OutOfScopeCase] = [
    OutOfScopeCase("El sistema devuelve error 502, ¿qué significa?", "HTTP 502 — not in docs"),
    OutOfScopeCase("¿Cómo reinicio el servicio de autenticación?", "Service restart — not in docs"),
    OutOfScopeCase("¿Cuál es la dirección IP del servidor de producción?", "Infrastructure info — not in docs"),
    OutOfScopeCase("¿Cómo actualizo el sistema operativo?", "OS update — not in docs"),
]
