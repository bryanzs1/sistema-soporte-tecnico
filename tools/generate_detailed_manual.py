from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Optional

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
        return "HTTP endpoint"
    if any("socketio.on" in d for d in decos):
        return "Socket event"
    if fi.class_name:
        return "Class method"
    if fi.name.startswith("_"):
        return "Internal helper"
    return "Application helper"


def main_effects(source: str) -> List[str]:
    effects = []
    checks = [
        ("db.session.commit", "Persists database changes."),
        ("db.session.add", "Creates or stages new records in database session."),
        ("db.session.rollback", "Rolls back transaction on error."),
        ("render_template(", "Renders HTML template response."),
        ("jsonify(", "Returns JSON response."),
        ("flash(", "Sends user-visible feedback message."),
        ("send_email(", "Triggers email notification flow."),
        ("send_webhook(", "Triggers webhook notification flow."),
        ("query.get_or_404", "Loads resource or returns 404 automatically."),
        ("abort(", "Can terminate request with HTTP error code."),
        ("socketio.emit", "Broadcasts real-time event via Socket.IO."),
        ("redirect(", "Redirects browser to another route."),
    ]
    for token, message in checks:
        if token in source:
            effects.append(message)
    return effects


def permission_notes(fi: FunctionInfo) -> List[str]:
    notes = []
    decos = set(fi.decorators)
    if "login_required" in decos:
        notes.append("Requires authenticated session.")
    if "admin_required" in decos:
        notes.append("Requires administrator privileges.")
    if "tech_or_admin_required" in decos:
        notes.append("Requires technician or administrator role.")
    return notes


def function_purpose(fi: FunctionInfo, kind: str) -> str:
    if kind == "HTTP endpoint" and fi.route:
        methods = fi.methods or "GET"
        return f"Exposes route {fi.route} with HTTP methods {methods}. Handles web request lifecycle and returns UI/API output."
    if kind == "Socket event":
        return "Handles a real-time Socket.IO event for chat/presence synchronization."
    if kind == "Class method":
        return "Implements model/business behavior encapsulated in class logic."
    if kind == "Internal helper":
        return "Supports internal workflow orchestration and is not intended as public endpoint."
    return "Provides shared application utility behavior used by multiple flows."


def collect_functions(py_path: Path) -> List[FunctionInfo]:
    source = py_path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(source)
    module = py_path.relative_to(ROOT).as_posix()
    out: List[FunctionInfo] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.class_stack: List[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.class_stack.append(node.name)
            self.generic_visit(node)
            self.class_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
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
                )
            )
            self.generic_visit(node)

    Visitor().visit(tree)
    return out


def build_manual(all_funcs: List[FunctionInfo]) -> str:
    lines: List[str] = []
    lines.append("# Manual de Uso y Referencia Detallada de Funciones")
    lines.append("")
    lines.append("## 1. Alcance")
    lines.append("Este manual incluye uso funcional por rol y catalogo tecnico funcion por funcion del backend principal.")
    lines.append("")
    lines.append("## 2. Roles del sistema")
    lines.append("- Usuario: crea, consulta, comenta, califica y reabre tickets dentro de la ventana permitida.")
    lines.append("- Tecnico: gestiona flujo operativo de tickets, chat y conocimientos.")
    lines.append("- Administrador: gestiona configuracion, seguridad, usuarios, integraciones, auditoria y reportes.")
    lines.append("")
    lines.append("## 3. Modulos principales")
    lines.append("- app/auth.py: autenticacion, password, 2FA y cierre de sesion.")
    lines.append("- app/tickets.py: operaciones completas de tickets, chat y reaperturas.")
    lines.append("- app/admin.py: panel administrativo, settings, KB, integraciones y auditoria.")
    lines.append("- app/api.py: endpoints externos y webhooks.")
    lines.append("- app/routes.py: paginas publicas, health y utilidades de sesion.")
    lines.append("- app/models.py: entidades y reglas de negocio de datos.")
    lines.append("")

    lines.append("## 4. Referencia detallada de funciones")
    lines.append("La siguiente seccion describe cada funcion detectada en el paquete app.")
    lines.append("")

    funcs_sorted = sorted(all_funcs, key=lambda f: (f.module, f.lineno))

    current_module = None
    for fi in funcs_sorted:
        if fi.module != current_module:
            current_module = fi.module
            lines.append(f"### Modulo: {current_module}")
            lines.append("")

        owner = f"{fi.class_name}.{fi.name}" if fi.class_name else fi.name
        kind = classify(fi)
        purpose = function_purpose(fi, kind)
        effects = main_effects(fi.source_segment)
        perms = permission_notes(fi)

        lines.append(f"#### Funcion: {owner}")
        lines.append(f"- Ubicacion: {fi.module}:{fi.lineno}")
        lines.append(f"- Tipo: {kind}")
        if fi.route:
            lines.append(f"- Ruta: {fi.route}")
            lines.append(f"- Metodos HTTP: {fi.methods or 'GET'}")
        if fi.params:
            lines.append(f"- Parametros: {', '.join(fi.params)}")
        else:
            lines.append("- Parametros: sin parametros declarados")
        lines.append(f"- Que hace: {purpose}")

        if perms:
            lines.append("- Seguridad/Permisos:")
            for p in perms:
                lines.append(f"  - {p}")

        if effects:
            lines.append("- Efectos principales:")
            for e in effects:
                lines.append(f"  - {e}")

        lines.append("")

    lines.append("## 5. Notas operativas")
    lines.append("- Revisar POST_LAUNCH_CHECKLIST.md para validacion post despliegue.")
    lines.append("- Para regenerar este manual, ejecutar tools/generate_detailed_manual.py y luego tools/build_manual_pdf.py.")
    lines.append("")
    lines.append("Fin del documento.")
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
