from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Optional
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
OUT_MD = ROOT / "docs" / "MANUAL_USO_SISTEMA.md"


class FunctionInfo:
    def __init__(
        self,
        module: str,
        name: str,
        lineno: int,
        class_name: Optional[str],
        decorators: List[str],
        route: Optional[str],
        methods: Optional[str],
        source_segment: str,
        params: List[str],
        returns: str,
    ) -> None:
        self.module = module
        self.name = name
        self.lineno = lineno
        self.class_name = class_name
        self.decorators = decorators
        self.route = route
        self.methods = methods
        self.source_segment = source_segment
        self.params = params
        self.returns = returns


def decorator_text(deco: ast.AST) -> str:
    if isinstance(deco, ast.Call):
        func = deco.func
        if isinstance(func, ast.Attribute):
            base = ast.unparse(func.value) if hasattr(ast, "unparse") else ""
            return f"{base}.{func.attr}" if base else func.attr
        if isinstance(func, ast.Name):
            return func.id
    if isinstance(deco, ast.Attribute):
        base = ast.unparse(deco.value) if hasattr(ast, "unparse") else ""
        return f"{base}.{deco.attr}" if base else deco.attr
    if isinstance(deco, ast.Name):
        return deco.id
    return "decorator"


def extract_route_info(deco: ast.AST) -> tuple[Optional[str], Optional[str]]:
    if not isinstance(deco, ast.Call):
        return None, None
    if not isinstance(deco.func, ast.Attribute):
        return None, None
    if deco.func.attr != "route":
        return None, None

    path = None
    methods = None
    if deco.args:
        arg0 = deco.args[0]
        if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
            path = arg0.value
    for kw in deco.keywords:
        if kw.arg == "methods":
            try:
                methods = ast.literal_eval(kw.value)
            except Exception:
                methods = None
    if isinstance(methods, list):
        methods = ", ".join(str(m) for m in methods)
    return path, methods


def classify(fi: FunctionInfo) -> str:
    decos = set(fi.decorators)
    if fi.route:
        return "Endpoint HTTP"
    if any("socketio.on" in d for d in decos):
        return "Evento Socket.IO"
    if fi.class_name:
        return "Metodo de clase"
    if fi.name.startswith("_"):
        return "Helper interno"
    return "Funcion de aplicacion"


def main_effects(source: str) -> List[str]:
    effects = []
    checks = [
        ("db.session.commit", "Persiste cambios en base de datos."),
        ("db.session.add", "Registra nuevas entidades en la sesion ORM."),
        ("db.session.rollback", "Revierte transaccion ante error."),
        ("render_template(", "Renderiza una vista HTML para el cliente."),
        ("jsonify(", "Retorna respuesta JSON."),
        ("flash(", "Genera mensaje visible para usuario en UI."),
        ("send_email(", "Dispara notificacion por correo."),
        ("send_webhook(", "Dispara notificacion por webhook."),
        ("query.get_or_404", "Obtiene recurso o finaliza con 404."),
        ("abort(", "Interrumpe la solicitud con codigo HTTP de error."),
        ("socketio.emit", "Emite evento en tiempo real por Socket.IO."),
        ("redirect(", "Redirige la navegacion a otra ruta."),
    ]
    for token, message in checks:
        if token in source:
            effects.append(message)
    return effects


def permission_notes(fi: FunctionInfo) -> List[str]:
    notes = []
    decos = set(fi.decorators)
    if "login_required" in decos:
        notes.append("Requiere sesion autenticada.")
    if "admin_required" in decos:
        notes.append("Requiere privilegios de administrador.")
    if "tech_or_admin_required" in decos:
        notes.append("Requiere rol tecnico o administrador.")
    return notes


def output_notes(source: str) -> str:
    if "return app" in source:
        return "Instancia de aplicacion Flask"
    if "return True" in source or "return False" in source:
        return "Valor booleano"
    if "jsonify(" in source:
        return "JSON"
    if "render_template(" in source:
        return "HTML"
    if "redirect(" in source:
        return "Redireccion HTTP"
    if "Response(" in source:
        return "Response explicita"
    return "Depende del flujo interno"


def error_notes(source: str) -> List[str]:
    notes = []
    if "get_or_404" in source:
        notes.append("Puede finalizar en 404 cuando el recurso no existe.")
    if "abort(" in source:
        notes.append("Puede finalizar por autorizacion/validacion con abort().")
    if "rollback" in source:
        notes.append("Incluye rollback de transaccion en escenarios de excepcion.")
    if "except" in source:
        notes.append("Contiene manejo explicito de excepciones.")
    return notes


def function_purpose(fi: FunctionInfo, kind: str) -> str:
    name = fi.name.lower()
    if name == "create_app":
        return "Inicializa la aplicacion Flask, registra extensiones, blueprints y configuracion base de ejecucion."
    if kind == "Endpoint HTTP" and fi.route:
        return f"Atiende la ruta {fi.route} y ejecuta la logica funcional asociada a la solicitud web/API."
    if kind == "Evento Socket.IO":
        return "Sincroniza eventos en tiempo real para chat/presencia entre clientes conectados."
    if "create" in name:
        return "Crea entidades o registros en el sistema." 
    if "edit" in name or "update" in name:
        return "Actualiza datos existentes y aplica validaciones de negocio."
    if "delete" in name or "revoke" in name:
        return "Ejecuta acciones de eliminacion o revocacion controlada."
    if "list" in name or "search" in name:
        return "Consulta y filtra informacion para visualizacion o seleccion." 
    if "login" in name or "logout" in name or "password" in name:
        return "Gestiona flujo de autenticacion y seguridad de acceso." 
    if "report" in name or "dashboard" in name:
        return "Consolida metricas e indicadores para seguimiento operativo." 
    if kind == "Metodo de clase":
        return "Implementa comportamiento de dominio dentro del modelo/clase." 
    if kind == "Helper interno":
        return "Soporta pasos internos del flujo; no expuesto directamente a usuario final." 
    return "Provee utilidad compartida dentro del modulo." 


def collect_functions(py_path: Path) -> List[FunctionInfo]:
    source = py_path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(source)
    module = py_path.relative_to(ROOT).as_posix()
    out: List[FunctionInfo] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.class_stack: List[str] = []
            self.function_depth = 0

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.class_stack.append(node.name)
            self.generic_visit(node)
            self.class_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            # Skip nested local functions (e.g., wrappers inside decorators) to keep docs professional.
            if self.function_depth > 0 and not self.class_stack:
                self.function_depth += 1
                self.generic_visit(node)
                self.function_depth -= 1
                return

            decorators = [decorator_text(d) for d in node.decorator_list]
            route = None
            methods = None
            for deco in node.decorator_list:
                r, m = extract_route_info(deco)
                if r:
                    route = r
                    methods = m
                    break

            params = [a.arg for a in node.args.args]
            returns = ast.unparse(node.returns) if node.returns and hasattr(ast, "unparse") else ""
            try:
                seg = ast.get_source_segment(source, node) or ""
            except Exception:
                seg = ""

            out.append(
                FunctionInfo(
                    module=module,
                    name=node.name,
                    lineno=node.lineno,
                    class_name=self.class_stack[-1] if self.class_stack else None,
                    decorators=decorators,
                    route=route,
                    methods=methods,
                    source_segment=seg,
                    params=params,
                    returns=returns,
                )
            )
            self.function_depth += 1
            self.generic_visit(node)
            self.function_depth -= 1

    Visitor().visit(tree)
    return out


def build_manual(all_funcs: List[FunctionInfo]) -> str:
    lines: List[str] = []
    lines.append("# Manual Profesional de Funcionalidades del Sistema")
    lines.append("")
    lines.append("## 1. Presentacion")
    lines.append("Documento oficial del sistema de soporte tecnico orientado a operacion funcional. Este manual describe que hace el sistema y como se utiliza por rol, sin detalle de codigo fuente.")
    lines.append("")
    lines.append("- Version del manual: 2.1")
    lines.append(f"- Fecha de generacion: {date.today().isoformat()}")
    lines.append("- Enfoque: funcionalidades de negocio y operacion")
    lines.append("")
    lines.append("## 2. Publico objetivo")
    lines.append("- Direccion/Operacion: comprension de capacidades y controles del sistema.")
    lines.append("- Soporte tecnico: uso diario de flujos y validaciones.")
    lines.append("- Lideres de area: seguimiento de indicadores y calidad de servicio.")
    lines.append("")
    lines.append("## 3. Roles del sistema")
    lines.append("- Usuario: crea, consulta, comenta, califica y reabre tickets dentro de la ventana permitida.")
    lines.append("- Tecnico: gestiona flujo operativo de tickets, chat y conocimientos.")
    lines.append("- Administrador: gestiona configuracion, seguridad, usuarios, integraciones, auditoria y reportes.")
    lines.append("")
    lines.append("## 4. Funcionalidades principales")
    lines.append("- Gestion integral de tickets: creacion, asignacion, seguimiento, cierre y reapertura controlada.")
    lines.append("- Comunicacion integrada: comentarios y chat en tiempo real entre usuario y equipo tecnico.")
    lines.append("- Base de conocimiento: consulta de articulos y sugerencias automaticas durante la creacion de tickets.")
    lines.append("- Control de servicio: estado operativo, indicadores SLA, satisfaccion del usuario y reportes ejecutivos.")
    lines.append("- Gobierno y seguridad: control de acceso por rol, confirmaciones para acciones criticas, auditoria e integraciones empresariales.")
    lines.append("")

    lines.append("## 5. Flujo funcional de tickets")
    lines.append("1. Registro del caso: el usuario crea un ticket con categoria, prioridad y descripcion del incidente.")
    lines.append("2. Analisis inicial: el sistema enruta el caso y el equipo tecnico prioriza atencion segun severidad.")
    lines.append("3. Atencion y colaboracion: se intercambian mensajes, evidencias y actualizaciones de avance.")
    lines.append("4. Resolucion: el tecnico documenta solucion, aplica cierre y deja trazabilidad del proceso.")
    lines.append("5. Validacion del usuario: el usuario confirma resultado y registra calificacion de satisfaccion.")
    lines.append("6. Reapertura controlada: si persiste la incidencia, se habilita reapertura con motivo dentro del plazo permitido.")
    lines.append("")
    lines.append("## 6. Funcionalidades por rol")
    lines.append("### 6.1 Usuario")
    lines.append("- Crear tickets y adjuntar informacion del incidente.")
    lines.append("- Consultar estado y progreso en su panel.")
    lines.append("- Enviar comentarios y responder en el chat del caso.")
    lines.append("- Reabrir tickets con motivo cuando aplique.")
    lines.append("- Calificar la atencion recibida al cierre del servicio.")
    lines.append("")
    lines.append("### 6.2 Tecnico")
    lines.append("- Visualizar cola de tickets por prioridad y estado.")
    lines.append("- Tomar, actualizar y cerrar casos con trazabilidad.")
    lines.append("- Mantener comunicacion continua con el solicitante.")
    lines.append("- Consultar respuestas rapidas y base de conocimiento para resolver mas rapido.")
    lines.append("- Gestionar reaperturas y cumplimiento de tiempos de atencion.")
    lines.append("")
    lines.append("### 6.3 Administrador")
    lines.append("- Administrar usuarios, perfiles y permisos.")
    lines.append("- Configurar parametros del sistema, politicas y plantillas operativas.")
    lines.append("- Supervisar auditoria, actividad sensible e integraciones.")
    lines.append("- Revisar indicadores de servicio, cumplimiento y calidad.")
    lines.append("- Coordinar mejoras continuas sobre procesos de soporte.")
    lines.append("")
    lines.append("## 7. Seguridad y control")
    lines.append("- Acceso controlado por autenticacion y roles.")
    lines.append("- Confirmaciones reforzadas para acciones criticas.")
    lines.append("- Registro de eventos para trazabilidad y auditoria.")
    lines.append("- Politicas de sesion y validacion para reducir errores operativos.")
    lines.append("")
    lines.append("## 8. Indicadores y seguimiento")
    lines.append("- Seguimiento de tiempos de atencion y cumplimiento de SLA.")
    lines.append("- Medicion de satisfaccion de usuario y calidad de resolucion.")
    lines.append("- Vista ejecutiva para monitoreo de volumen, estado y tendencia de casos.")
    lines.append("")

    lines.append("## 9. Herramientas del proyecto y su funcion")
    lines.append("- Python: lenguaje base para logica de negocio y servicios backend.")
    lines.append("- Flask: framework web principal para rutas, vistas y ciclo de solicitudes.")
    lines.append("- Flask-SQLAlchemy: capa ORM para modelado y acceso a datos.")
    lines.append("- Flask-Migrate: control de migraciones de esquema de base de datos.")
    lines.append("- Flask-Login: autenticacion de sesiones y control de usuario activo.")
    lines.append("- Flask-WTF: formularios con validaciones y proteccion CSRF.")
    lines.append("- Flask-Limiter: limitacion de intentos para proteger endpoints sensibles.")
    lines.append("- Flask-Talisman: endurecimiento de cabeceras de seguridad HTTP.")
    lines.append("- Flask-CORS: control de acceso entre origenes para integraciones web/API.")
    lines.append("- Flask-Mail: envio de notificaciones por correo.")
    lines.append("- Flask-SocketIO: comunicacion en tiempo real para chat y eventos operativos.")
    lines.append("- eventlet: soporte de concurrencia para Socket.IO en produccion.")
    lines.append("- redis: backend de mensajeria/cache para eventos y escalabilidad.")
    lines.append("- psycopg2-binary: conector PostgreSQL para persistencia en entorno productivo.")
    lines.append("- gunicorn: servidor WSGI de ejecucion en despliegues Linux/Render.")
    lines.append("- python-dotenv: carga de variables de entorno desde archivo .env.")
    lines.append("- pyotp: generacion y validacion de codigos TOTP para 2FA.")
    lines.append("- qrcode y pillow: generacion de imagen QR para enrolamiento 2FA.")
    lines.append("- sentry-sdk: monitoreo de errores y telemetria de excepciones.")
    lines.append("- marshmallow: serializacion y validacion de estructuras de datos.")
    lines.append("- cryptography: cifrado y operaciones criptograficas de soporte.")
    lines.append("- requests: consumo de APIs externas y validaciones de conectividad.")
    lines.append("- beautifulsoup4: parsing HTML en utilidades de integracion/analisis.")
    lines.append("- pandas: analisis tabular para reportes y consolidaciones.")
    lines.append("- scikit-learn y numpy: capacidades de analitica/modelado en componentes inteligentes.")
    lines.append("- textblob: apoyo NLP para procesamiento de texto y clasificacion basica.")
    lines.append("")
    lines.append("## 10. Notas operativas")
    lines.append("- Revisar POST_LAUNCH_CHECKLIST.md para validacion post despliegue.")
    lines.append("- Regeneracion del documento: ejecutar tools/generate_detailed_manual.py y luego tools/build_manual_pdf.py.")
    lines.append("")
    lines.append("Documento funcional del sistema (sin detalle tecnico de codigo).")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    py_files = sorted(APP_DIR.glob("*.py"))
    all_funcs: List[FunctionInfo] = []
    for py in py_files:
        all_funcs.extend(collect_functions(py))

    manual = build_manual(all_funcs)
    OUT_MD.write_text(manual, encoding="utf-8")
    print(f"Detailed manual generated: {OUT_MD}")


if __name__ == "__main__":
    main()
