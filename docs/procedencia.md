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
| `app/ui/` | mydataspace | `ui/` sin `papers/` ni `urban-health-data/` |
| `app/ui/vendor/keycloak.js` | mydataspace | `ui/vendor/keycloak.js` — adaptador de Keycloak, Apache-2.0, sin modificar |

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

### C-002 — El adaptador de Keycloak volvió al árbol

La fase 1 borró `ui/vendor/` entera tomándola por lastre de terceros. Dentro
estaba `keycloak.js`, que **cuatro ficheros importan en tiempo de ejecución**:
las dos páginas de acceso, la consola y el panel de auditoría. Sin él, el
`import()` falla, se traga en un `catch` y la página dice «No se pudo
completar el login» sin decir por qué.

Vuelve tal cual, sin modificar. **Vendorizado y no desde un CDN**, que es la
regla de la sección 0b: un nodo tiene que funcionar con lo que hay en el
árbol, y la página de acceso no puede depender de que un tercero esté
disponible.

### C-003 — La consola hablaba con servicios que se quedaron en el origen

`app/ui/app.js` y `app/ui/console-audit.js` venían del panel del proyecto de
origen, que se apoyaba en un servicio de gobernanza externo. Al traerlos se
quitó el servicio pero se dejaron las llamadas, y quedaron pidiendo rutas que
este producto no sirve: `/api/governance/dataspaces/<id>/catalog` para cuatro
identificadores —tres de ellos del origen: `dataspace-a`, `dataspace-b`,
`myfiware`—, `/api/governance/audit/traces`, `/api/v1/edc/bridge/payloads` y
`papers_manifest.json`. Todo daba 404.

`console-audit.js` se retira entero: además de las rutas, empezaba por
`if (cfg.id !== "connector-1") return;` y buscaba los identificadores de un
`console.html` que la consola generada no tiene, así que no se ejecutaba nunca
en este producto. Lo que sí hacía falta —aprobar altas y ver participantes—
está en `app/ui/console-solicitudes.js`, escrito para la consola que este
producto genera.

En `app.js` se retiran la capa de gobernanza, el puente de EDC, el manifiesto
de papers y la auditoría documental que colgaba de las descargas —la del
análisis con Mistral, que esta versión no tiene—. Se conserva el camino entre
pares, que era el único que podía funcionar aquí.

La corrección va en el repositorio de destino y **no vuelve al origen**, como
manda la sección 0.

### C-004 — Prefijos e identificadores del origen en los metadatos

La consola escribía `myds:deliveryMode`, `myds:policyId` y `myds:contractId`
—el prefijo del proyecto de origen— y el perfil de metadatos de este producto
exige `ods:`. Se cambian los que escribe; al leer se aceptan los dos, porque
`myds:` lo llevan los activos publicados antes del cambio y dejar de verlos
sería perderlos del catálogo.

### C-005 — El aprovisionamiento dinámico de conectores

El `onboarding_api.py` de origen servía a un despliegue con tres conectores y
daba de alta participantes creando uno por persona: `make_connector_id(correo)`
más su cliente de Keycloak, su cartera, su registro, su participante y su
consola. La sección 4 de la especificación manda eliminarlo —«todo lo que
instancie más de uno»— y la poda se llevó las páginas y los grupos pero no esta
parte, que es la que lo instanciaba.

Se retira entera, junto con la reconciliación que existía para sostenerla
(`create_connector_for_owner`, `rollback_connector_artifacts`,
`connector_is_complete`, `ensure_connector_artifacts_for_existing_user`). Lo
que queda en su lugar migra a quien hubiera quedado colgando de uno de aquellos
conectores al conector del nodo, sin tocar su cuenta.

`app/ui/home-audit.js` consultaba `/api/connector-1/…`, `-2` y `-3`, del mismo
despliegue de origen; ahora consulta el paso al conector de este nodo.

### C-005 bis — El aprovisionamiento por participante, rehecho

C-005 retiró el aprovisionamiento dinámico de conectores del proyecto de origen
porque la especificación pedía un conector por nodo. La enmienda 16 pide lo
contrario, así que la idea vuelve —un conector por participante— pero **no el
código**: aquél creaba un identificador, un cliente y una cartera sin que nada
detrás separase la oferta, de modo que todos los participantes compartían la
misma bolsa de activos y a cada uno le salía todo como propio.

Lo que hay ahora se ha escrito para este producto: el claim firmado, la columna
de dueño en las tres tablas del conector y el filtro al leer.
