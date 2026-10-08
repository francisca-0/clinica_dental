# Clínica Dental Sonrisas

Evaluación Sumativa N°1 - Programación Orientada a Objeto Seguro (TI3V21), sección 114-2A-F2.  
**Integrantes:** Francisca Garín y Fernando Miranda.

---

## 📌 Descripción del Proyecto
**Clínica Dental Sonrisas** es una aplicación de consola en Python diseñada bajo los principios de la **Programación Orientada a Objetos Segura**, robustez en el manejo de datos, persistencia en archivos JSON y tolerancia a fallos. Permite administrar pacientes, catálogos de tratamientos dentales, profesionales clínicos, y agendamiento integral de fichas de atención médica con validación estricta de reglas de negocio y consulta de divisas en tiempo real.

---

## 🚀 Cómo Ejecutarlo

### Requisitos previos
- Python 3.9 o superior instalado.
- Conexión a internet (para la consulta en tiempo real del dólar en tratamientos de ortodoncia).

### Pasos de instalación y ejecución
1. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Ejecutar el programa:**
   - En Windows (acceso directo): hacer doble clic en `ejecutar.bat`.
   - O por terminal:
     ```bash
     python main.py
     ```

> **Nota sobre persistencia:** Los datos se guardan automáticamente en `datos_clinica.json`. Si el archivo no existe, el sistema lo crea automáticamente con el catálogo base de tratamientos.

---

## 🛠️ Detalle de Cambios, Mejoras y Arquitectura Implementada

A continuación se detallan de forma exhaustiva todos los cambios y componentes arquitectónicos integrados en la solución:

### 1. Arquitectura Orientada a Objetos y Principios de POO Seguro
- **Clases Abstractas (`abc.ABC` y `@abstractmethod`):**
  - `Persona`: Clase base abstracta para cualquier individuo asociado a la clínica (`Paciente` y `Trabajador`). Define la propiedad abstracta `rol` y encapsula datos comunes (RUT, nombre, teléfono, correo).
  - `Trabajador`: Subclase abstracta de `Persona` que introduce el método abstracto `verificar_permisos(accion)`.
  - `TratamientoDental`: Clase base abstracta para los procedimientos de la clínica. Define los métodos polimórficos obligatorios `calcular_costo(indicador)` y `calcular_duracion()`.
- **Herencia y Especialización de Roles:**
  - `Paciente`: Hereda de `Persona` y agrega historial médico, registro de alergias generales, alergia a la anestesia y días de morosidad.
  - `Odontologo`: Hereda de `Trabajador`, incorporando especialidad, registro profesional y autorización para diagnosticar y realizar tratamientos.
  - `AsistenteDental`: Hereda de `Trabajador`, incorporando certificación asistencial y permisos para agendamiento y preparación de instrumental.
- **Polimorfismo en Tratamientos y Permisos:**
  - **Cálculo de costos especializado:**
    - `Limpieza`: Costo base fijo en pesos chilenos (CLP).
    - `Ortodoncia`: Costo base fijado en dólares (USD), el cual se convierte dinámicamente multiplicando por el valor del dólar observado del día mediante la API externa.
    - `Cirugia`: Aplica automáticamente un recargo del **50% (`x 1.5`)** sobre el costo base para cubrir insumos de pabellón y riesgo quirúrgico.
    - `Radiografia`: Tratamiento complementario con costo base directo en CLP.
  - **Duración estimada:** Cada tratamiento devuelve polimórficamente su tiempo en minutos (Limpieza: 30 min, Ortodoncia: 90 min, Cirugía: 120 min, Radiografía: 10 min).
  - **Verificación de permisos:** Cada tipo de trabajador (`Odontologo` y `AsistenteDental`) valida si cuenta con atribuciones para ejecutar una acción dada mediante `verificar_permisos()`.
- **Relaciones entre Clases:**
  - **Composición:** La clase `AtencionMedica` compone a instancias de `DetalleAtencion`. Las líneas de detalle existen en función de la atención médica creada.
  - **Asociación:** `AtencionMedica` se asocia directamente a un `Paciente` y a un `Odontologo` tratante. A su vez, `DetalleAtencion` se asocia al `TratamientoDental` seleccionado.
  - **Dependencia:** `TratamientoDental` (específicamente `Ortodoncia`) depende de `IndicadorExterno` para resolver el valor de conversión cambiaria.
- **Encapsulamiento y Protección de Datos:**
  - Uso de decoradores `@property` y `@setter` para todos los atributos sensibles (`_rut`, `_nombre`, `_telefono`, `_correo`, `_alergia_anestesia`, `_dias_deuda_vencida`, etc.).
  - Los setters validan tipos, impiden cadenas vacías, restringen números negativos o no finitos (`math.isfinite`), garantizando la integridad de cada objeto antes de almacenarlo.

---

### 2. Reglas de Negocio Implementadas y Validadas
- **Validación Matemática de RUT Chileno (Módulo 11):**
  - Implementación del algoritmo Módulo 11 en `Persona.normalizar_rut()`.
  - Acepta múltiples formatos de entrada (con o sin puntos, con o sin guion, minúsculas o mayúsculas).
  - Valida el dígito verificador numérico o `K`. Si es inválido, rechaza el ingreso con un mensaje explicativo sin botar el sistema.
  - Formatea automáticamente el RUT para despliegue visual formal (ej. `12.345.678-5`).
- **Política Financiera de Morosidad:**
  - La clínica define un límite estricto de deuda (`DIAS_DEUDA_LIMITE = 60`).
  - Si un paciente presenta más de 60 días de deuda vencida, el sistema rechaza automáticamente el agendamiento de la cita mediante el método `puede_ser_atendido()`.
- **Seguridad Clínica para Procedimientos Quirúrgicos:**
  - **Bloqueo por falta de registro de anestesia:** No se permite agendar una `Cirugia` si el estado de la alergia a la anestesia del paciente figura como *Sin registrar* (`None`). El sistema exige actualizar la ficha en la opción de modificar paciente antes de proceder.
  - **Alerta médica activa:** Si el paciente registra alergia confirmada a la anestesia (`True`) y se agenda una cirugía, el sistema emite una alerta destacada en consola solicitando la aplicación del protocolo de anestesia alternativa.
  - **Disponibilidad de Pabellón Especial:** Si la cirugía requiere pabellón especial (`requiere_pabellon_especial = True`), se valida interactivamente la disponibilidad del recinto antes de confirmar la atención.
- **Citas Multiprocedimiento con Duración y Subtotales:**
  - Una sola ficha de atención permite incorporar múltiples tratamientos y sesiones (ej. Limpieza + Radiografía en la misma cita).
  - Se calcula el subtotal por procedimiento, la duración total acumulada de la sesión y el monto total final a pagar.

---

### 3. Integración con API Externa (Mindicador.cl) y Tolerancia Offline
- **Clase `IndicadorExterno`:**
  - Consulta en tiempo real el valor del dólar observado desde `https://mindicador.cl/api/dolar`.
  - Incluye timeout de conexión para no congelar la interfaz si la red es lenta.
- **Manejo Seguro de Errores y Excepción Personalizada:**
  - Se creó la excepción `IndicadorNoDisponible`.
  - Si no hay conexión a internet, si la API está caída o si no está instalada la librería `requests`, el sistema **no se cae**: advierte al usuario de forma amigable e impide presupuestar la ortodoncia con datos desactualizados o inventados.

---

### 4. Persistencia Atómica y Recuperación ante Corrupción de Archivos
- **Escritura Atómica (`.tmp` -> `os.replace`):**
  - El guardado en JSON se realiza primero sobre un archivo temporal (`datos_clinica.json.tmp`) y luego se reemplaza atómicamente. Esto previene que el archivo de datos quede cortado o en blanco si se produce una interrupción repentina del suministro eléctrico o del proceso.
- **Mecanismo de Auto-Recuperación ante Datos Corruptos:**
  - Si el archivo `datos_clinica.json` sufre modificaciones manuales inválidas o corrupción de sintaxis, la clase `Clinica` lo detecta, crea un respaldo automático con extensión `.corrupto`, restaura el catálogo base en un nuevo archivo limpio y avisa al usuario en el menú principal sin interrumpir la ejecución.
- **Serialización Limpia:**
  - Métodos `to_dict()` y `from_dict()` en todas las entidades para una serialización JSON desacoplada y predecible.
- **Librería de Base de Datos Relacional (`base_datos.py` y archivo `.bd`):**
  - Implementación con SQLite nativo de Python para persistencia en archivo `clinica.bd`.
  - **Relación 1 a N:** Cada paciente posee su propio historial de fichas médicas vinculadas por clave foránea (`paciente_rut REFERENCES pacientes(rut) ON DELETE CASCADE`).
  - **Detalle de procedimientos:** Cada ficha médica desglosa múltiples tratamientos con cantidad, valor unitario y subtotal.
  - **Programación segura en BD:** Consultas parametrizadas (protección contra SQL Injection), gestión determinista de conexiones (`contextlib.contextmanager`), transacciones seguras y migración/sincronización automática de datos existentes.


---

### 5. Interfaz de Usuario de Consola Segura e Interactiva
- **Entrada de Datos Blindada:**
  - `leer_texto()`: Previene ingresos en blanco en campos obligatorios.
  - `leer_numero()`: Valida que la entrada sea numérica, soporte separadores decimales (punto o coma), valores enteros o flotantes, números finitos y mayores a un mínimo establecido.
  - `leer_si_no()`: Acepta respuestas afirmativas o negativas de forma tolerante (`s`, `si`, `sí`, `n`, `no`).
  - `leer_hora()`: Valida formato de hora `HH:MM` o asigna la hora actual automáticamente al presionar `Enter`.
  - `pedir_dato()`: Bucle interactivo que reintenta la lectura ante cualquier `ValueError` lanzado por los setters del modelo.
- **Facilidad de Uso (UX):**
  - Selección de pacientes por número de listado o por RUT.
  - Si no hay pacientes registrados al momento de agendar una cita, el sistema ofrece registrarlos de inmediato sin obligar a volver al menú principal.
  - Impresión de montos en moneda chilena formateada (ej. `$25.000`).
  - Soporte y reconfiguración explícita de codificación `UTF-8` en `sys.stdout` y `sys.stderr` para evitar fallos de codificación en consolas de Windows.
  - Protección global contra cierres forzados por excepciones imprevistas.

---

## 📋 Catálogo Base de Tratamientos y Reglas de Costo

| Tipo | Procedimiento Base | Duración | Regla de Cálculo de Costo |
|---|---|---|---|
| **Limpieza** | Limpieza dental general (ultrasónica) | 30 min | Costo base en CLP directo |
| **Ortodoncia** | Instalación de brackets metálicos | 90 min | Costo base en USD × Dólar del día (API) |
| **Cirugía** | Extracción de muela del juicio | 120 min | Costo base en CLP × 1,5 (recargo de pabellón) |
| **Radiografía** | Radiografía panorámica | 10 min | Costo base en CLP directo (complementario) |

---

## 📁 Estructura de Archivos del Repositorio

- [`main.py`](file:///C:/Users/hobif/OneDrive/Escritorio/clinica_dental/main.py): Interfaz de usuario interactiva por consola, menú principal de 11 opciones y lectura segura de entradas.
- [`clinica.py`](file:///C:/Users/hobif/OneDrive/Escritorio/clinica_dental/clinica.py): Capa de lógica de negocio, orquestación de entidades, operaciones CRUD y sincronización dual (JSON y Base de Datos .BD).
- [`base_datos.py`](file:///C:/Users/hobif/OneDrive/Escritorio/clinica_dental/base_datos.py): Librería de persistencia relacional en SQLite que administra pacientes y sus fichas médicas en el archivo `.bd`.
- [`clinica.bd`](file:///C:/Users/hobif/OneDrive/Escritorio/clinica_dental/clinica.bd): Base de datos relacional SQLite con tablas de pacientes, fichas médicas y líneas de tratamiento asociadas.
- [`modelos.py`](file:///C:/Users/hobif/OneDrive/Escritorio/clinica_dental/modelos.py): Definición de clases del modelo UML (Persona, Paciente, Trabajador, Odontólogo, Asistente, Tratamientos, Atenciones e Indicador de divisas).
- [`datos_clinica.json`](file:///C:/Users/hobif/OneDrive/Escritorio/clinica_dental/datos_clinica.json): Archivo de persistencia de datos (pacientes, catálogo y atenciones registradas).
- [`ejecutar.bat`](file:///C:/Users/hobif/OneDrive/Escritorio/clinica_dental/ejecutar.bat): Script de ejecución rápida para entornos Windows.
- [`requirements.txt`](file:///C:/Users/hobif/OneDrive/Escritorio/clinica_dental/requirements.txt): Declaración de librerías externas requeridas (`requests`).
- [`.gitignore`](file:///C:/Users/hobif/OneDrive/Escritorio/clinica_dental/.gitignore): Exclusión de archivos de caché de Python (`__pycache__/`, `*.pyc`) y configuraciones locales de IDE (`.vscode/`).
