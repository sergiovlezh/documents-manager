# Documents Manager

## Descripción

Este proyecto es un **clon básico de [Paperless NGX](https://docs.paperless-ngx.com/)**, enfocado exclusivamente en el **backend**, desarrollado con **Django y Django REST Framework (DRF)**.

El objetivo principal es demostrar un **dominio sólido de DRF**, buenas prácticas de diseño backend y capacidad para modelar lógica de negocio real, más allá de un CRUD básico.

---
## Alcance

La aplicación permite la **gestión de documentos digitales**, incluyendo:

- Carga y descarga de documentos.
- Organización de documentos mediante el uso de etiquetas, metadatos, descripciones y notas.
- Gestión de usuarios (documentos por usuario o compartidos).

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
