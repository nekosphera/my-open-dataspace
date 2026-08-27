# Estado de la entrega

Una línea por fase. Se actualiza al terminar cada una.

| Fase | Estado | Fecha | Entregable |
|---|---|---|---|
| 1 — Repositorio limpio | ✅ hecho | 2026-08-27 | Árbol nuevo sin historial, licencia, ficheros de comunidad y estructura de carpetas |
| 2 — Poda | ✅ hecho | 2026-08-27 | Seis contenedores, sin referencias a lo eliminado |
| 3 — Un solo conector | ✅ hecho | 2026-08-27 | Consola única, ciclo completo |
| 3b — Catálogo consolidado | ✅ hecho | 2026-08-27 | Dos nodos ven su oferta mutua |
| 4 — Configuración | ✅ hecho | 2026-08-27 | Todo a `.env`, cero valores codificados |
| 5 — Asistente e instalador | ✅ hecho | 2026-08-27 | Criterio de los diez minutos |
| 6 — Imágenes y publicación | ✅ hecho | 2026-08-27 | Imágenes descargables, E2E en verde |
| 7 — Documentación | ✅ hecho | 2026-08-27 | README, manuales de instalación y personalización |
| 8 — Revisión previa | ✅ publicado | 2026-08-27 | Repositorio listo para público |

---

## Fase 1 — Repositorio limpio

**Hecha el 2026-08-27.**

Árbol nuevo en `repos/my-open-dataspace` con la estructura de la sección 10 y
el código de origen vendorizado dentro, sin submódulos ni referencias
externas. Qué se ha traído y de dónde, en [procedencia.md](procedencia.md).

Ficheros de proyecto: `LICENSE` (Apache-2.0), `NOTICE`, `SECURITY.md`,
`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md`, `.gitignore` y
`.gitattributes` — este último fija LF en todo el árbol, porque un
`install.sh` con CRLF no arranca dentro del contenedor.

---

## Fase 2 — Poda

**Hecha el 2026-08-27, con una comprobación pendiente que se dice abajo.**

### Lo que se ha quitado

**Capa de IA.** Mistral entero: el análisis documental, las dos rutas
`/analyze`, las funciones que componían sugerencias de metadatos a partir de
un modelo, y las tres columnas de la tabla de auditoría de la consola que
mostraban su veredicto.

**SIMPL.** El puente EDC y sus dos rutas, el plan de arranque IAA, el entorno
`lab`/`live`, el reenvío del registro de auditoría a un servicio de gobernanza
externo, y las etiquetas que atribuían cada perfil a un bloque de SIMPL.

**Identidad avanzada.** Las credenciales verificables con sus cuatro rutas y
la resolución `did:web` con la publicación del documento DID. En las páginas
de acceso, las tarjetas de Cl@ve/eIDAS y EU Login con sus manejadores: estaban
ocultas por omisión, y la especificación dice que no entra nada de eso «ni
siquiera desactivado».

**Infraestructura sobrante.** Vault, MinIO, Airflow y la pila de
observabilidad. Los activos pasan del almacén de objetos a un volumen de
disco, con la clave resuelta contra la carpeta para que un `..` no lea el
contenedor entero.

**Verticales.** Los cuadros de mando urbanos, el caso de Málaga, el panel de
riesgo federado, el manifiesto de artículos y los diagramas del ecosistema
propio, que nombraban FIWARE, Orion, NGSI-LD y la marca de origen.

**Rastros del despliegue actual.** Los cinco dominios, la IP pública de un
VPS que estaba en el humo de descarga, tres direcciones de correo reales en la
matriz de cuentas del RBAC, el servidor SMTP de OVH, y la analítica de Google,
que mandaba a un tercero sin que nadie lo hubiera pedido.

### Lo que se conserva, porque la especificación lo conserva

El ciclo completo de alta, publicación, catálogo, negociación y descarga
mediada. Los dos controles que dan valor: exigir negociación cerrada para
descargar y limitar los destinos de entrega. El registro de operaciones y
denegaciones — sigue firmado y encadenado, pero lo firma la identidad del
propio nodo y no se reenvía a nadie ([D-005](decisiones.md)). Fuseki con TDB2
y el federador por delta con su purga de grafos huérfanos y su validador
DCAT-AP.

### La composición

De dieciocho servicios a seis: `caddy`, `app`, `connector`, `postgres`,
`keycloak` y `fuseki`. Un solo puerto expuesto. La base de datos, Keycloak,
Fuseki y la superficie de gestión del conector dejan de asomar a la máquina
anfitriona. El realm se importa en el arranque con sus roles, sus grupos, el
cliente de la consola y la cuenta de servicio del conector: cero pasos
manuales.

El federador pasa a vivir dentro de `app` ([D-006](decisiones.md)).

### La prueba

`tests/test_no_hidden_dependencies.py` es la búsqueda de términos prohibidos
que la fase pedía dejar como prueba automática. Comprueba tres cosas: que no
queda ni un dominio, correo, IP o ruta de servidor de los despliegues de
origen; que nada de lo podado ha vuelto; y que `.env.example` no lleva ningún
secreto con valor.

Busca los términos **como palabras y no como subcadenas**, porque «minio» vive
dentro de «dominio» y «ngsi» dentro de «alongside»: una prueba que falla por
eso deja de decir nada y se acaba desactivando.

Estado del conjunto: **53 pasan, 8 se saltan.** Las 8 son las del federador
por delta, que necesitan `jq` y no lo hay en esta máquina; corren dentro de la
imagen de `app`, que sí lo instala.

### El arranque, comprobado

`docker compose up -d` levanta los seis contenedores y todo responde:

| Comprobación | Resultado |
|---|---|
| Los seis contenedores en marcha | ✅ `app`, `caddy`, `connector`, `postgres`, `keycloak`, `fuseki` |
| Portal por Caddy (`/`, `/styles.css`, `/app.js`, `/login.html`) | ✅ 200 |
| API por Caddy (`/api/onboarding/health`) | ✅ 200 |
| Keycloak por Caddy (`/auth/realms/dataspace/...`) | ✅ 200 |
| Recorrido de rutas (`/../../etc/passwd`) | ✅ 404 |
| Fuseki por la red interna | ✅ 200 |
| Superficie del conector por la red interna | ✅ 401 — está arriba y exige identidad |
| Superficie del conector desde fuera | ✅ no se publica |
| Realm importado: grupos | ✅ `connector-users`, `dataspace-admins`, `dataspace-negotiators`, `dataspace-users` |
| Realm importado: roles | ✅ `connector-user`, `dataspace-admin`, `dataspace-negotiator`, `dataspace-user` |
| Cuenta de servicio del conector | ✅ con sus tres roles, sin un solo paso manual |

**Tres fallos reales que sólo aparecieron al levantarlo:**

1. **Caddy no arrancaba.** `{$ODS_DOMAIN::80}` sólo cae al valor por omisión
   cuando la variable **no está definida**, y la composición la define siempre.
   Con `ODS_DOMAIN` vacía la clave del bloque quedaba vacía y Caddy lo leía
   como un segundo bloque global. La dirección se resuelve ahora en la
   composición, con `${ODS_DOMAIN:-:80}`, que sí cae al defecto cuando está
   vacía.

2. **Keycloak entraba en bucle de reinicio:** la base `keycloak` no existía.
   `db/01-create-databases.sql` venía del origen y creaba seis bases de tres
   conectores y un monedero, ninguna de ellas la que Keycloak necesita.

3. **El portal contestaba 404.** En el despliegue de origen la interfaz la
   servía un nginx aparte, así que la API contestaba 404 a todo lo que no
   empezara por `/api`. Aquí no hay ese nginx —son seis contenedores— y `app`
   es quien tiene que servirla. Se ha añadido, con la ruta comprobada contra
   la carpeta resuelta.

**Y una dependencia oculta que el arranque delató:** el servicio intentaba
registrarse en cada arranque contra `GOVERNANCE_API_BASE_URL`, un servicio de
gobernanza externo, y lo anunciaba con un aviso. Ha salido entera: las tres
funciones y el fichero `governance.env` que las alimentaba. Los tres valores
que de ahí se leían —dirección pública, nombre de la organización y URL de
identidad— salen ahora de `ODS_PUBLIC_URL`, `ODS_ORG_NAME` y `ODS_AUTH_URL`.

---

## Fase 3 — Un solo conector

**Hecha el 2026-08-27.**

El identificador del conector sale de `ODS_CONNECTOR_ID`. Las tablas de tres
conectores predefinidos —directorio, perfiles e identificadores estáticos—
colapsan a una entrada. La tabla de redirecciones heredadas, que nombraba tres
cuentas del despliegue de origen, desaparece.

Las páginas `connector-2*` y `connector-3*` se van; `connector-1*` pasa a ser
`console.html` y `console-en.html`. **La consola vive en una sola dirección**
porque el identificador del conector es configurable y por tanto no puede
estar en la URL. Las pestañas son las que la especificación pide: Operación
—con sus dos vistas, proveedor y consumo—, Auditoría, y Usuarios y solicitudes.

`setup_keycloak_rbac.sh` crea un grupo `connector-users` y una cuenta de
servicio, no tres de cada.

---

## Fase 3b — Catálogo consolidado

**Hecha el 2026-08-27, salvo la prueba con dos nodos de verdad.**

### La lista de nodos conocidos

El nodo propio va siempre primero y **no se guarda**: se compone en cada
lectura, para que no envejezca cuando cambia `ODS_CONNECTOR_ID` o la dirección
pública. Los remotos se dan de alta desde la consola con `POST /api/v1/nodes`,
se retiran con `DELETE /api/v1/nodes/<id>` y se sincronizan a demanda con
`POST /api/v1/nodes/sync`, que es el botón de «actualizar ahora».

Listar es público —es quién forma este espacio de datos—; añadir, quitar y
forzar una sincronización exigen identidad de administrador.

### El federador

Vive dentro de `app`, en su propio hilo, y sincroniza cada
`ODS_FEDERATION_INTERVAL` segundos. Se le pasa la lista por
`FEDERATION_NODES_FILE`; sin ella sigue aceptando la configuración fija de
catalejo, que es como se ejecuta suelto. **Un grafo con nombre por nodo**, de
modo que retirar uno no toca el resto del almacén.

### Comprobado, arrancado de verdad

| Comprobación | Resultado |
|---|---|
| El sembrado publica el ejemplo | ✅ 2 activos, 2 políticas, 2 contratos |
| Y es idempotente | ✅ la segunda vez: `ya_existian=6`, no duplica |
| El federador recoge la oferta | ✅ `contributing=1`, 91 tripletas en `urn:ods:catalog/connector` |
| Descarga sin negociación cerrada | ✅ 403 `completed negotiation required for this asset` |
| Alta de nodo sin identidad | ✅ 403 |
| Un nodo que no contesta | ✅ se marca `unreachable` y **no vacía la vista de los demás**: el grafo del nodo propio sigue con sus 91 tripletas |
| Retirar un nodo | ✅ se lleva su grafo y sólo el suyo |

### Cuatro fallos encadenados que sólo se ven arrancando

1. **El conector contestaba 401 a todo.** Verificaba la firma de los tokens
   contra `identity-hub:8080`, un servicio del despliegue de origen que aquí no
   existe, y el fallo se registraba como `JWT validation failed: null`. Ahora la
   composición le pasa el JWKS y, si le falta, **lo dice en el arranque** en vez
   de callar.

2. **Keycloak emitía tokens con el emisor equivocado.** `KC_HOSTNAME` es una URL
   completa y su ruta manda sobre `--http-relative-path`: sin `/auth` al final,
   Keycloak emitía `iss=<pública>/realms/…` mientras servía en
   `<pública>/auth/realms/…`, y el conector los rechazaba todos.

3. **Los ficheros de ejemplo no se versionaban.** La regla `data/` de
   `.gitignore` no estaba anclada, así que casaba con `seed/data/`. Quien
   clonara el repositorio recibía un manifiesto apuntando a ficheros que no
   están y dos productos publicados cuya descarga da 404 — peor que no publicar
   ninguno, porque parece que funciona. Anclada a `/data/`, y con
   `tests/test_seed_is_shippable.py` para que no vuelva.

4. **Un guion con CRLF no arranca dentro del contenedor.** El federador devolvía
   `ok=False` sin decir por qué: bash lo rechazaba en su primera línea con
   `pipefail: invalid option name`. `.gitattributes` lo garantiza para lo que
   entra al repositorio pero no reescribe lo que ya estaba en disco. Cuarenta
   ficheros normalizados y `tests/test_line_endings.py` para que no vuelva —
   que ya ha cazado dos reincidencias mías.

### La prueba con dos nodos, hecha

Se levantó un segundo nodo completo en la misma máquina —otro proyecto de
Docker, otros puertos, otro conector, sus propios volúmenes— y se le presentó
al primero desde la lista de nodos conocidos. El procedimiento está en
[dos-nodos.md](dos-nodos.md).

| Criterio de aceptación | Resultado |
|---|---|
| **8** — la oferta de dos nodos en una sola pantalla | ✅ `contributing=2`, 4 ofertas de 2 nodos en una consulta |
| **9** — apagar el segundo y que la vista aguante | ✅ sigue mostrando las 4 ofertas; el vecino queda `unreachable` **conservando la fecha de su última sincronización correcta**, no la de ahora |
| Recuperación | ✅ al volver a arrancarlo, `unavailable=0` en la siguiente sincronización |
| El portal durante la caída | ✅ `/`, `/api/onboarding/health`, `/api/v1/nodes` y `/api/v1/catalog`, todos 200 |

**Cómo se federa entre nodos, y por qué hubo que cambiarlo.** El federador de
origen leía la API de gestión del conector con un token de Keycloak. Eso vale
dentro de un nodo y es **imposible entre organizaciones**: el nodo A no tiene
credenciales en el Keycloak del nodo B, y publicar esa superficie es justo lo
que la sección 3 no hace.

Cada nodo expone ahora `GET /api/v1/catalog`: público, de sólo lectura, y sólo
con la oferta. Ni usuarios, ni solicitudes, ni el registro de operaciones. Es
lo que hace que dar de alta un nodo se reduzca a escribir su dirección. El
nodo propio se sigue leyendo por la API de gestión con la cuenta de servicio;
un nodo remoto, por su catálogo público.

**Un fallo que sólo aparece con el segundo nodo apagado.** El federador
contaba el nodo caído como `contributing=0` pero `unavailable=0`, así que la
consola lo enseñaba como «disponible, sin ofertas» — que se lee como un nodo
que ha retirado su catálogo, no como uno que no contesta. Son cosas distintas
y el operador tiene que poder distinguirlas.

### La consola

La pestaña **Nodos conocidos** está: alta, baja, «actualizar ahora», y la
tabla con el estado y la fecha de la última sincronización correcta de cada
nodo. El cambio de pestañas dejó de estar cableado a dos: se lee del DOM por
`aria-controls`, que es lo que los botones ya tenían que declarar.

**La consola se genera en cada arranque**, no se sirve estática: lleva dentro
la lista de nodos, el identificador del conector y el perfil de quien la usa,
y los tres cambian sin que nadie toque un fichero. Las `console*.html` que
viajan en el repositorio son lo que se ve antes del primer arranque.

### El paso hacia el conector

La consola necesita publicar activos y abrir negociaciones, y eso vive en la
API de gestión del conector, que **no se publica**: Caddy no tiene ninguna
ruta hacia él y el servicio no expone puertos.

`/api/connector` la alcanza por la red interna y **reenvía el token de quien
llama tal cual**. No concede nada: un token de otro realm y uno inventado
reciben 401 del propio conector. Sólo deja pasar los cuatro recursos que la
consola usa. `tests/test_connector_surface_is_not_published.py` vigila las
cuatro cosas que lo convertirían en un agujero: que Caddy no enrute al
conector, que el conector no publique puertos, que la lista blanca no crezca y
que el paso no adquiera credenciales propias.

También se corrigió un resto del despliegue de origen que nadie habría notado:
la consola decidía si filtrar recursos por dueño con `/^connector-[123]$/`,
los tres identificadores de aquel despliegue. En cualquier otra instalación esa
expresión no casa con nada.

**99 pruebas en verde**, 8 saltadas por falta de `jq` en esta máquina.

### Lo que falta

Nada de las fases 3 y 3b. Lo siguiente es la fase 4 —repasar que no quede
ningún valor de despliegue codificado— y la 5, el asistente de primer arranque
y el instalador, que es donde se mide el criterio de los diez minutos.

---

## Fase 4 — Configuración

**Hecha el 2026-08-27.**

El repaso encontró **tres opciones declaradas en `.env.example` que no leía
nadie**. Configurarlas no hacía nada, que es peor que no ofrecerlas: quien las
ponía creía haber cambiado algo.

- **`ODS_TLS`.** Poner `off` con un dominio seguía pidiendo certificado. La
  dirección la calcula ahora el arranque de Caddy, que sí sabe ramificar entre
  los tres casos —sin dominio, dominio con TLS, dominio sin TLS—. La
  composición no puede: no tiene condicionales.
- **`ODS_SPARQL_PUBLIC`.** El punto de consulta no existía ni abierto ni
  cerrado. Ahora está **cerrado por omisión y devuelve 404, no 403**: un punto
  que no está abierto no tiene por qué anunciar que existe. Abierto, sólo deja
  leer.
- **`ODS_ADMIN_PASSWORD`**, que sigue sin consumidor a propósito: la usa el
  instalador, y está anotada como pendiente en la prueba de deriva.

**Un fallo propio en la comprobación de «esto es sólo una lectura».** Quitaba
comentarios con `#[^
]*` y se comía la almohadilla del fragmento de un IRI,
de modo que cualquier consulta con `PREFIX dcat: <http://…/dcat#>` —es decir,
casi cualquiera— se rechazaba como si fuera una escritura. Ahora se recorre la
consulta saltando IRIs y literales. La prueba lleva los dos lados: once
lecturas que tienen que pasar, incluida una con `"insert data"` dentro de un
literal, y doce escrituras que no, incluidas las escondidas detrás de un
`PREFIX` y de un comentario que dice `select`.

**El correo del administrador llega a sus cuatro sitios**: el usuario
administrador del realm, el registro ACME del certificado, el contacto del
participante en el catálogo y el destinatario de los avisos.

**Prueba de deriva.** Ninguna variable que el código lea puede quedar sin
declarar, y ninguna declarada puede quedarse sin consumidor. La lista de
pendientes se vacía sola: hay una prueba que falla cuando una pendiente ya
tiene quien la lea, para que la lista de excepciones no deje de decir nada.

---

## Fase 5 — Asistente e instalador

**Hecha el 2026-08-27.**

### El asistente

Un nodo sin configurar manda **cualquier** ruta a `/setup` —salvo la hoja de
estilo que el propio asistente necesita, sin la cual la página sale en
blanco—. Cuatro pasos: organización, administrador, idioma y marca,
confirmación. Al terminar crea el administrador en Keycloak con sus cuatro
grupos, guarda los ajustes, regenera la consola y la marca, publica el
ejemplo y marca el nodo como configurado. A partir de ahí **`/setup` devuelve
404**.

El marcador y los ajustes viven en el volumen de estado, no en el árbol: si
vivieran en el árbol, cada actualización de la imagen devolvería el nodo a la
pantalla de configuración.

### Dos fallos que sólo se ven usándolo

1. **Quien llegara al asistente antes de que Keycloak terminara de subir
   recibía un `Connection refused` en crudo.** No dice qué ha pasado ni que
   basta con esperar. El asistente comprueba ahora si la identidad contesta:
   lo avisa antes de que pulses Finalizar, y si pulsas igual el error dice qué
   hacer. La comprobación va **antes** de escribir nada, porque fallar a mitad
   dejaría ajustes guardados sin administrador que los use.

2. **Los ajustes del asistente llegaban a la interfaz pero no al backend.** La
   marca se veía bien —`runtime-config.js` se regenera con ella— mientras el
   catálogo seguía publicando el nombre y el correo del `.env`. Es decir: uno
   de los cuatro sitios a los que el correo del administrador tiene que llegar
   se quedaba con el valor de ejemplo, y nada lo decía.

### El instalador

`./install.sh` pregunta cuatro cosas, deriva el identificador del nombre,
genera las contraseñas de servicio que falten, escribe `.env` con permisos
600, levanta la composición, espera a que el nodo **y la identidad** contesten,
y dice qué hacer a continuación.

**Es idempotente y se comprueba.** Un `.env` que ya existe no se sobrescribe
—lleva dentro las contraseñas del nodo, y regenerarlas deja la base de datos
inaccesible—: se reutiliza y sólo se le añaden las claves que falten. La
segunda ejecución detecta que el nodo ya pasó por el asistente y lo dice en
vez de mandarte a una pantalla que devuelve 404.

Sin terminal interactivo no pregunta: toma los valores por omisión. Un guion
que interroga a un stdin cerrado se cuelga en CI.

### El criterio de los diez minutos

Medido, de cero a producto de datos publicado:

| Paso | Tiempo |
|---|---|
| `./install.sh` con las imágenes ya construidas | 52 s |
| Completar el asistente | 1 s |
| **Total** | **53 s** |

Con las imágenes ya construidas. Una máquina que empiece de verdad de cero
tiene que construir el conector Java, que son varios minutos; eso desaparece
en la fase 6, cuando `docker compose pull` sustituya al `build`. **Ese es el
recorrido que hay que volver a cronometrar cuando las imágenes estén
publicadas**, porque es el que describe el README.

**150 pruebas en verde**, 8 saltadas por falta de `jq` en esta máquina.

---

## Fase 6 — Imágenes y publicación

**El flujo está hecho y probado. Publicar es una acción de Francisco, no mía.**

### Los espacios de nombres, comprobados

La sección 15 pedía confirmarlo antes de esta fase:

| | Estado |
|---|---|
| Docker Hub `myopendataspace` | ✅ **libre** — 404 como usuario y como organización |
| GitHub `myopendataspace` | libre, pero no hace falta: se usa `nekosphera` |
| `github.com/nekosphera/my-open-dataspace` | ⚠️ **ya existe** — creado el 2026-08-27 a las 13:01 UTC, **vacío**, y **ya público**, con la descripción de la sección 10b |

Que el repositorio esté vacío es bueno: no choca con «un único commit
inicial». Que **ya sea público** cambia el riesgo y conviene decirlo: no hay
un paso intermedio en el que subir, mirar y corregir. El primer `git push`
publica. La lista de la sección 14 tiene que estar cerrada **antes**, no
después.

### La puerta

`.github/workflows/tests.yml` es la puerta, y `release.yml` la reutiliza en
vez de copiarla: dos puertas distintas dejan de ser una puerta.

`tests/e2e/golden_path.py` comprueba el criterio de aceptación contra un nodo
levantado de verdad, no una lista de funciones. **Trece comprobaciones, en
verde desde cero:**

| | |
|---|---|
| Un nodo sin configurar manda al asistente | ✅ |
| El asistente se completa | ✅ |
| Después, `/setup` devuelve 404 | ✅ |
| Portal y consola responden | ✅ |
| Hay un producto de ejemplo publicado | ✅ |
| El catálogo declara el contacto del participante | ✅ |
| Cada producto declara su política y su contrato | ✅ |
| La API de administración del conector no está publicada | ✅ |
| El paso al conector exige identidad | ✅ |
| Descargar sin negociación cerrada se rechaza | ✅ |
| El punto SPARQL está cerrado por omisión | ✅ |

**«Si el E2E falla, no hay versión» deja de ser una frase.** El trabajo que
construye declara `needs: pruebas`. `tests/test_release_gate.py` vigila las
cuatro formas de romperlo sin que nada dé error —un `continue-on-error` puesto
un viernes para desatascar una publicación, un `if: always()` en un trabajo
entero, quitar el `needs`, o duplicar la puerta en vez de reutilizarla— y sabe
distinguir un `always()` de limpieza, que sí es correcto, de uno que no lo es.

### Las imágenes

Tres, en GHCR siempre y en Docker Hub cuando haya credenciales. Intel y ARM en
la misma etiqueta; cuatro etiquetas por versión (`1.2.3`, `1.2`, `1`,
`latest`); firmadas sin claves, contra la identidad del propio flujo; con
inventario de componentes y procedencia.

**Docker Hub es opcional a propósito.** Sin sus dos secretos el flujo no
falla: sube sólo a GHCR y sigue. Quien bifurque el repositorio tiene que poder
cortar sus versiones sin credenciales que no son suyas.

**El análisis de vulnerabilidades no bloquea.** Se ejecuta y su informe se
guarda, pero no rompe la publicación: una vulnerabilidad conocida en una
dependencia de la imagen base aparece a diario, y bloquear cada versión por eso
lleva —siempre— a que alguien desactive el análisis. Un informe que se mira
vale más que una puerta que se acaba quitando. Lo que sí bloquea es el
recorrido completo, porque eso depende del código de este repositorio.

### El modo de evaluación

La imagen todo-en-uno no lleva Keycloak, y el conector exige un token válido
en cada petición: `rbacEnabled` sólo controla los roles, no la autenticación.
Hacía falta un modo explícito, y es un interruptor de seguridad, así que:

- se activa **sólo** con la variable puesta a `true`, nunca por omisión;
- se apaga solo si detecta una identidad o un dominio configurados, porque
  tener las dos cosas a la vez significa que alguien lo ha heredado sin querer
  de una plantilla de evaluación —y entonces lo dice, en vez de callarse—;
- se anuncia en el arranque del conector y en el de la aplicación.

No aparece en `.env.example`: ponerlo en la lista de opciones de una
instalación normal es invitar a que alguien lo pruebe «a ver si así arranca».

### Un fallo propio en el Dockerfile todo-en-uno

La comprobación de la suma de Fuseki recortaba el hash a mano con `tr -d` y
`sed`, y como Apache publica `<hash>  <fichero>`, el `tr` pegaba el nombre del
fichero al final del hash: **no coincidía nunca y la construcción fallaba
siempre**, por el motivo equivocado. `sha512sum -c` lee ese formato tal cual.

También llegué a escribir un hash inventado como valor por omisión de un
`ARG`. Eso sí que habría sido grave: una comprobación que parece verificar y
no verifica nada. Está fuera.

### Lo que falta de esta fase

**Publicar.** Requiere credenciales de Docker Hub y empujar una etiqueta al
repositorio, que además ya es público. Las dos cosas son decisiones de
Francisco.

**Volver a cronometrar el recorrido de los diez minutos** cuando las imágenes
estén publicadas: hoy son 53 segundos con las imágenes ya construidas en
local, pero el recorrido que describe el README empieza por descargarlas.

**El aviso de alcance** pasa a `docs/alcance.md`, que es su única copia: estaba
en el README, en la política de seguridad y en las notas de cada versión, y
tres copias a mano divergen —la que se queda vieja es siempre la que alguien
lee—.

**167 pruebas en verde**, 8 saltadas por falta de `jq` en esta máquina; en CI
no se saltan.

---

## La imagen todo-en-uno, probada

`docker run -p 8080:8080 myopendataspace/my-open-dataspace` arranca sana, se
configura por el asistente, publica el ejemplo y **pasa el recorrido completo:
14 comprobaciones**.

Lo que más importa de ese resultado: **«descargar sin negociación cerrada se
rechaza» sigue pasando con la autenticación apagada.** El modo de evaluación
quita la identidad, no los controles del conector. Son cosas distintas y era
importante comprobar que no se habían confundido.

El recorrido pregunta en qué modo está el nodo en vez de suponerlo: un nodo
sin autenticación y uno con ella se ven igual desde fuera hasta que alguien
intenta algo, así que `/api/onboarding/health` lo declara.

### Cuatro fallos que no dan error al construir

La imagen salía, arrancaba y el portal contestaba 200 con el producto roto por
dentro. Cada uno tiene ya su comprobación en
`tests/test_allinone_image.py`, que mira la forma —levantar la imagen son
varios minutos y no cabe en la puerta de calidad—:

1. **PostgreSQL no arrancaba.** El usuario `postgres` no puede escribir su
   registro en el volumen, que es de root. `pg_ctl` esperaba a un servidor que
   nunca venía, y sin un `|| true` el `set -e` se llevaba el guion por delante
   sin decir nada útil.
2. **Fuseki moría dos veces seguidas.** `--loc` no crea la carpeta del almacén
   —dice «Does not exist» y se va— y sin `FUSEKI_HOME` busca su `webapp`
   relativa al directorio de trabajo.
3. **El conector no se ejecutaba.** Se compila con Java 21 y la imagen
   instalaba OpenJDK 17 de Debian: `UnsupportedClassVersionError` en su
   registro mientras el portal seguía contestando 200.
4. **El vigilante no vigilaba.** Detectaba la caída y hacía `exit` dentro de
   un subshell en segundo plano: mataba el subshell y dejaba el contenedor en
   pie sirviendo medio producto, que es justo lo que existe para evitar.

Y uno mío que engañaba más que los cuatro: la comprobación de la suma de
Fuseki recortaba el hash a mano, y como Apache publica `<hash>  <fichero>`, el
`tr -d` pegaba el nombre al final del hash y no coincidía nunca. Llegué además
a escribir un hash inventado como valor por omisión de un `ARG` — una
comprobación que parece verificar y no verifica nada. `sha512sum -c` lee ese
formato tal cual.

---

## Fase 7 — Documentación y personalización

**Hecha el 2026-08-27, salvo la captura del README.**

| | |
|---|---|
| [personalizacion.md](personalizacion.md) | Marca, perfiles, casos de uso, nodos e idioma — y **qué no se personaliza sin tocar código**, dicho ahí para que nadie lo descubra a mitad de una migración |
| [backup.md](backup.md) | Qué salvar, qué no hace falta, cómo restaurar y cómo comprobar que la copia sirve **antes** de necesitarla |
| [dos-nodos.md](dos-nodos.md) | Levantar dos nodos y ver la federación |
| [publicar.md](publicar.md) | Cómo se corta una versión y cómo verificar una imagen |
| [alcance.md](alcance.md) | La única copia del aviso de alcance |
| `deploy/backup.sh` | El guion de respaldo mínimo que pedía la sección 6.3 |

El README enlaza los ocho documentos y dice sin rodeos que las imágenes
**todavía no están publicadas**, de modo que los `docker run` de la portada
aún no resuelven.

### Lo que falta

**La captura del README.** No la puedo hacer desde aquí. El nodo levanta y la
consola responde, así que es cuestión de abrir `http://localhost:8080` con el
nodo en marcha y guardar una imagen de la consola con el ejemplo publicado.

**Un tercer idioma** sigue pasando por las plantillas. Está anotado como
limitación en personalizacion.md, no escondido.

**177 pruebas en verde**, 8 saltadas por falta de `jq` en esta máquina.

---

## Fase 8 — Antes de pulsar «público»

**Doce de los catorce puntos de la sección 14, cerrados y comprobados. Los dos
que faltan no los puedo cerrar yo.**

La lista completa, punto por punto y con quién la sostiene, está en
[revision/lista.md](revision/lista.md).

### Lo primero, porque cambia el procedimiento

El repositorio de destino **ya existe, está vacío y ya es público**. No hay
paso intermedio: no se puede subir, mirar cómo queda y corregir. **El primer
`git push` publica.**

Por eso el árbol local no tiene ningún remoto configurado, y hay una prueba
que falla si alguien se lo pone antes de tiempo. No es paranoia: configurar un
remoto y empujar son dos comandos, y el segundo no pregunta.

### El barrido de secretos

**detect-secrets 1.5.0** sobre los ficheros versionados —no sobre el árbol de
trabajo: lo que importa es lo que se publicaría, y un `.env` local no se
publica—. Resultado en `.secrets.baseline`, triaje en
[revision/secretos.md](revision/secretos.md).

**9 hallazgos, los 9 falsos positivos:** etiquetas de interfaz que llevan la
palabra «password», y contraseñas de prueba que sólo se le dan a un validador
para que las rechace.

**Lo que sí encontró y se corrigió.** El recorrido completo creaba el
administrador con una contraseña escrita en el fichero. Contra un nodo de usar
y tirar da igual; contra el nodo de alguien que ejecutó el recorrido «para ver
si funciona» y luego se lo quedó, no: ese nodo tendría un administrador cuya
contraseña está publicada. Ahora se genera una distinta en cada ejecución y no
se imprime.

`tests/test_secret_scan.py` vuelve a barrer y falla si aparece algo que no está
en la línea base — y también si la línea base arrastra hallazgos que ya no
existen, porque una excepción que ya no hace falta deja de decir nada y
estorba.

### Las listas de excepciones, vigiladas

Este es el fallo de diseño que más me preocupaba de esta fase: **una prueba
con lista de excepciones deja de decir nada en cuanto alguien añade una
entrada para desatascarse un martes.** Hay tres listas y las tres tienen ahora
su límite comprobado:

- **`PROSA`** —lo que puede nombrar SIMPL, Gaia-X, FIWARE, IDSA o EHDS— sólo
  admite documentos y ficheros de prueba. Nunca código. Un `.py` de `app/`
  ahí dentro dejaría la poda sin comprobar en ese fichero para siempre.
- **Los rastros** —dominios, correos e IPs reales— **no se eximen nunca**, ni
  siquiera dentro de un párrafo que explique por qué están. Hay una prueba que
  lee la función de verdad, con `inspect`, y falla si algún día consulta
  `PROSA`.
- **`PENDIENTES`**, en la prueba de configuración, se vacía sola: falla cuando
  una variable listada como pendiente ya tiene quien la lea.

### Plantillas de incidencia

Dos —un fallo y una idea— y una configuración que **manda los problemas de
seguridad a un canal privado** y desactiva la incidencia en blanco. Una
incidencia es pública desde el primer momento, y el primer reflejo de
cualquiera es abrir una: sin esa desviación, el primer fallo explotable que
alguien encuentre acaba publicado antes de que exista el arreglo.

La plantilla de fallo pide los registros y **avisa de mirarlos antes de
pegarlos**: llevan direcciones de correo y nombres de máquina de quien los
pega.

---

## Lo que queda, y por qué no lo cierro yo

### 1. La captura del README — hecha, y encontró un agujero

Se toma con `./deploy/capturas.sh`, en Chrome o Edge headless, contra un nodo
configurado como «Organización de Ejemplo».

**Lo que enseñó no lo había visto ninguna prueba:** el portal público seguía
siendo, entero, el del despliegue de origen —«espacio de datos de salud
urbana», «indicadores sintéticos de calidad ambiental, confort, afluencia,
energía, incendios y radiación electromagnética»— con dos botones grandes que
llevaban a páginas que la poda había borrado. Y la tabla del catálogo decía
«No se encontraron productos de datos federados» en un nodo que tenía dos
publicados, porque leía de una gobernanza externa que este producto no tiene.

**La poda miró el código y no la prosa.** El barrido de términos prohibidos
buscaba `ehds`, `fhir`, `healthdcat`: ninguno aparece en un párrafo escrito en
castellano sobre salud urbana. Un fallo que además no da error —una tabla
vacía se lee como una respuesta, no como una avería—.

Corregido: portal reescrito en las dos lenguas, catálogo leyendo el
`/api/v1/catalog` de cada nodo conocido, con plazo por nodo y todos a la vez
para que uno lento no deje la página cargando. Y dos comprobaciones nuevas que
no existían: **ningún enlace lleva a una página que no existe**, y **ninguna
página habla de la vertical podada**.

Es exactamente para esto para lo que la sección 14 pide una captura.

### 2. La instalación probada por alguien que no sea el autor

La sección 14 pide que alguien que no ha visto el código instale esto en una
máquina limpia siguiendo **sólo el README**. Lo que puedo decir con
honestidad:

- El recorrido completo pasa —14 comprobaciones— contra la composición y
  contra la imagen todo-en-uno.
- La instalación de cero está cronometrada: 53 segundos.
- **Pero lo he probado yo, que escribí el código, y eso no es lo que la
  sección 14 pide.** Lo que una prueba propia no detecta nunca es el paso que
  uno da sin pensar porque ya sabe cómo funciona.

### 3. Aplastar el historial — hecho

`main` tiene **un solo commit y es el commit raíz**, como pide D-001. El
aplastado no cambió ni un byte: el árbol es el mismo objeto antes y después,
`00bb8c08`.

**La historia de trabajo está en la rama local `historia-de-trabajo`**, con
sus 22 commits, y no se empuja. Sus mensajes documentan por qué cada cosa está
como está —los seis fallos que sólo se ven arrancando, las tres opciones que
estaban declaradas y no hacían nada, los cuatro de la imagen todo-en-uno, el
`.gitignore` que se llevó los datos de ejemplo— y eso no vuelve a escribirse.

**Lo que falte a partir de ahora va con `git commit --amend`**, o `main` deja
de tener un solo commit sin que nadie lo note. Está dicho en
[revision/lista.md](revision/lista.md), con la comprobación de una línea.

### 4. Publicar

Configurar el remoto, empujar, y cortar `v0.1.0`. Las tres cosas publican y
las tres son decisión de Francisco.

**237 pruebas en verde**, 8 saltadas por falta de `jq` en esta máquina.

---

## Publicado

**2026-08-27.** [github.com/nekosphera/my-open-dataspace](https://github.com/nekosphera/my-open-dataspace),
un commit, público, con `v0.1.0` cortada.

### Lo que CI encontró y esta máquina no

El primer empujón dejó los tres trabajos en rojo. La puerta hizo exactamente
lo que se construyó para hacer, y uno de los cuatro fallos era grave.

**Todos los guiones estaban versionados como `100644`.** La máquina de
desarrollo es Windows y tiene `core.filemode=false`: `chmod +x` no deja rastro
en el índice de git. Aquí daba igual. Quien clonara en Linux o macOS se
encontraba, en el primer comando del README:

```
$ ./install.sh
bash: ./install.sh: Permission denied
```

Y el arranque de Caddy moría con `exec: permission denied` sin decir por qué.
**Es exactamente lo que la instalación por otra persona iba a encontrar.** CI
llegó antes.

Ahora el bit se comprueba **sobre el clon recién hecho**, que es donde
importa: una prueba que mire el árbol de trabajo de quien lo escribió no
detecta esto nunca.

### Y un fallo mío en una prueba, que es peor que el fallo

`test_ningun_enlace_lleva_a_una_pagina_que_no_existe` **pasaba en local por la
razón equivocada.** `runtime-config.js` se genera en el arranque y no está en
el árbol; en mi máquina había quedado de una ejecución anterior, así que el
fichero existía y la prueba pasaba. En un clon limpio, no.

Una prueba que depende de la basura de una ejecución previa no comprueba nada,
y lo peor es que da confianza. Ahora la lista de ficheros generados es
explícita, y hay otra prueba que comprueba que alguien los genera de verdad —
porque una excepción que no corresponde a nada real es un agujero con forma de
comentario.

Los otros dos eran menores: las comprobaciones de `historia-de-trabajo`
fallaban en CI, donde esa rama no existe porque no se empuja; y shellcheck
avisaba de un `source` con ruta variable en el federador, que es justo lo que
permite ejecutarlo suelto.

### Lo único que queda

**La instalación por alguien que no sea el autor**, clonando de GitHub y
siguiendo sólo el README. La hace Francisco desde otra máquina.

Lo que se busca ahí no es que funcione: es dónde tropieza alguien que no sabe
cómo funciona. El bit de ejecución era de ese tipo, y ya no está; los que
queden serán del mismo tipo.
