# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-08-27

Primera versión pública.

### Added

- Portal público y consola del participante, con el asistente de primer
  arranque: cuatro preguntas y el nodo queda configurado, con un producto de
  datos de ejemplo ya publicado.
- Un conector EDC, proveedor y consumidor a la vez, con negociación de
  contrato y descarga mediada.
- **Catálogo federado consolidado.** Se añade la dirección de otro nodo y su
  oferta pasa a formar parte de una vista única. Un grafo con nombre por nodo,
  escritura por delta, y degradación al catálogo local cuando Fuseki o un nodo
  remoto no responden.
- `GET /api/v1/catalog`: lo único que un nodo expone para que otro lo federe.
  Público, de sólo lectura y sólo con la oferta.
- `./install.sh`, idempotente, y toda la configuración en un único `.env`.
- Perfiles DCAT-AP y ODRL genéricos con sus formas SHACL, en `profiles/`:
  añadir el propio es copiar una carpeta.
- Imagen todo-en-uno para evaluación y docencia. **Sin identidad y sin TLS**,
  y lo dice al arrancar.

### Security

- La API de administración del conector **no se publica**. La consola la
  alcanza por un paso que reenvía el token de quien llama; no concede nada.
- Descargar exige una negociación cerrada, y los destinos de entrega están
  limitados.
- El punto SPARQL está cerrado por omisión; abierto, sólo permite leer.
- Registro de operaciones y denegaciones, firmado y encadenado, que vive en el
  propio nodo.

[Unreleased]: https://github.com/nekosphera/my-open-dataspace/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nekosphera/my-open-dataspace/releases/tag/v0.1.0
