# Procedencia del código

Cada bloque de código traído de otro repositorio queda anotado aquí con su
origen y el commit exacto del que sale. Es lo que permite volver a traer
mejoras de aguas arriba más adelante sin adivinar de dónde salió cada cosa.

Los repositorios de origen son **de sólo lectura** para este proyecto. Si algo
de origen resulta incompleto o erróneo se corrige **aquí** y se anota en la
sección «Correcciones respecto al origen»; nunca aguas arriba.

## Repositorios de origen

| Origen | Commit | Fecha |
|---|---|---|
| `nekosphera/mydataspace` | `395092b4e9a2a27ff270ce079d2a7e6e761bda02` | 2026-08-24 |
| `nekosphera/catalejo` | `dd6c56ad3308d7850a06fb9bf140435a7eedeb73` | 2026-08-24 |

## Bloques incorporados

### `app/` — portal, consola y API

| Destino | Origen | Fichero de origen |
|---|---|---|
| `app/onboarding_api.py` | mydataspace | `tools/onboarding_api.py` |
| `app/requirements.txt` | mydataspace | `tools/onboarding_api.requirements.txt` |
| `app/tools/render_ui_runtime_config.py` | mydataspace | `tools/render_ui_runtime_config.py` |
| `app/tools/setup_keycloak_rbac.sh` | mydataspace | `tools/setup_keycloak_rbac.sh` |
| `app/tools/smoke_secure_download.py` | mydataspace | `tools/smoke_secure_download.py` |
| `app/ui/` | mydataspace | `ui/` sin `vendor/`, `papers/` ni `urban-health-data/` |

### `connector/` — conector EDC propio

| Destino | Origen | Fichero de origen |
|---|---|---|
| `connector/src/` | mydataspace | `src/` (Java, `main` y `test`) |
| `connector/pom.xml` | mydataspace | `pom.xml` |
| `connector/Dockerfile` | mydataspace | `Dockerfile` (el de la raíz) |
| `connector/config/edc-config.properties` | mydataspace | `config/edc-config.properties` |

### `federation/` — catálogo federado

Se toma del repositorio público `catalejo`, **no** de la copia vendorizada que
`mydataspace` mantenía en `catalogue/`: el repositorio original está más
completo (trae el federador, los vocabularios y la observabilidad) y es el que
recibe las mejoras.

| Destino | Origen | Fichero de origen |
|---|---|---|
| `federation/src/catalejo/` | catalejo | `src/catalejo/` |
| `federation/federator/` | catalejo | `federator/` |
| `federation/smoke/`, `federation/smoke.sh` | catalejo | `smoke/`, `smoke.sh` |
| `federation/requirements.txt` | catalejo | `requirements.txt` |

### `profiles/` — perfiles de metadatos y política

| Destino | Origen | Fichero de origen |
|---|---|---|
| `profiles/dcat-ap/1.0.0/` | catalejo | `vocabularies/dcat-ap/1.0.0/` |
| `profiles/odrl/1.0.0/` | catalejo | `vocabularies/odrl/1.0.0/` |
| `profiles/ns.jsonld` | catalejo | `vocabularies/ns.jsonld` |

### `db/`

| Destino | Origen | Fichero de origen |
|---|---|---|
| `db/01-create-databases.sql` | mydataspace | `config/postgres-init/01-create-databases.sql` |

### `tests/`

| Destino | Origen | Fichero de origen |
|---|---|---|
| `tests/test_catalog_federation_delta.py` | mydataspace | `tests/test_catalog_federation_delta.py` |
| `tests/test_catalog_metadata_shapes.py` | mydataspace | `tests/test_catalog_metadata_shapes.py` |
| `tests/e2e/` | mydataspace | `tests/e2e/` |

## Correcciones respecto al origen

Se anotan aquí a medida que aparecen.

### C-001 — El Dockerfile del conector

`mydataspace` tiene dos Dockerfile de Java y no dice cuál construye el conector
propio. `eclipse-runtime/Dockerfile` clona el conector oficial de Eclipse desde
`main` en tiempo de construcción; el de la raíz es el que compila
`org.eclipse.dataspace.DataSpaceApplication`, que es el conector propio con su
superficie `management/v3` y la descarga mediada.

Se trae el de la raíz. El del runtime oficial queda fuera: además de no ser el
conector que la especificación manda reutilizar, construye desde `main` sin
fijar versión, lo que hace la imagen irreproducible.

Se le han cambiado dos etiquetas OCI que apuntaban al repositorio de origen
(`image.source` y `image.title`).
