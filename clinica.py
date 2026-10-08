"""Lógica de la clínica: pacientes, catálogo, atenciones y guardado en JSON."""
from __future__ import annotations

import json
import os
from typing import Optional

from base_datos import BaseDatosClinica
from modelos import (AsistenteDental, AtencionMedica, Cirugia, IndicadorExterno,
                     IndicadorNoDisponible, Limpieza, Odontologo, Ortodoncia,
                     Paciente, Persona, Radiografia, TIPOS_TRATAMIENTO,
                     TratamientoDental)

CAMPOS_MODIFICABLES = {"telefono", "correo", "alergias", "alergia_anestesia",
                       "dias_deuda_vencida", "historial_medico"}


class Clinica:
    def __init__(self, ruta_datos: str):
        self.ruta = ruta_datos
        self.bd = BaseDatosClinica(os.path.join(os.path.dirname(self.ruta), "clinica.bd"))
        self.indicador = IndicadorExterno()
        self.odontologo = Odontologo("11111111-1", "Dra. Ana Soto", "912345678",
                                     "ana.soto@clinica.cl", "OD-01", "Mañana",
                                     "Ortodoncia", "COL-4521")
        self.asistente = AsistenteDental("22222222-2", "Pedro Ríos", "987654321",
                                         "pedro.rios@clinica.cl", "AS-01", "Tarde",
                                         "Cert. Asistencial N°10")
        self.pacientes: dict[str, Paciente] = {}
        self.tratamientos: dict[int, TratamientoDental] = {}
        self.atenciones: list[AtencionMedica] = []
        self._sig_atencion = 1
        self.mensaje_carga: Optional[str] = None
        self._cargar()

    # -- Persistencia ---------------------------------------------------------
    def _vaciar(self):
        self.pacientes, self.tratamientos, self.atenciones = {}, {}, []
        self._sig_atencion = 1

    def _sembrar_catalogo(self):
        for t in (Limpieza(1, "Limpieza dental general", 25000, "Ultrasónico"),
                  Ortodoncia(2, "Instalación de brackets (costo base en USD)", 300, "Metálicos", 18),
                  Cirugia(3, "Extracción de muela del juicio", 80000, True),
                  Radiografia(4, "Radiografía panorámica", 15000)):
            self.tratamientos[t.id_tratamiento] = t

    def _cargar(self):
        if not os.path.exists(self.ruta):
            self._sembrar_catalogo()
            self.guardar()
            return
        try:
            with open(self.ruta, encoding="utf-8") as f:
                d = json.load(f)
            self.pacientes = {p["rut"]: Paciente.from_dict(p) for p in d["pacientes"]}
            trats = [TratamientoDental.from_dict(t) for t in d["tratamientos"]]
            self.tratamientos = {t.id_tratamiento: t for t in trats}
            self.atenciones = [AtencionMedica.from_dict(a, self.odontologo) for a in d["atenciones"]]
            self._sig_atencion = int(d["siguiente_atencion"])
        except (OSError, ValueError, KeyError, TypeError) as e:
            respaldo = self.ruta + ".corrupto"
            try:
                os.replace(self.ruta, respaldo)
            except OSError:
                pass
            self._vaciar()
            self._sembrar_catalogo()
            self.mensaje_carga = (f"No se pudo leer el archivo de datos ({e}). "
                                  f"Se guardó una copia en '{os.path.basename(respaldo)}' y se partió de cero.")
            self.guardar()

    def guardar(self):
        datos = {"pacientes": [p.to_dict() for p in self.pacientes.values()],
                 "tratamientos": [t.to_dict() for t in self.tratamientos.values()],
                 "atenciones": [a.to_dict() for a in self.atenciones],
                 "siguiente_atencion": self._sig_atencion}
        tmp = self.ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.ruta)

    # -- Pacientes ------------------------------------------------------------
    def buscar_paciente(self, rut: str) -> Optional[Paciente]:
        try:
            return self.pacientes.get(Persona.normalizar_rut(rut))
        except ValueError:
            return None

    def registrar_paciente(self, rut: str, nombre: str, telefono: str = "", correo: str = "",
                           **otros) -> Paciente:
        paciente = Paciente(rut, nombre, telefono, correo, **otros)  # valida todo
        if paciente.rut in self.pacientes:
            raise ValueError("Ya existe un paciente con ese RUT.")
        self.pacientes[paciente.rut] = paciente
        self.guardar()
        try:
            self.bd.registrar_paciente(
                paciente.rut, paciente.nombre, paciente.telefono, paciente.correo,
                paciente.historial_medico, paciente.alergias, paciente.alergia_anestesia,
                paciente.dias_deuda_vencida
            )
        except Exception:
            pass
        return paciente

    def listar_pacientes(self) -> list[Paciente]:
        return sorted(self.pacientes.values(), key=lambda p: p.nombre.lower())

    def modificar_paciente(self, rut: str, campo: str, valor) -> Paciente:
        if campo not in CAMPOS_MODIFICABLES:
            raise ValueError("Ese dato no se puede modificar.")
        paciente = self.buscar_paciente(rut)
        if paciente is None:
            raise ValueError("No existe un paciente con ese RUT.")
        setattr(paciente, campo, valor)  # los setters validan
        self.guardar()
        try:
            self.bd.actualizar_paciente(paciente.rut, **{campo: valor})
        except Exception:
            pass
        return paciente

    def eliminar_paciente(self, rut: str):
        paciente = self.buscar_paciente(rut)
        if paciente is None:
            raise ValueError("No existe un paciente con ese RUT.")
        del self.pacientes[paciente.rut]
        self.guardar()
        try:
            self.bd.eliminar_paciente(paciente.rut)
        except Exception:
            pass

    # -- Tratamientos -----------------------------------------------------------
    def crear_tratamiento(self, tipo: str, descripcion: str, costo_base: float, **extra):
        clase = TIPOS_TRATAMIENTO[tipo]
        nuevo_id = max(self.tratamientos, default=0) + 1
        t = clase(nuevo_id, descripcion, costo_base, **extra)
        self.tratamientos[nuevo_id] = t
        self.guardar()
        return t

    def refrescar_dolar(self) -> bool:
        """Intenta consultar el dólar. Devuelve False (sin lanzar) si no se pudo."""
        try:
            self.indicador.refrescar()
            return True
        except IndicadorNoDisponible:
            return False

    # -- Atenciones -------------------------------------------------------------
    def registrar_atencion(self, paciente: Paciente, hora: str,
                           items: list[tuple[TratamientoDental, int]],
                           pabellon_disponible: bool = True) -> tuple[bool, str, AtencionMedica]:
        atencion = AtencionMedica(self._sig_atencion, paciente, self.odontologo, hora=hora)
        for tratamiento, cantidad in items:
            atencion.agregar_detalle(tratamiento, cantidad)
        ok, motivo = atencion.validar_condiciones(pabellon_disponible)
        if not ok:
            atencion.estado = "rechazada"
            return False, motivo, atencion
        if atencion.usa_dolar() and not self.refrescar_dolar():
            return False, ("no se pudo obtener el valor del dólar (revisa tu internet), "
                           "así que no se puede calcular el precio de la ortodoncia."), atencion
        ok, motivo = atencion.registrar(self.indicador, pabellon_disponible)
        if ok:
            self.atenciones.append(atencion)
            self._sig_atencion += 1
            self.guardar()
            try:
                detalles_bd = [{
                    "tratamiento": d.descripcion,
                    "cantidad": d.cantidad,
                    "precio_unitario": d.precio_unitario or 0.0,
                    "subtotal": d.calcular_subtotal()
                } for d in atencion.detalles]
                self.bd.registrar_ficha_medica(
                    paciente_rut=paciente.rut,
                    odontologo=f"{self.odontologo.nombre} ({self.odontologo.especialidad})",
                    fecha=atencion.fecha.isoformat(),
                    hora=atencion.hora,
                    motivo_consulta="Atención odontológica programada",
                    diagnostico="Procedimiento realizado según protocolo",
                    estado=atencion.estado,
                    monto_total=atencion.monto_total or 0.0,
                    valor_dolar_usado=atencion.valor_dolar_usado,
                    detalles=detalles_bd
                )
            except Exception:
                pass
        return ok, motivo, atencion


if __name__ == "__main__":
    import main
    try:
        main.menu()
    except (KeyboardInterrupt, EOFError):
        print("\nPrograma finalizado.")

