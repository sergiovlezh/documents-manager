# Documents Manager

## Descripción

Este proyecto es un **clon básico de [Paperless NGX](https://docs.paperless-ngx.com/)**, enfocado exclusivamente en el **backend**, desarrollado con **Django y Django REST Framework (DRF)**.

El objetivo principal es modelar un sistema realista de gestión documental, aplicando buenas prácticas de arquitectura, diseño de dominio y lógica de negocio más allá de un CRUD básico.

---

## Alcance funcional

La aplicación permite la **gestión de documentos digitales**, incluyendo:

- Carga de documentos con uno o múltiples archivos.
- Descarga de archivos asociados a documentos.
- Organización mediante:
  - Etiquetas por usuario.
  - Metadatos clave–valor.
  - Descripciones
  - Notas
- Aislamiento estricto por usuario (ownership).
- Operaciones avanzadas como **fusión de documentos**.

---

## Stack tecnológico

- Python 3.x
- Django
- Django REST Framework

---

## Requisitos

### Requisitos funcionales

- **Modelos**
    - Implementación de **más de cinco (5) modelos relacionados**:
        - Document
        - DocumentFile
        - DocumentMetadata
        - DocumentNote
        - Tag
        - DocumentTag

    - Inclusión de métodos personalizados dentro de los modelos que reflejen lógica de negocio relevante:
        - Creación atómica de documentos y archivos.
        - Reglas de integridad (ej. un documento no puede quedar sin archivos).
        - Gestión de etiquetas, notas y metadatos.
        - Fusión de documentos.

    - Uso de QuerySets
        - Filtrado por usuario.
        - Prefetch optimizado de archivos y etiquetas.
        - Anotaciones (conteo de archivos).
        - Búsqueda por título, descripción y etiquetas.

- **ViewSets**
    - Uso adecuado de `ModelViewSet`.


    - Acciones personalizadas (`@action`) más allá del CRUD:
        - Carga de múltiples archivos.
        - Gestión de archivos por documento.
        - Gestión de notas y metadatos.
        - Fusión de documentos.

- **Serializers**
    - Validaciones avanzadas a nivel de campo y objeto.
        - Serializers específicos para lectura y escritura.

    - Implementación de lógica personalizada de creación y actualización.
        - Delegación de reglas de negocio a los modelos.

- **Pruebas**
    - El proyecto incluye **pruebas unitarias y de integración** que cubren:
        - Métodos personalizados de los modelos.
        - QuerySets personalizados.
        - Validaciones y flujos de negocio implementados en serializers.
        - Endpoints de la API.

---

### Requisitos no funcionales

- Código claro, legible, modular y mantenible.
- Arquitectura clara y escalable.
- Seguridad básica en APIs (autenticación y autorización).
- Base de datos bien modelada y normalizada.
- APIs documentadas y manejo adecuado de errores.

---


## Dominio del negocio

### Documento (`Document`)

Representa la entidad lógica principal del sistema y es la unidad que el usuario visualiza y gestiona.

Un documento:
- Pertenece a un usuario.
- Contiene un título y una descripción.
- Se relaciona con:
    - uno o más archivos físicos
    - metadatos
    - notas
    - etiquetas

El título del documento es el identificador amigable con el usuario y puede derivarse del primer archivo cargado.

### Archivo de documento (`DocumentFile`)

Representa un archivo físico cargado en el sistema.

- Un documento puede tener múltiples archivos (páginas, versiones, formatos).
- El nombre original del archivo se obtiene directamente del almacenamiento (FileField), sin duplicar información en el modelo.

Esta separación permite tratar los documentos como conceptos de negocio independientes de los detalles de almacenamiento.

### Metadatos (`DocumentMetadata`)

Representa los campos adicionales que puede tener un documento.

- Se modelan como pares clave / valor asociados a un documento.
- Un documento puede tener múltiples metadatos.
- Cada clave es única por documento.

Este enfoque permite un esquema flexible y extensible, facilitando futuros filtros y búsquedas.

### Notas (`DocumentNote`)

Son textos libres creado por los usuarios.

- Asociadas a un documento.
- Ordenadas por fecha de creación.

### Etiquetas (`Tag`)

Las etiquetas son entidades globales, únicas por nombre que sirven para gestionar los documentos más fácilmente.

### Relación Documento–Etiqueta (`DocumentTag`)

Modelo explícito de relación muchos-a-muchos que incluye:

- Documento
- Etiqueta
- Usuario propietario de la etiqueta
- Color de la etiqueta

> Cada combinación (documento, etiqueta, usuario) es única.

La relación entre documento y etiqueta incluye al usuario que la asignó.

Esto permite:
  - Evitar duplicación de etiquetas.
  - Que distintos usuarios etiqueten el mismo documento de forma independiente.
  - La posibilidad de etiquetas definidas por el sistema.

---
