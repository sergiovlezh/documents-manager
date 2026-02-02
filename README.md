# Documents Manager

## Descripción

Este proyecto es un **clon básico de [Paperless NGX](https://docs.paperless-ngx.com/)**, enfocado exclusivamente en el **backend**, desarrollado con **Django y Django REST Framework (DRF)**.

El objetivo principal es modelar un sistema realista de gestión documental, aplicando buenas prácticas de arquitectura, diseño de dominio y lógica de negocio más allá de un CRUD básico.

---

## Alcance funcional

La aplicación permite la **gestión de documentos digitales**, incluyendo:

- Carga y descarga de documentos.
- Organización de documentos mediante:
    - Etiquetas
    - Metadatos
    - Descripciones
    - Notas
- Gestión de documentos por usuario.
- Base preparada para documentos compartidos entre usuarios.

---

## Requisitos

### Requisitos funcionales

- **Modelos**
    - Implementación de al menos cinco (5) modelos relacionados entre sí.
    - Inclusión de métodos personalizados dentro de los modelos que reflejen lógica de negocio relevante.
    - Uso de consultas avanzadas (querysets).

- **ViewSets**
    - Uso adecuado de ModelViewSet o equivalentes.
    - Implementación de acciones adicionales (@action) más allá del CRUD estándar.

- **Serializers**
    - Validaciones avanzadas a nivel de campo y de objeto.
    - Implementación de lógica personalizada para el guardado (create / update) o para el renderizado de los datos.

- **Pruebas**
    - Inclusión de pruebas unitarias que cubran:
        - Métodos personalizados de los modelos.
        - Validaciones y lógica implementada en los serializers.

- **Sustentación técnica**
    - Durante la sustentación, el candidato deberá explicar el diseño y las decisiones técnicas adoptadas.
    - Se solicitará realizar modificaciones en tiempo real (live coding) sobre el proyecto presentado, con el fin de evaluar la capacidad de análisis, adaptación y dominio del framework.

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

> Cada combinación (documento, etiqueta, usuario) es única.

La relación entre documento y etiqueta incluye al usuario que la asignó.

Esto permite:
  - Evitar duplicación de etiquetas.
  - Que distintos usuarios etiqueten el mismo documento de forma independiente.
  - La posibilidad de etiquetas definidas por el sistema.

---
