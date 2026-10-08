"""
Clínica Dental Sonrisas - programa de consola
Evaluación Sumativa N°1 - Programación Orientada a Objeto Seguro (TI3V21)
Ejecutar:  python main.py
"""
from datetime import datetime
import math
import os
import re
import sys

# Asegurar codificación UTF-8 en Windows para evitar caídas por acentos o caracteres
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from clinica import Clinica
from modelos import Cirugia, IndicadorNoDisponible, Paciente, Persona



RUTA_DATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos_clinica.json")


# ---------------------------------------------------------------------------
# Entrada de datos segura (nunca se cae por una entrada mala)
# ---------------------------------------------------------------------------
def clp(valor: float) -> str:
    return "$" + f"{valor:,.0f}".replace(",", ".")


def leer_texto(mensaje: str, obligatorio: bool = True) -> str:
    while True:
        valor = input(mensaje).strip()
        if valor or not obligatorio:
            return valor
        print("  Este dato es obligatorio.")


def leer_numero(mensaje: str, entero: bool = False, minimo: float = 0):
    """Pide un número; si escriben letras, muestra un mensaje y vuelve a pedir."""
    while True:
        texto = input(mensaje).strip().replace(",", ".")
        try:
            numero = int(texto) if entero else float(texto)
        except ValueError:
            print("  Debes ingresar un número" + (" entero." if entero else " (ej. 25000)."))
            continue
        if not math.isfinite(numero) or numero < minimo:
            print(f"  El número debe ser mayor o igual a {minimo:g}.")
            continue
        return numero


def leer_si_no(mensaje: str) -> bool:
    while True:
        r = input(mensaje + " (s/n): ").strip().lower()
        if r in ("s", "si", "sí"):
            return True
        if r in ("n", "no"):
            return False
        print("  Responde 's' o 'n'.")


def leer_rut(mensaje: str) -> str:
    while True:
        rut = input(mensaje).strip()
        try:
            return Persona.normalizar_rut(rut)
        except ValueError as e:
            print(f"  {e} Ejemplo válido: 12.345.678-5")


def leer_hora(mensaje: str) -> str:
    while True:
        h = input(mensaje).strip()
        if not h:
            return datetime.now().strftime("%H:%M")
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", h)
        if m and int(m.group(1)) < 24 and int(m.group(2)) < 60:
            return f"{int(m.group(1)):02d}:{m.group(2)}"
        print("  Hora inválida. Formato HH:MM (ej. 10:30) o presiona Enter para usar la hora actual.")



def leer_alergia_anestesia():
    while True:
        r = input("¿Alergia a la anestesia? (s = sí / n = no / x = sin registrar): ").strip().lower()
        if r in ("s", "si", "sí"):
            return True
        if r in ("n", "no"):
            return False
        if r == "x":
            return None
        print("  Responde s, n o x.")


def pedir_dato(constructor_mensaje):
    """Repite la pregunta hasta que el dato sea aceptado por el modelo."""
    while True:
        try:
            return constructor_mensaje()
        except ValueError as e:
            print(f"  {e}")


# ---------------------------------------------------------------------------
# Pacientes
# ---------------------------------------------------------------------------
def mostrar_paciente(p: Paciente):
    print(f"  - {p.nombre} | RUT {p.rut_formateado} | Tel: {p.telefono or '-'} | "
          f"Correo: {p.correo or '-'}")
    print(f"      Alergia anestesia: {p.texto_alergia_anestesia} | Otras alergias: {p.alergias or '-'} | "
          f"Estado: {p.verificar_estado_financiero()}")


def registrar_paciente(c: Clinica):
    print("\n--- Registrar paciente ---")
    rut = leer_rut("RUT del paciente: ")
    if c.buscar_paciente(rut):
        print("  Ya existe un paciente con ese RUT.")
        return
    nombre = leer_texto("Nombre completo: ")
    telefono = pedir_dato(lambda: Persona.validar_telefono(input("Teléfono (opcional): ")))
    correo = pedir_dato(lambda: Persona.validar_correo(input("Correo (opcional): ")))
    alergia = leer_alergia_anestesia()
    dias = int(leer_numero("Días de deuda vencida (0 si está al día): ", entero=True))
    try:
        p = c.registrar_paciente(rut, nombre, telefono, correo,
                                 alergia_anestesia=alergia, dias_deuda_vencida=dias)
    except ValueError as e:
        print(f"  No se pudo guardar: {e}")
        return
    print(f"  Paciente {p.nombre} guardado correctamente.")


def listar_pacientes(c: Clinica):
    print("\n--- Pacientes ---")
    pacientes = c.listar_pacientes()
    if not pacientes:
        print("  No hay pacientes registrados.")
    for p in pacientes:
        mostrar_paciente(p)


def elegir_paciente(c: Clinica):
    if not c.pacientes:
        print("\n  [AVISO] No hay pacientes registrados todavía.")
        if leer_si_no("  ¿Deseas registrar un paciente ahora?"):

            registrar_paciente(c)
            if c.pacientes:
                return list(c.pacientes.values())[-1]
        return None

    lista = list(c.pacientes.values())
    print("\n--- Pacientes registrados ---")
    for idx, p in enumerate(lista, 1):
        print(f"   {idx}) {p.nombre} (RUT: {p.rut_formateado}) | Tel: {p.telefono or '-'}")

    while True:
        entrada = input("  Elige el NÚMERO del paciente o ingresa su RUT: ").strip()
        if not entrada:
            return None
        if entrada.isdigit() and 1 <= int(entrada) <= len(lista):
            return lista[int(entrada) - 1]
        p = c.buscar_paciente(entrada)
        if p is not None:
            return p
        print("  No se encontró un paciente con ese RUT o número. Intenta de nuevo (o presiona Enter para cancelar).")



def modificar_paciente(c: Clinica):
    print("\n--- Modificar paciente ---")
    p = elegir_paciente(c)
    if not p:
        return
    mostrar_paciente(p)
    print("  ¿Qué quieres cambiar?\n   1) Teléfono\n   2) Correo\n   3) Alergia a la anestesia"
          "\n   4) Otras alergias\n   5) Días de deuda vencida\n   6) Agregar al historial médico")
    op = input("Opción: ").strip()
    try:
        if op == "1":
            c.modificar_paciente(p.rut, "telefono", input("Nuevo teléfono: "))
        elif op == "2":
            c.modificar_paciente(p.rut, "correo", input("Nuevo correo: "))
        elif op == "3":
            c.modificar_paciente(p.rut, "alergia_anestesia", leer_alergia_anestesia())
        elif op == "4":
            c.modificar_paciente(p.rut, "alergias", input("Alergias (texto): ").strip())
        elif op == "5":
            c.modificar_paciente(p.rut, "dias_deuda_vencida",
                                 int(leer_numero("Días de deuda vencida: ", entero=True)))
        elif op == "6":
            nuevo = input("Nota para el historial: ").strip()
            p.actualizar_historial(nuevo)
            c.guardar()
        else:
            print("  Opción inválida.")
            return
    except ValueError as e:
        print(f"  No se pudo modificar: {e}")
        return
    print("  Cambio guardado.")


def eliminar_paciente(c: Clinica):
    print("\n--- Eliminar paciente ---")
    p = elegir_paciente(c)
    if not p:
        return
    mostrar_paciente(p)
    if leer_si_no("¿Seguro que quieres eliminarlo?"):
        c.eliminar_paciente(p.rut)
        print("  Paciente eliminado.")
    else:
        print("  No se eliminó nada.")


# ---------------------------------------------------------------------------
# Tratamientos
# ---------------------------------------------------------------------------
def mostrar_catalogo(c: Clinica, con_dolar: bool = True):
    print("\n========================================================")
    print("        CATÁLOGO DE TRATAMIENTOS DENTALES")
    print("========================================================")
    if any(t.TIPO == "Ortodoncia" for t in c.tratamientos.values()) and con_dolar:
        if c.refrescar_dolar():
            print(f"  * Dólar del día: {clp(c.indicador.valor_dolar)} (fecha {c.indicador.fecha})")
        else:
            print("  * AVISO: Sin conexión a API del dólar. La ortodoncia no se puede calcular ahora.")
    print("-" * 56)
    for t in c.tratamientos.values():
        try:
            costo = clp(t.calcular_costo(c.indicador))
        except IndicadorNoDisponible:
            costo = "No disponible (sin dólar)"
        extra = ""
        if t.TIPO == "Ortodoncia":
            extra = f" (USD ${t.costo_base:g} base x dólar {clp(c.indicador.valor_dolar)})" if c.indicador.valor_dolar else ""
        elif t.TIPO == "Cirugia":

            extra = " (Costo base con recargo de cirugía x1.5 incluido)"
        print(f"  {t.id_tratamiento}) [{t.TIPO.upper()}] {t.descripcion}")
        print(f"      - Duración: {t.calcular_duracion()} min")
        print(f"      - Valor:    {costo}{extra}")
    print("========================================================\n")




def crear_tratamiento(c: Clinica):
    print("\n--- Crear tratamiento ---")
    print("  Tipo:\n   1) Limpieza\n   2) Ortodoncia\n   3) Cirugía")
    op = input("Opción: ").strip()
    tipo = {"1": "Limpieza", "2": "Ortodoncia", "3": "Cirugia"}.get(op)
    if tipo is None:
        print("  Opción inválida.")
        return
    desc = leer_texto("Descripción: ")
    try:
        if tipo == "Limpieza":
            costo = leer_numero("Costo base en pesos: ")
            t = c.crear_tratamiento(tipo, desc, costo,
                                    tipo_cepillado=input("Tipo de cepillado (ej. Ultrasónico): ").strip() or "Manual")
        elif tipo == "Ortodoncia":
            costo = leer_numero("Costo base en USD (se multiplica por el dólar del día): ")
            t = c.crear_tratamiento(tipo, desc, costo,
                                    tipo_brackets=input("Tipo de brackets (ej. Metálicos): ").strip() or "Metálicos",
                                    cantidad_meses=int(leer_numero("Meses de tratamiento: ", entero=True, minimo=1)))
        else:
            costo = leer_numero("Costo base en pesos: ")
            t = c.crear_tratamiento(tipo, desc, costo,
                                    requiere_pabellon_especial=leer_si_no("¿Requiere pabellón especial?"))
    except ValueError as e:
        print(f"  No se pudo crear: {e}")
        return
    print(f"  Tratamiento #{t.id_tratamiento} creado. Duración: {t.calcular_duracion()} min.")
    if tipo == "Ortodoncia":
        if c.refrescar_dolar():
            print(f"  Costo hoy: {clp(t.calcular_costo(c.indicador))} (dólar {clp(c.indicador.valor_dolar)})")
        else:
            print("  Aviso: no se pudo obtener el dólar; el costo no se puede calcular ahora.")
    else:
        print(f"  Costo: {clp(t.calcular_costo(c.indicador))}")


# ---------------------------------------------------------------------------
# Atenciones
# ---------------------------------------------------------------------------
def registrar_atencion(c: Clinica):
    print("\n========================================================")
    print("           AGENDAR CITA / REGISTRAR ATENCIÓN            ")
    print("========================================================")
    paciente = elegir_paciente(c)
    if not paciente:
        return

    hora = leer_hora(f"  Hora de la cita (HH:MM) [Enter para {datetime.now().strftime('%H:%M')}]: ")

    # Refrescar indicador de dólar antes de mostrar opciones
    c.refrescar_dolar()

    print("\n--- Tratamientos disponibles con sus valores ---")
    for t in c.tratamientos.values():
        try:
            costo_val = clp(t.calcular_costo(c.indicador))
        except IndicadorNoDisponible:
            costo_val = "Dólar no disponible"
        extra_info = ""
        if t.TIPO == "Ortodoncia" and c.indicador.valor_dolar:
            extra_info = f" (USD ${t.costo_base:g} base x dólar {clp(c.indicador.valor_dolar)})"
        elif t.TIPO == "Cirugia":

            extra_info = " (incluye recargo x1.5)"
        print(f"   {t.id_tratamiento}) [{t.TIPO.upper()}] {t.descripcion}")
        print(f"       -> Valor: {costo_val}{extra_info} | Duración aprox: {t.calcular_duracion()} min")

    items = []
    while True:
        id_t = int(leer_numero("\n  Ingresa el NÚMERO del tratamiento: ", entero=True, minimo=1))
        t = c.tratamientos.get(id_t)
        if t is None:
            print("  Ese número de tratamiento no existe en el catálogo.")
            continue

        cant_txt = input("  Cantidad de sesiones/procedimientos [Enter = 1]: ").strip()
        cantidad = int(cant_txt) if (cant_txt.isdigit() and int(cant_txt) >= 1) else 1
        items.append((t, cantidad))

        try:
            sub = clp(t.calcular_costo(c.indicador) * cantidad)
        except IndicadorNoDisponible:
            sub = "Por confirmar"
        print(f"  [OK] Agregado: {t.descripcion} (x{cantidad}) | Subtotal: {sub} | Duración: {t.calcular_duracion() * cantidad} min")

        otro = input("\n  ¿Deseas agregar otro tratamiento adicional a esta misma cita? (s/n) [n]: ").strip().lower()
        if otro not in ("s", "si", "sí"):
            break

    if not items:
        print("  No agregaste ningún tratamiento; se canceló la cita.")
        return

    pabellon = True
    if any(isinstance(t, Cirugia) and t.requiere_pabellon_especial for t, _ in items):
        pabellon = leer_si_no("  La cita incluye una cirugía con pabellón especial. ¿Está disponible el pabellón?")

    ok, motivo, atencion = c.registrar_atencion(paciente, hora, items, pabellon)

    if ok:
        duracion_total = sum(d.tratamiento.calcular_duracion() * d.cantidad for d in atencion.detalles)
        print("\n" + "=" * 65)
        print("               [OK] CITA AGENDADA CON ÉXITO")
        print("=" * 65)
        print(f"  Ficha de Atención N°:   #{atencion.id_atencion}")
        print(f"  Fecha de la cita:       {atencion.fecha.strftime('%d/%m/%Y')}")
        print(f"  Hora agendada:          {atencion.hora} hrs")
        print(f"  Estado de la cita:      {atencion.estado.upper()}")
        print("-" * 65)
        print("  DATOS DEL PACIENTE:")
        print(f"    Nombre:               {paciente.nombre}")
        print(f"    RUT:                  {paciente.rut_formateado}")
        print(f"    Teléfono:             {paciente.telefono or 'No registrado'}")
        print(f"    Alergia a anestesia:  {paciente.texto_alergia_anestesia}")
        print(f"    Situación financiera: {paciente.verificar_estado_financiero()} ({paciente.dias_deuda_vencida} días)")
        print("-" * 65)
        print("  PROFESIONALES A CARGO:")
        print(f"    Odontólogo tratante:  {c.odontologo.nombre} ({c.odontologo.especialidad})")
        print(f"                          Reg. Profesional: {c.odontologo.registro_profesional}")
        print(f"    Asistente dental:     {c.asistente.nombre} (Turno: {c.asistente.turno})")

        print("-" * 65)
        print("  DETALLE DEL TRATAMIENTO Y VALORES:")
        for d in atencion.detalles:
            t = d.tratamiento
            extra_calc = ""
            if t.TIPO == "Ortodoncia" and atencion.valor_dolar_usado:
                extra_calc = f" (USD ${t.costo_base:g} x ${atencion.valor_dolar_usado:,.0f})"
            elif t.TIPO == "Cirugia":

                extra_calc = f" (Base {clp(t.costo_base)} + recargo cirugía x1.5)"
            dur_d = t.calcular_duracion() * d.cantidad
            print(f"    * [{t.TIPO.upper()}] {d.descripcion}")
            print(f"      Cantidad: {d.cantidad} | Duración: {dur_d} min | Valor unitario: {clp(d.precio_unitario)}{extra_calc}")
            print(f"      Subtotal a pagar: {clp(d.calcular_subtotal())}")
        print("-" * 65)
        print(f"  DURACIÓN TOTAL ESTIMADA:  {duracion_total} minutos")
        if atencion.valor_dolar_usado:
            print(f"  DÓLAR DEL DÍA OBSERVADO: {clp(atencion.valor_dolar_usado)} (mindicador.cl)")
        print(f"  TOTAL A PAGAR DE LA CITA: {clp(atencion.monto_total)}")
        print("=" * 65)
        if paciente.alergia_anestesia and any(isinstance(d.tratamiento, Cirugia) for d in atencion.detalles):
            print("\n  [!] PRECAUCIÓN MÉDICA: El paciente tiene registrada alergia a la anestesia.")
            print("      Aplicar protocolo de anestesia alternativa antes del procedimiento.")
        print()
    else:
        print("\n" + "=" * 65)
        print("  [X] CITA NO AGENDADA (RECHAZADA)")
        print(f"  Motivo del rechazo: {motivo}")
        print("=" * 65 + "\n")



def ver_atenciones(c: Clinica):
    print("\n========================================================")
    print("             FICHAS DE ATENCIÓN REGISTRADAS             ")
    print("========================================================")
    if not c.atenciones:
        print("  Aún no hay fichas registradas.")
        print("========================================================\n")
        return
    for a in c.atenciones:
        print(f"\n  [Ficha #{a.id_atencion}] Fecha: {a.fecha} | Hora: {a.hora} hrs | Estado: {a.estado.upper()}")
        print(f"  Paciente:   {a.paciente_nombre} (RUT: {a.paciente_rut})")
        print(f"  Odontólogo: {a.odontologo.nombre} ({a.odontologo.especialidad})")
        print("  Tratamientos incluidos:")
        for d in a.detalles:
            sub = clp(d.calcular_subtotal()) if d.precio_unitario else "Pendiente"
            precio = clp(d.precio_unitario) if d.precio_unitario else "-"
            print(f"    · {d.descripcion} (x{d.cantidad}) | Unitario: {precio} | Subtotal: {sub}")
        if a.valor_dolar_usado:
            print(f"  Dólar aplicado: {clp(a.valor_dolar_usado)}")
        print(f"  TOTAL DE LA ATENCIÓN: {clp(a.monto_total) if a.monto_total else '-'}")
        print("-" * 56)
    print()



def consultar_dolar(c: Clinica):
    print("\n--- Dólar del día ---")
    if c.refrescar_dolar():
        print(f"  Valor: {clp(c.indicador.valor_dolar)} (fecha {c.indicador.fecha}). "
              f"Compáralo con https://mindicador.cl/api/dolar")
    else:
        print("  No se pudo obtener el valor del dólar (revisa tu conexión a internet).")


def ver_permisos(c: Clinica):
    print("\n--- Permisos de trabajadores ---")
    for accion in ("diagnosticar", "realizar_tratamiento", "agendar_hora", "preparar_instrumental"):
        print(f"  {accion}: Odontólogo={c.odontologo.verificar_permisos(accion)} | "
              f"Asistente={c.asistente.verificar_permisos(accion)}")


def consultar_ficha_medica_bd(c: Clinica):
    print("\n========================================================")
    print("      CONSULTAR FICHA MÉDICA DE PACIENTE (.BD)          ")
    print("========================================================")
    paciente = elegir_paciente(c)
    if not paciente:
        return

    fichas = c.bd.listar_fichas_paciente(paciente.rut)

    print("\n" + "=" * 65)
    print(f"  HISTORIAL CLÍNICO: {paciente.nombre.upper()}")
    print("=" * 65)
    print(f"  RUT:                  {paciente.rut_formateado}")
    print(f"  Teléfono:             {paciente.telefono or 'No registrado'}")
    print(f"  Correo:               {paciente.correo or 'No registrado'}")
    print(f"  Alergia anestesia:    {paciente.texto_alergia_anestesia}")
    print(f"  Otras alergias:       {paciente.alergias or 'Ninguna registrada'}")
    print(f"  Situación financiera: {paciente.verificar_estado_financiero()}")
    print(f"  Historial base:       {paciente.historial_medico or 'Sin anotaciones previas'}")
    print("-" * 65)
    print(f"  FICHAS MÉDICAS REGISTRADAS EN LA BD ({len(fichas)} encontrada(s)):")
    print("-" * 65)

    if not fichas:
        print("  Este paciente aún no registra fichas médicas en la base de datos.")
    else:
        for idx, f in enumerate(fichas, 1):
            print(f"\n  [Ficha Médica N° {f['id_ficha']}]  ({idx} de {len(fichas)})")
            print(f"    Fecha y hora:       {f['fecha']} a las {f['hora']} hrs")
            print(f"    Profesional:        {f['odontologo']}")
            print(f"    Motivo consulta:    {f['motivo_consulta'] or 'Atención clínica'}")
            print(f"    Diagnóstico:        {f['diagnostico'] or 'En evaluación'}")
            if f.get('observaciones'):
                print(f"    Observaciones:      {f['observaciones']}")
            print(f"    Estado de atención: {f['estado'].upper()}")
            print("    Tratamientos / Procedimientos:")
            for d in f.get("detalles", []):
                print(f"      · {d['tratamiento']} (x{d['cantidad']}) -> Subtotal: {clp(d['subtotal'])}")
            print(f"    MONTO TOTAL:        {clp(f['monto_total'])}")
            print("  " + "." * 55)
    print("=" * 65 + "\n")


# ---------------------------------------------------------------------------
# Menú
# ---------------------------------------------------------------------------
def menu():
    c = Clinica(RUTA_DATOS)
    if c.mensaje_carga:
        print(f"AVISO: {c.mensaje_carga}")
    opciones = {
        "1": ("Registrar paciente", registrar_paciente),
        "2": ("Listar pacientes", listar_pacientes),
        "3": ("Modificar paciente", modificar_paciente),
        "4": ("Eliminar paciente", eliminar_paciente),
        "5": ("Crear tratamiento", crear_tratamiento),
        "6": ("Ver tratamientos (duración y costo)", mostrar_catalogo),
        "7": ("Registrar ficha de atención", registrar_atencion),
        "8": ("Ver fichas de atención (detalle)", ver_atenciones),
        "9": ("Consultar ficha médica de paciente (.BD)", consultar_ficha_medica_bd),
        "10": ("Consultar dólar del día", consultar_dolar),
        "11": ("Ver permisos de trabajadores", ver_permisos),
    }
    while True:
        print("\n===== Clínica Dental Sonrisas =====")
        for clave, (titulo, _) in opciones.items():
            print(f"  {clave}) {titulo}")
        print("  0) Salir")
        eleccion = input("Elige una opción: ").strip()
        if eleccion == "0":
            print("¡Hasta luego!")
            return
        accion = opciones.get(eleccion)
        if accion is None:
            print("  Opción inválida, intenta de nuevo.")
            continue
        try:
            accion[1](c)
        except (KeyboardInterrupt, EOFError):
            raise
        except Exception as e:  # el programa nunca se cae por un error inesperado
            print(f"  Ocurrió un error inesperado ({type(e).__name__}: {e}). Volviendo al menú.")


if __name__ == "__main__":
    try:
        menu()
    except (KeyboardInterrupt, EOFError):
        print("\nPrograma finalizado.")
