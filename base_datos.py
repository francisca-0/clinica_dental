"""
Módulo / Librería de Base de Datos para Clínica Dental Sonrisas
==============================================================
Evaluación de Programación Orientada a Objeto Seguro.

Este módulo implementa una capa de persistencia completa utilizando SQLite,
almacenando todos los datos en un archivo con extensión '.bd' (por defecto: 'clinica.bd').

Características de seguridad y diseño:
- Consultas parametrizadas (prevención de Inyección SQL).
- Manejo de transacciones con commit/rollback seguro.
- Integridad referencial habilitada (FOREIGN KEYS ON DELETE CASCADE).
- Relación 1 a N: Cada paciente puede tener múltiples fichas médicas asociadas.
- Cada ficha médica puede incluir múltiples tratamientos o detalles clínicos.
- Compatible con objetos de 'modelos.py' y con diccionarios de datos estándar.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple


class BaseDatosClinica:
    """Gestor de persistencia SQLite en archivo .bd para pacientes y fichas médicas."""

    def __init__(self, ruta_bd: str = "clinica.bd"):
        """
        Inicializa la conexión a la base de datos y asegura que las tablas existan.
        :param ruta_bd: Nombre o ruta del archivo de base de datos (por defecto 'clinica.bd').
        """
        # Si se pasa una ruta relativa, ubicarla en el mismo directorio del script
        if not os.path.isabs(ruta_bd):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.ruta_bd = os.path.join(base_dir, ruta_bd)
        else:
            self.ruta_bd = ruta_bd

        self._crear_tablas()

    # -------------------------------------------------------------------------
    # Conexión Segura
    # -------------------------------------------------------------------------
    @contextmanager
    def _obtener_conexion(self):
        """Crea y configura la conexión con claves foráneas y cierre determinista."""
        conn = sqlite3.connect(self.ruta_bd)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _crear_tablas(self) -> None:
        """Crea las tablas de pacientes, fichas médicas y detalles si no existen."""
        with self._obtener_conexion() as conn:
            cursor = conn.cursor()

            # 1. Tabla Pacientes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pacientes (
                    rut TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    telefono TEXT DEFAULT '',
                    correo TEXT DEFAULT '',
                    historial_medico TEXT DEFAULT '',
                    alergias TEXT DEFAULT '',
                    alergia_anestesia INTEGER DEFAULT NULL, -- 1: Sí, 0: No, NULL: Sin registrar
                    dias_deuda_vencida INTEGER DEFAULT 0,
                    fecha_creacion TEXT NOT NULL
                );
            """)

            # 2. Tabla Fichas Médicas (asociadas al RUT del paciente)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fichas_medicas (
                    id_ficha INTEGER PRIMARY KEY AUTOINCREMENT,
                    paciente_rut TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    hora TEXT NOT NULL,
                    odontologo TEXT NOT NULL,
                    motivo_consulta TEXT DEFAULT '',
                    diagnostico TEXT DEFAULT '',
                    observaciones TEXT DEFAULT '',
                    estado TEXT DEFAULT 'registrada',
                    monto_total REAL DEFAULT 0.0,
                    valor_dolar_usado REAL DEFAULT NULL,
                    FOREIGN KEY (paciente_rut) REFERENCES pacientes(rut) ON DELETE CASCADE
                );
            """)

            # 3. Tabla Detalles de la Ficha (tratamientos y procedimientos de la sesión)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detalles_ficha (
                    id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_ficha INTEGER NOT NULL,
                    tratamiento TEXT NOT NULL,
                    cantidad INTEGER DEFAULT 1,
                    precio_unitario REAL DEFAULT 0.0,
                    subtotal REAL DEFAULT 0.0,
                    FOREIGN KEY (id_ficha) REFERENCES fichas_medicas(id_ficha) ON DELETE CASCADE
                );
            """)
            conn.commit()

    # -------------------------------------------------------------------------
    # CRUD de Pacientes
    # -------------------------------------------------------------------------
    def registrar_paciente(
        self,
        rut: str,
        nombre: str,
        telefono: str = "",
        correo: str = "",
        historial_medico: str = "",
        alergias: str = "",
        alergia_anestesia: Optional[bool] = None,
        dias_deuda_vencida: int = 0
    ) -> bool:
        """
        Inserta un nuevo paciente en la base de datos.
        Lanza ValueError si el RUT ya está registrado o si faltan datos obligatorios.
        """
        rut = rut.strip()
        nombre = nombre.strip()
        if not rut:
            raise ValueError("El RUT del paciente no puede estar vacío.")
        if not nombre:
            raise ValueError("El nombre del paciente no puede estar vacío.")

        # Convertir booleano a entero (o None) para SQLite
        val_anestesia = None if alergia_anestesia is None else (1 if alergia_anestesia else 0)
        ahora = datetime.now().isoformat(sep=" ", timespec="seconds")

        try:
            with self._obtener_conexion() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO pacientes (
                        rut, nombre, telefono, correo, historial_medico,
                        alergias, alergia_anestesia, dias_deuda_vencida, fecha_creacion
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    rut, nombre, telefono.strip(), correo.strip(),
                    historial_medico.strip(), alergias.strip(),
                    val_anestesia, int(dias_deuda_vencida), ahora
                ))
                conn.commit()
                return True
        except sqlite3.IntegrityError as e:
            raise ValueError(f"Ya existe un paciente registrado con el RUT '{rut}'.") from e

    def obtener_paciente(self, rut: str) -> Optional[Dict[str, Any]]:
        """Busca un paciente por su RUT y devuelve un diccionario con sus datos (o None si no existe)."""
        with self._obtener_conexion() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pacientes WHERE rut = ?;", (rut.strip(),))
            fila = cursor.fetchone()
            if not fila:
                return None
            return self._formatear_paciente(fila)

    def listar_pacientes(self) -> List[Dict[str, Any]]:
        """Devuelve una lista con todos los pacientes ordenados alfabéticamente por nombre."""
        with self._obtener_conexion() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pacientes ORDER BY nombre COLLATE NOCASE ASC;")
            filas = cursor.fetchall()
            return [self._formatear_paciente(f) for f in filas]

    def actualizar_paciente(self, rut: str, **campos) -> bool:
        """
        Actualiza uno o varios campos de un paciente (ej. telefono, correo, dias_deuda_vencida, etc.).
        """
        campos_permitidos = {
            "nombre", "telefono", "correo", "historial_medico",
            "alergias", "alergia_anestesia", "dias_deuda_vencida"
        }
        actualizaciones = {}
        for campo, valor in campos.items():
            if campo not in campos_permitidos:
                raise ValueError(f"Campo no modificable: '{campo}'.")
            if campo == "alergia_anestesia":
                actualizaciones[campo] = None if valor is None else (1 if valor else 0)
            elif campo == "dias_deuda_vencida":
                actualizaciones[campo] = int(valor)
            else:
                actualizaciones[campo] = str(valor).strip()

        if not actualizaciones:
            return False

        clausula_set = ", ".join([f"{c} = ?" for c in actualizaciones.keys()])
        valores = list(actualizaciones.values()) + [rut.strip()]

        with self._obtener_conexion() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE pacientes SET {clausula_set} WHERE rut = ?;", valores)
            conn.commit()
            if cursor.rowcount == 0:
                raise ValueError(f"No se encontró ningún paciente con el RUT '{rut}'.")
            return True

    def eliminar_paciente(self, rut: str) -> bool:
        """
        Elimina un paciente y todas sus fichas médicas asociadas (gracias a ON DELETE CASCADE).
        """
        with self._obtener_conexion() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pacientes WHERE rut = ?;", (rut.strip(),))
            conn.commit()
            if cursor.rowcount == 0:
                raise ValueError(f"No existe ningún paciente con el RUT '{rut}'.")
            return True

    # -------------------------------------------------------------------------
    # Gestión de Fichas Médicas (Relación 1 a N)
    # -------------------------------------------------------------------------
    def registrar_ficha_medica(
        self,
        paciente_rut: str,
        odontologo: str,
        fecha: Optional[str] = None,
        hora: Optional[str] = None,
        motivo_consulta: str = "",
        diagnostico: str = "",
        observaciones: str = "",
        estado: str = "registrada",
        monto_total: float = 0.0,
        valor_dolar_usado: Optional[float] = None,
        detalles: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """
        Crea una ficha médica para el paciente especificado y opcionalmente añade sus líneas de detalle.
        :param detalles: Lista de diccionarios con formato:
                         [{'tratamiento': str, 'cantidad': int, 'precio_unitario': float, 'subtotal': float}]
        :return: id_ficha autogenerado.
        """
        paciente_rut = paciente_rut.strip()
        paciente = self.obtener_paciente(paciente_rut)
        if not paciente:
            raise ValueError(f"No se puede registrar la ficha: No existe el paciente con RUT '{paciente_rut}'.")

        fecha_val = fecha or date.today().isoformat()
        hora_val = hora or datetime.now().strftime("%H:%M")
        detalles_val = detalles or []

        with self._obtener_conexion() as conn:
            cursor = conn.cursor()

            # Insertar cabecera de la ficha médica
            cursor.execute("""
                INSERT INTO fichas_medicas (
                    paciente_rut, fecha, hora, odontologo, motivo_consulta,
                    diagnostico, observaciones, estado, monto_total, valor_dolar_usado
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                paciente_rut, fecha_val, hora_val, odontologo.strip(),
                motivo_consulta.strip(), diagnostico.strip(), observaciones.strip(),
                estado.strip(), float(monto_total), valor_dolar_usado
            ))
            id_ficha = cursor.lastrowid

            # Insertar líneas de detalle si se proporcionaron
            for item in detalles_val:
                trat = item.get("tratamiento", "Procedimiento dental")
                cant = int(item.get("cantidad", 1))
                precio = float(item.get("precio_unitario", 0.0))
                subtotal = float(item.get("subtotal", cant * precio))

                cursor.execute("""
                    INSERT INTO detalles_ficha (
                        id_ficha, tratamiento, cantidad, precio_unitario, subtotal
                    ) VALUES (?, ?, ?, ?, ?);
                """, (id_ficha, trat, cant, precio, subtotal))

            conn.commit()
            return id_ficha

    def obtener_ficha_medica(self, id_ficha: int) -> Optional[Dict[str, Any]]:
        """Obtiene una ficha médica completa con su paciente y sus detalles de procedimientos."""
        with self._obtener_conexion() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.*, p.nombre AS paciente_nombre, p.telefono AS paciente_telefono,
                       p.correo AS paciente_correo, p.alergia_anestesia AS paciente_anestesia
                FROM fichas_medicas f
                JOIN pacientes p ON f.paciente_rut = p.rut
                WHERE f.id_ficha = ?;
            """, (id_ficha,))
            fila_ficha = cursor.fetchone()
            if not fila_ficha:
                return None

            # Obtener detalles
            cursor.execute("SELECT * FROM detalles_ficha WHERE id_ficha = ?;", (id_ficha,))
            filas_detalles = cursor.fetchall()

            ficha_dict = dict(fila_ficha)
            ficha_dict["detalles"] = [dict(d) for d in filas_detalles]
            return ficha_dict

    def listar_fichas_paciente(self, paciente_rut: str) -> List[Dict[str, Any]]:
        """
        Obtiene todo el historial de fichas médicas de un paciente específico,
        ordenadas de la más reciente a la más antigua.
        """
        paciente_rut = paciente_rut.strip()
        with self._obtener_conexion() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM fichas_medicas
                WHERE paciente_rut = ?
                ORDER BY fecha DESC, hora DESC, id_ficha DESC;
            """, (paciente_rut,))
            filas = cursor.fetchall()

            fichas = []
            for f in filas:
                f_dict = dict(f)
                cursor.execute("SELECT * FROM detalles_ficha WHERE id_ficha = ?;", (f["id_ficha"],))
                f_dict["detalles"] = [dict(d) for d in cursor.fetchall()]
                fichas.append(f_dict)
            return fichas

    def listar_todas_las_fichas(self) -> List[Dict[str, Any]]:
        """Lista todas las fichas médicas de la clínica con datos del paciente."""
        with self._obtener_conexion() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.*, p.nombre AS paciente_nombre
                FROM fichas_medicas f
                JOIN pacientes p ON f.paciente_rut = p.rut
                ORDER BY f.id_ficha DESC;
            """)
            filas = cursor.fetchall()
            resultado = []
            for f in filas:
                f_dict = dict(f)
                cursor.execute("SELECT * FROM detalles_ficha WHERE id_ficha = ?;", (f["id_ficha"],))
                f_dict["detalles"] = [dict(d) for d in cursor.fetchall()]
                resultado.append(f_dict)
            return resultado

    def actualizar_diagnostico_ficha(
        self, id_ficha: int, diagnostico: str, observaciones: str = ""
    ) -> bool:
        """Actualiza el diagnóstico y observaciones de una ficha médica ya registrada."""
        with self._obtener_conexion() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE fichas_medicas
                SET diagnostico = ?, observaciones = ?
                WHERE id_ficha = ?;
            """, (diagnostico.strip(), observaciones.strip(), id_ficha))
            conn.commit()
            if cursor.rowcount == 0:
                raise ValueError(f"No se encontró ninguna ficha médica con ID #{id_ficha}.")
            return True

    # -------------------------------------------------------------------------
    # Utilidades y Migración desde JSON
    # -------------------------------------------------------------------------
    def migrar_desde_json(self, ruta_json: str = "datos_clinica.json") -> Tuple[int, int]:
        """
        Importa automáticamente los datos de 'datos_clinica.json' a la base de datos .bd.
        Retorna una tupla: (pacientes_importados, fichas_importadas).
        """
        if not os.path.exists(ruta_json):
            raise FileNotFoundError(f"No se encontró el archivo JSON en: '{ruta_json}'.")

        with open(ruta_json, "r", encoding="utf-8") as f:
            datos = json.load(f)

        pacientes_cargados = 0
        fichas_cargadas = 0

        # 1. Cargar pacientes
        for p in datos.get("pacientes", []):
            try:
                self.registrar_paciente(
                    rut=p["rut"],
                    nombre=p["nombre"],
                    telefono=p.get("telefono", ""),
                    correo=p.get("correo", ""),
                    historial_medico=p.get("historial_medico", ""),
                    alergias=p.get("alergias", ""),
                    alergia_anestesia=p.get("alergia_anestesia"),
                    dias_deuda_vencida=p.get("dias_deuda_vencida", 0)
                )
                pacientes_cargados += 1
            except ValueError:
                # Si ya existía, actualizamos sus datos
                self.actualizar_paciente(
                    p["rut"],
                    nombre=p["nombre"],
                    telefono=p.get("telefono", ""),
                    correo=p.get("correo", ""),
                    historial_medico=p.get("historial_medico", ""),
                    alergias=p.get("alergias", ""),
                    alergia_anestesia=p.get("alergia_anestesia"),
                    dias_deuda_vencida=p.get("dias_deuda_vencida", 0)
                )

        # 2. Cargar atenciones como fichas médicas
        for a in datos.get("atenciones", []):
            # Comprobar si ya existe para evitar duplicación
            with self._obtener_conexion() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id_ficha FROM fichas_medicas
                    WHERE paciente_rut = ? AND fecha = ? AND hora = ?;
                """, (a["rut"], a.get("fecha"), a.get("hora")))
                if cursor.fetchone():
                    continue

            detalles_formateados = []
            for d in a.get("detalles", []):
                detalles_formateados.append({
                    "tratamiento": d.get("descripcion", "Tratamiento"),
                    "cantidad": d.get("cantidad", 1),
                    "precio_unitario": d.get("precio_unitario", 0.0),
                    "subtotal": d.get("cantidad", 1) * d.get("precio_unitario", 0.0)
                })

            try:
                self.registrar_ficha_medica(
                    paciente_rut=a["rut"],
                    odontologo="Dra. Ana Soto (Ortodoncia)",
                    fecha=a.get("fecha"),
                    hora=a.get("hora"),
                    motivo_consulta="Atención odontológica programada",
                    diagnostico="Procedimiento realizado según protocolo",
                    observaciones="Importado desde registro previo",
                    estado=a.get("estado", "registrada"),
                    monto_total=a.get("monto_total", 0.0),
                    valor_dolar_usado=a.get("valor_dolar_usado"),
                    detalles=detalles_formateados
                )
                fichas_cargadas += 1
            except ValueError:
                pass

        return pacientes_cargados, fichas_cargadas

    # -------------------------------------------------------------------------
    # Formateo Interno
    # -------------------------------------------------------------------------
    @staticmethod
    def _formatear_paciente(fila: sqlite3.Row) -> Dict[str, Any]:
        """Convierte una fila de base de datos a un diccionario amigable."""
        d = dict(fila)
        raw_anestesia = d["alergia_anestesia"]
        if raw_anestesia is None:
            d["alergia_anestesia_bool"] = None
            d["alergia_anestesia_texto"] = "Sin registrar"
        elif raw_anestesia == 1:
            d["alergia_anestesia_bool"] = True
            d["alergia_anestesia_texto"] = "Sí"
        else:
            d["alergia_anestesia_bool"] = False
            d["alergia_anestesia_texto"] = "No"
        return d


# =============================================================================
# Demostración interactiva / Menú de prueba directa
# =============================================================================
def _demo():
    print("=" * 65)
    print("   LIBRERÍA DE BASE DE DATOS (.BD) - CLÍNICA DENTAL SONRISAS")
    print("=" * 65)
    db = BaseDatosClinica("clinica.bd")
    print(f"Base de datos activa en: {db.ruta_bd}")

    # Verificar si existe datos_clinica.json y migrar
    json_path = os.path.join(os.path.dirname(__file__), "datos_clinica.json")
    if os.path.exists(json_path):
        pac, fich = db.migrar_desde_json(json_path)
        print(f"Sincronización inicial: {pac} pacientes y {fich} fichas desde JSON.")

    pacientes = db.listar_pacientes()
    print(f"\nTotal de pacientes en .BD: {len(pacientes)}")
    for p in pacientes:
        fichas = db.listar_fichas_paciente(p["rut"])
        print(f" - {p['nombre']} (RUT: {p['rut']}) -> {len(fichas)} ficha(s) médica(s) registrada(s).")
        for f in fichas:
            print(f"     * [Ficha #{f['id_ficha']}] Fecha: {f['fecha']} | Odontólogo: {f['odontologo']} | Total: ${f['monto_total']:,.0f}")
            for det in f["detalles"]:
                print(f"         · {det['tratamiento']} (x{det['cantidad']}): ${det['subtotal']:,.0f}")
    print("\nLibrería inicializada y probada con éxito.")


if __name__ == "__main__":
    _demo()
