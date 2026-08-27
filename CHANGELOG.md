# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Un conector de verdad por participante: su contenedor, su base de datos y
  su instancia EDC.** Antes era una identidad dentro del proceso compartido del
  nodo; ahora aprobar un alta levanta una instancia para esa persona, con su
  base dentro del mismo PostgreSQL, y el nodo le habla por su nombre en la red
  interna. Nadie comparte proceso con nadie.

  - `app/conectores.py` crea, arranca, lista y retira contenedores contra el
    demonio de Docker, por su socket. Sólo toca lo que él mismo etiqueta.
  - El paso acepta `/api/connector/<id>/management/…` para dirigirse a un
    conector concreto: negociar con un vecino y descargar lo suyo es hablar con
    **su** conector, no con el de quien llama. Quién puede qué lo sigue
    decidiendo el conector de destino con el token, que se reenvía tal cual.
  - El catálogo del nodo lee de todos sus conectores y marca cada oferta con el
    suyo. Un conector caído no vacía el resto.
  - En cada arranque se levantan los conectores del registro, y lo que cada
    participante publicó cuando se compartía uno **se lleva a su base**: se
    copia, se comprueba que llegó y sólo entonces se borra del origen.
  - Retirar un participante para y borra su contenedor. **Su base no se toca**:
    es lo que publicó, y se reutiliza si vuelve a darse de alta.

  **Requiere el socket de Docker montado en `app`, y eso es acceso equivalente
  a root en la máquina anfitriona.** Quien alcance ese proceso puede pedirle al
  demonio un contenedor privilegiado o el disco del anfitrión montado. El `:ro`
  del montaje sólo impide reescribir el fichero del socket; no limita nada de
  lo que se hace a través de él. Quien no quiera esa exposición quita la línea,
  y las altas se quedan sin conector propio —el nodo lo dice al aprobar—.


### Security

- **Tres rutas publicaban datos personales sin pedir nada.** Contestaban 200 a
  cualquiera que alcanzara el nodo:

  - `/api/onboarding/connectors` — el correo, el nombre y los apellidos de
    **todos** los participantes.
  - `/api/v1/participants` — el registro de participantes, con su correo.
  - `/api/audit/events` — el registro de operaciones, donde el sujeto de cada
    evento es la dirección de quien lo hizo.

  Ahora: quien administra el nodo ve el nodo entero, cada participante ve lo
  suyo, y quien no se identifica no ve nada.

- **La columna «Proveedor» del catálogo nombraba a cada participante con su
  correo.** Pasa a ser el identificador de su conector —`connector-1ac633f863`—,
  que identifica con quién se negocia sin decir quién es. El conector del nodo
  sigue nombrándose con la organización, que ya es pública.


### Fixed

- **Publicar un producto cuyo dato vive fuera fallaba al final del recorrido y
  sin decir por qué.** El conector sólo va a buscar datos a los dominios de
  `ODS_DOWNLOAD_ALLOWED_HOSTS` —es uno de los dos controles que la
  especificación manda conservar— pero eso se descubría después de publicar,
  crear la política y el contrato, negociar y pulsar descargar:
  `asset source host is not allowed`, sin decir qué dominio ni dónde se
  permite.

  Ahora se comprueba **al crear el activo**, que es cuando se puede arreglar, y
  el aviso nombra el dominio y la variable. El 403 del conector, si algo se
  cuela, también los nombra. El control no cambia: lo que cambia es cuándo se
  entera uno.


- **Un contrato creado poco después de otro no se federaba hasta cinco minutos
  más tarde**, así que quien lo creaba no lo veía, daba por hecho que no había
  salido y volvía a pulsar. Dos causas encadenadas: el freno **descartaba** la
  petición en vez de encolarla, y el catálogo del nodo se servía de una caché de
  hasta treinta segundos, así que la sincronización que sí corría leía la oferta
  de antes del contrato.

  Ahora el freno encola —ninguna petición se pierde y los nodos vecinos siguen
  sin recibir una ronda por pulsación—, la caché caduca en cuanto la oferta
  cambia, y la ventana baja de 15 s a 5. La consola recarga el catálogo del
  espacio de datos al crear el contrato y otra vez pasada la ventana, para que
  la oferta aparezca sin ir a buscarla.

- **Los campos obligatorios del formulario de publicación no decían qué poner.**
  «Tema DCAT-AP» vacío no dice que espera un URI del vocabulario europeo: se
  publicaba, el servidor contestaba «campos obligatorios pendientes» y ahí se
  quedaba. Nombre, descripción, keywords y tema llevan ahora un ejemplo válido
  —copiarlo y publicar funciona— y van marcados como obligatorios, para que lo
  diga el navegador antes de enviar y no el servidor después.


- **La columna «Proveedor» ponía el nodo delante y el participante detrás**, así
  que la oferta de una persona se leía como asignada al nodo: el nombre de la
  organización en grande y un identificador con aspecto de hash debajo. Ahora
  va delante quien la ofrece y debajo, en gris, el nodo donde está.

  Y ese identificador se sustituye por algo que se pueda leer: la organización
  para el conector del nodo, y el correo para el de cada participante —que es a
  quien se escribe para negociar—. No el nombre de la cuenta: el propio
  producto rellena el apellido con la etiqueta del nodo al crearla, y salían
  participantes llamados «Mi Organización». La etiqueta se compone al leer y
  **no se federa**: a un nodo vecino sólo le llega el identificador del
  conector, nunca un correo de aquí.


- **El nodo se federaba a sí mismo por un camino distinto del que ofrece a los
  demás.** Para su propio catálogo leía la API de gestión del conector con el
  token de la cuenta de servicio, que ve el nodo entero: entraban activos sin
  contrato y de conectores ya retirados. Lo que un nodo ofrece se decide en un
  sitio —su catálogo público— y federarse por otro garantizaba que los dos se
  separasen. Se separaron. Ahora se federa por el suyo, como cualquier otro
  nodo.

- **Y no se difunde la oferta de un conector que ya no está.** Retirar un
  participante no borra lo que publicó —el conector no sabe borrar—, así que el
  nodo seguía anunciando ofertas de alguien con quien ya no se puede negociar.
  Quién sigue estando sale de **las cuentas del realm**, no del registro de
  participantes: ese es papeleo que se queda atrás —al borrar una cuenta su
  entrada sobrevive hasta el siguiente arranque— y mientras tanto el nodo
  seguía anunciando la oferta de alguien que ya no está. Si la identidad no
  contesta **no se filtra nada**, porque vaciar el catálogo por eso sería peor
  que ofrecer de más.


- **Lo recién publicado tardaba hasta cinco minutos en aparecer en el catálogo
  del espacio de datos, y ya no había forma de adelantarlo.** El federador va
  cada `ODS_FEDERATION_INTERVAL` —300 s por omisión— y el botón «Actualizar
  ahora» se fue con la pestaña de nodos conocidos. Un participante publicaba su
  activo con su política y su contrato, y ni sus vecinos ni él lo veían.

  Ahora el nodo federa **al nacer un contrato**, que es el momento en que la
  oferta existe para los demás: hasta que no lo hay no se puede negociar. Va en
  el paso al conector y no en la consola, así que vale igual para quien lo cree
  por la API. En segundo plano, para no hacer esperar a quien publica.

  «Recargar federado» sincroniza también antes de mirar, que es lo que se
  espera de ese botón. Y `POST /api/v1/nodes/sync` deja de exigir
  `dataspace-admins`: basta con estar dentro, porque quien publica lo suyo
  tiene que poder hacer que se vea. Con freno —`ODS_FEDERATION_MIN_SECONDS`,
  15 s— para que pulsar repetido no lance una ronda de peticiones a cada nodo
  vecino por cada pulsación; quien administra el nodo no lo tiene.


- **Las copias de seguridad no estaban en `.gitignore`.** `deploy/backup.sh`
  las escribe en `backups/` de la raíz, con el volcado de PostgreSQL y el
  estado del nodo dentro: un `git add -A` las habría publicado.


- **`./reiniciar.sh` no existía donde se le busca.** Se instala con
  `./install.sh` desde la raíz, así que ahí es donde se escribe cuando algo va
  mal — y lo que se encontraba era `No such file or directory`, porque el guion
  vivía sólo en `deploy/`. Ahora está en la raíz y lleva al de siempre.

  Y desde dentro de `deploy/` sí corría, pero sin argumentos imprimía la ayuda
  y **salía con éxito**, que se lee como «ha corrido y no ha hecho nada». Ahora
  sale con error y dice por qué. La ayuda, además, nombra el camino que se ha
  escrito: decía siempre `./deploy/reiniciar.sh`, que desde `deploy/` no existe.

  Es el peor sitio para un tropiezo así: se llega aquí cuando ya no se puede
  entrar en el nodo.

- **En PowerShell, `.
einiciar.sh` no ejecutaba nada y no decía nada.**
  PowerShell no corre ficheros `.sh`: ni error, ni salida, ni nada. Ahora hay
  `reiniciar.ps1` al lado, que llama a bash y pasa los mismos argumentos, y lo
  dicen el README y `docs/recuperar.md`.


- **Un conector cuya persona ya no está en el realm se retira solo**, con su
  grupo vacío. Con un conector por participante, borrar una cuenta dejaba su
  entrada de registro y su grupo detrás, y el registro es lo que consulta quien
  federa: se anunciaba al espacio de datos un participante que no existe. El
  del nodo no se retira nunca, y un grupo con gente dentro tampoco.

- **Y al revés: una cuenta con conector propio y sin entrada de registro la
  recupera.** Le pasa a quien se dio de alta antes de que el registro se
  escribiera, o si una migración se llevó su entrada por delante.

### Added

- **Un conector por participante — Connector as a Service.** Quien se da de
  alta y es autorizado recibe su propio conector con el perfil que pidió:
  consumidor, proveedor o ambos. Suyo de verdad: su identificador, sus
  credenciales, su oferta y su consola. Los activos, políticas y contratos que
  publique son de su conector y no del nodo; en «Ver mis activos» ve lo suyo y
  nada más; y en el catálogo del espacio de datos su oferta aparece atribuida a
  él, de forma que otro participante del mismo nodo la negocia y la descarga
  como la de un tercero.

  Enmienda 16 de la especificación, que sustituye a la decisión 5 de la
  sección 2 y a la parte correspondiente de la sección 4. Siguen siendo seis
  contenedores: el conector de cada participante es una identidad dentro del
  tiempo de ejecución EDC del nodo, no un contenedor por persona.

  Las piezas: el claim `connector_id`, firmado por Keycloak desde un atributo
  de la cuenta —no deducido del nombre de un grupo ni del identificador de un
  activo, las dos formas que ya fallaron aquí—; columna `connector_id` en
  `assets`, `policy_definitions` y `contract_definitions`, sellada desde el
  token al escribir y filtrada al leer; el federador atribuyendo cada oferta a
  su conector; y la consola tomando su identidad del token en vez de la página
  generada, que la comparte todo el nodo.

  Un nodo ya instalado se migra solo en el arranque: se añade el claim al realm
  importado y se rellena el conector de las cuentas que ya existían, la de quien
  instaló el nodo con el conector del nodo. Nadie pierde su acceso.

- `tests/e2e/navegador_conector_por_participante.py`: los criterios 10 a 13 de
  la enmienda, en un navegador. Dos participantes del mismo nodo, uno publica y
  el otro negocia y descarga; cada uno ve sólo lo suyo entre sus activos; un
  consumidor no puede publicar.


### Changed

- El README lleva una **captura de la consola**, tomada de un nodo limpio
  levantado para eso —nada de datos reales—, y la del portal se ha vuelto a
  hacer: la que había enseñaba los dos botones de la portada descuadrados, que
  ya está arreglado.

- Fuera `diagnostico.txt`, que estaba versionado y vacío. Es la salida de
  `deploy/diagnostico.sh`, se genera en la raíz al ejecutarlo y lleva dentro el
  estado del nodo de quien lo corre: ahora está en `.gitignore`.


- **La pestaña «Nodos conocidos» no se ofrece.** El panel, el alta de nodos, la
  lista con su última sincronización y «actualizar ahora» siguen en la consola
  y en el código, intactos; lo que se retira es el botón que lleva a ellos. Se
  apaga en un solo sitio y se vuelve a encender ahí mismo. Mientras tanto se
  dan de alta nodos por `POST /api/v1/nodes`, como explica `docs/dos-nodos.md`.

### Fixed

- **El atributo `hidden` no ocultaba nada en los botones.** La regla
  `button, .btn { ... display: inline-block }` declara un `display` para todo
  botón, y cualquier declaración de autor gana a la del navegador para
  `[hidden]`, tenga la especificidad que tenga: el botón quedaba con el
  atributo puesto y dibujándose igual. Le pasaba a la pestaña de nodos
  conocidos y, antes, a la de aprobar altas, que se le enseñaba a quien no
  puede usarla —el servidor la rechazaba con un 403, pero el botón estaba
  ahí—. La prueba de navegador lo daba por bueno porque comprobaba el
  atributo; ahora comprueba lo que se dibuja.


- **No se podía negociar ni descargar nada de la oferta del propio nodo**, que
  es justo lo que pide el criterio 6 de la sección 12: publicar un producto y,
  desde la vista de consumo, negociar su contrato y descargar el dato. La
  consola devolvía «Activo propio» desactivado para toda fila de este nodo, y
  `requestNegotiation` rechazaba con «no se negocian assets propios». En un
  nodo con varios participantes dejaba fuera además a quien se acababa de dar
  de alta: la oferta del nodo le salía como suya. Lo que decide si se puede
  descargar sigue siendo lo de siempre —una negociación cerrada, y el conector
  la ata a la persona que la hizo, no al nodo—.

- **La descarga de un producto alojado en el propio nodo nunca funcionó.** El
  activo lleva la URL pública del nodo —tiene que llevarla: es la que viaja en
  el catálogo federado y la que otro nodo necesita—, y desde el contenedor del
  conector esa dirección no lleva al portal sino al propio conector. Fallaba
  con `upstream download failed`, el producto de ejemplo incluido. El conector
  traduce ahora el prefijo público de **su** nodo a la dirección interna del
  portal, y lo hace **después** de comprobar la lista de destinos permitidos,
  para que ese control siga diciendo lo mismo.

- **La consola adivinaba el dueño de cada recurso** con
  `/connector-[a-z0-9]+/` sobre el identificador, del despliegue de origen con
  tres conectores. Con un conector llamado `connector`, un activo
  `asset-connector-mtck41dc-x` daba el dueño inventado `connector-mtck41dc` y
  negociar contra él fallaba con «proveedor no configurado». Un nodo tiene un
  conector: lo que devuelve es suyo, y no hay nada que adivinar.

- **Dos peticiones a rutas que este conector no implementa** —
  `/management/v3/edrs` y `/management/v3/transferprocesses` — en cada
  negociación y en cada descarga. Devolvían siempre vacío y dejaban dos 404 en
  la consola del navegador. El conector sirve cuatro recursos y ahora hay una
  prueba que compara la lista blanca del paso con lo que sirve de verdad.

### Security

- **Cualquier persona dada de alta podía aprobar y denegar altas ajenas**, y
  leer los datos personales de quien estuviera esperando. `REQUEST_REVIEWER_GROUPS`
  incluía `connector-users`, y a ese grupo entraba **toda** persona aprobada.
  Ahora aprobar es cosa de `dataspace-admins` y nada más.

- **Dar de alta a alguien como proveedor lo convertía en administrador del
  nodo.** Publicar exigía el rol `dataspace-admin`, que es el mismo que
  gobierna el nodo, así que no había forma de dejar publicar a alguien sin
  darle también permiso para aprobar altas. Se separan: rol `dataspace-provider`
  y grupo `dataspace-providers`, y el conector acepta ese rol para escribir.
  El arranque los crea en los nodos que ya estaban instalados.

### Fixed

- **El alta minaba un identificador de conector por persona** —
  `connector-<sha1 del correo>` — con su cliente de Keycloak, su cartera, su
  registro y su participante. Ese conector no existía: un nodo tiene uno, y así
  lo cierran la decisión 5 de la sección 2 de la especificación y la sección 4
  («Eliminar del aprovisionamiento dinámico de conectores todo lo que instancie
  más de uno»). Era poda que quedó a medias.

  Lo que provocaba: se daba de alta a alguien, se le decía «tu conector se ha
  creado correctamente», y al entrar en la consola **todos los activos del nodo
  le salían como propios** —porque lo son— y no podía negociar nada. Ahora un
  alta es pasar a ser participante del conector del nodo, y se dice así.
  Negociar es entre nodos: criterio 8 de la sección 12, y `docs/dos-nodos.md`.

  El arranque migra a quien quedó colgando de uno de aquellos conectores: le da
  el grupo del conector del nodo y retira el papeleo del conector inexistente.
  Ninguna cuenta se toca.

- **El color de marca se elegía y no cambiaba nada.** Llegaba hasta
  `runtime-config.js` y ahí se quedaba: la hoja de estilo tenía su paleta
  escrita a mano. Ahora `site-config.js` deriva de él los cinco tonos de marca
  y los aplica antes de que la página se pinte. Los colores de estado
  —correcto, aviso, error— no siguen la marca a propósito: significan algo.

- **Los dos botones de la portada salían de distinto tamaño**: `.btn + .btn`
  añade 8px de margen superior al segundo, pensado para cuando van apilados, y
  en una fila que estira se los quitaba de alto.

- **Ninguna referencia a que se enviará o se recibirá un correo.** La
  instalación por omisión no tiene correo saliente, así que decirle a alguien
  que espere un aviso es mandarle a esperar un mensaje que nadie manda. Se dice
  lo que sí es cierto y accionable: que hay que aprobarlo y que vuelva a
  intentar entrar.

- **El registro de operaciones de la página pública no cargaba nunca**: pedía
  `/api/connector-1/…`, `-2` y `-3`, tres identificadores del proyecto de
  origen. Y la página de alta decía que «Connector-1» revisaría la solicitud.

- **`urllib.parse` sin importar `urllib`**, dentro de un `try/except` que se
  tragaba el `NameError`: el emisor interno de tokens nunca se añadía a la
  lista de aceptados y nadie se enteraba.

### Added

- `tests/test_no_hay_nombres_sin_definir.py`: ninguna función puede nombrar
  algo que no existe. Borrando código muerto se fueron por delante dos
  constantes escritas entre las funciones retiradas; el fichero seguía
  compilando y el fallo salió horas después, una tumbando `/health` con un
  `NameError` en cada petición. En su primera ejecución encontró además el
  `urllib` de arriba, que llevaba ahí desde el principio.

- **La consola no funcionaba: ni se llegaba a ella, ni sus llamadas llegaban a
  ningún sitio.** Encontrado conduciendo un Chrome de verdad contra
  `/login.html`, que es por donde se entra. Ninguna prueba lo decía porque
  todas llamaban a las rutas correctas directamente, sin ejecutar el
  JavaScript de la página.

  - El paso al conector aceptaba `/api/connector/v3/…` y la consola pide
    `/api/connector/management/v3/…` —la forma de la API de EDC, y la que hay
    que usar también contra un nodo remoto—. **Todas** sus llamadas daban 404:
    la consola cargaba con buena cara y no podía leer ni publicar nada.
  - Quien administra el nodo entraba bien y aterrizaba en la página pública,
    que sigue diciendo «Acceder». Desde fuera es indistinguible de no haber
    entrado, y le pasaba a la primera persona de cada instalación.
  - La consola hablaba con `/api/governance/…`, un servicio externo que se
    quitó al separar el producto de su origen, para cuatro identificadores de
    espacio de datos —tres de ellos del origen: `dataspace-a`, `dataspace-b`,
    `myfiware`—. Además toda fila del catálogo se juzgaba «de otro espacio de
    datos», porque el identificador que trae es el del conector y nunca
    coincide con el de la organización: **ningún botón de negociar o descargar
    hacía nada**, ni siquiera sobre los activos del propio nodo.
  - `/api/v1/edc/bridge/payloads` y `papers_manifest.json`, del origen, daban
    404 en cada contrato y en cada carga del catálogo.

- **No había ninguna pantalla donde aprobar un alta.** El módulo que la trae
  empezaba por `if (cfg.id !== "connector-1") return;` —un identificador del
  proyecto de origen—, así que se apagaba solo en todas las instalaciones; y
  aunque no se apagara, buscaba unos identificadores que la consola generada no
  tiene. Una persona se registraba, se le decía que esperase, y no había sitio
  donde aprobarla. Ahora la consola generada trae su pestaña de solicitudes y
  participantes, visible para quien está en `dataspace-admins`.

- **Aprobar un alta le quitaba a todo el nodo la mitad de su consola.** La
  consola es una sola y la comparte el nodo entero, pero se regeneraba con el
  perfil de la última persona aprobada: tras aprobar a un consumidor,
  desaparecía la pestaña «Proveedor de datos» para todos, empezando por quien
  administra. Ahora la consola enseña lo que el nodo sabe hacer y lo que cada
  persona puede hacer lo decide su token, que es lo que el RBAC del conector
  hace cumplir de todas formas.

- **El registro de operaciones no existía.** `POST /api/audit/events` firmaba
  el evento y llamaba después a `forward_audit_event`, una función que no está
  definida en ninguna parte —quedó el hueco al quitar el servicio de gobernanza
  externo—. El `except` de alrededor convertía el `NameError` en un 502
  «audit_forward_failed», así que **todos** los eventos fallaban y parecía un
  problema de red; y no había forma de leerlos. Ahora se guardan firmados en el
  volumen de estado y se sirven por `GET /api/audit/events`.

- **No se podía publicar nada desde la consola.** Enviaba
  `myds:deliveryMode` —el prefijo del proyecto de origen— y el perfil de
  metadatos exige `ods:deliveryMode`: la validación contestaba «campos
  obligatorios pendientes» pasara lo que pasara. Además no había campo para
  elegirlo. Ahora se elige entre los cuatro valores que el perfil admite.

- **Ninguna fila del catálogo traía con qué negociar.** La consulta pedía la
  política colgada del activo, y el federador la escribe como sujeto aparte
  enlazado por la definición de contrato. Aceptar una política contestaba
  siempre «datos de negociación incompletos».

- **El catálogo público no decía bajo qué condiciones se accede a lo publicado
  desde la consola**, porque allí el enlace vive en la definición de contrato.
  Ahora se declara `ods:policyId` y `ods:contractId` a partir de ella, y lo que
  no tiene contrato **no se difunde**: un activo sin contrato no está ofrecido
  y anunciarlo manda a los nodos vecinos una oferta que nadie puede obtener.

- **Lo que el asistente decidía no sobrevivía a un reinicio.** `runtime-config.js`
  se genera en el arranque **sólo desde el entorno**, así que un nodo
  configurado como «PACO» volvía a llamarse «Mi Organización» en cada
  reinicio, con el correo de contacto de ejemplo, y las respuestas del
  asistente se quedaban en `site.json` sin que nadie las mirara.

- **«Actualizar ahora» fallaba con `invalid_json`**: manda un POST sin cuerpo,
  y el servidor trataba un cuerpo vacío como un JSON roto.

- **El alta prometía un correo que nadie enviaba.** Sin SMTP configurado —la
  instalación por omisión— ahora se dice que no habrá aviso y qué hacer.

- **Tres correos del proyecto de origen decidían a dónde iba cada persona
  después de entrar**, comparados por el principio de la dirección, y llevaban
  a `/connector-1.html`, `-2` y `-3`, páginas que este producto no tiene. Quien
  tuviera la mala suerte de llamarse así aterrizaba en un 404.

- **La consola apuntaba a `/api/<id-del-conector>`** y el paso vive en
  `/api/connector` y sólo ahí: en cuanto alguien pusiera `ODS_CONNECTOR_ID`
  distinto de `connector`, la consola dejaba de funcionar entera.

### Added

- `tests/e2e/navegador_alta_y_acceso.py`: el alta, el acceso, la aprobación y
  la publicación **en un navegador de verdad**, por el protocolo de DevTools.
  Es la única prueba que ejecuta el JavaScript de la consola y del acceso, que
  es donde estaba todo lo de arriba. Va en la puerta de integración; si no hay
  navegador sale con código 2 y se ve como saltada, nunca como verde.

- `tests/test_la_consola_no_llama_a_lo_que_no_existe.py`: cada ruta que la
  interfaz nombra tiene que existir en el servidor, y los nombres del proyecto
  de origen no pueden volver. Lleva una prueba de sus propios patrones: uno de
  ellos se escribió con un `` que acabó siendo un byte de retroceso, no
  encontraba nada nunca, y pasaba en verde diciendo que no había restos.

- **El acceso no funcionaba sobre HTTP plano**, que es la instalación por
  omisión. Keycloak marca su cookie de sesión con `Secure; SameSite=None`, y
  un navegador **se niega a guardar una cookie `Secure` en un origen
  `http://`**: al enviar el formulario la cookie no viaja, Keycloak responde
  `cookie_not_found` y la página traduce el 400 a «No se pudo completar el
  login». Caddy le quita el `Secure` y baja `SameSite` a `Lax` **sólo cuando
  se sirve en claro**; sobre HTTPS no se toca nada.

- **El administrador que crea el asistente no podía entrar.** Se creaba con
  nombre y sin apellido, y Keycloak 26 exige `VERIFY_PROFILE` a las cuentas
  incompletas: tras acertar la contraseña, en vez de volver con un código, se
  va a una pantalla de perfil que la consola no sabe completar. Le pasaba a
  cada nodo recién instalado, a la primera persona que lo intentaba.

  Dos arreglos, porque uno solo no bastaba: las cuentas que crea el producto
  llevan perfil completo, y `VERIFY_PROFILE` y `VERIFY_EMAIL` se desactivan en
  el realm —y también en cada arranque, para los nodos ya instalados—. Sin lo
  segundo, cualquier cuenta creada a mano volvería a bloquearse.

- **La consola pedía el catálogo consolidado al SPARQL de Fuseki**, con sus
  credenciales de administración metidas en la página (`btoa("admin:")`).
  Nadie enruta `/fuseki` —y no debe: publicarlo es justo lo que
  `ODS_SPARQL_PUBLIC=false` evita—, así que contestaba el 404 de la propia
  aplicación. Ahora la consulta la hace el servidor en `/api/v1/nodes/catalog`
  y esas credenciales no salen del contenedor.


- **El acceso no funcionaba.** La poda de la fase 1 borró `app/ui/vendor/`
  tomándola por lastre de terceros, y dentro estaba el adaptador de Keycloak
  que importan las dos páginas de acceso, la consola y el panel de auditoría.
  El `import()` fallaba, un `catch` se lo tragaba, y la página decía «No se
  pudo completar el login» sin más. Vuelve al árbol, vendorizado y no desde un
  CDN.
### Changed

- El cliente `dataspace-ui` declara ahora su `rootUrl` y destinos absolutos, y
  el arranque los ajusta a `ODS_PUBLIC_URL`. **No arregla ningún fallo**: con
  `redirectUris: ["/*"]` Keycloak ya aceptaba la vuelta a `/login.html`,
  porque la identidad y el portal comparten origen detrás de Caddy. Es
  explícito en vez de implícito, y es lo que hace falta el día que alguien
  ponga Keycloak en otro origen con `ODS_AUTH_URL`.
- **Publicar desde la consola era imposible.** `createAsset` y `createPolicy`
  exigían un informe de análisis documental que la poda de la fase 2 había
  quitado, así que «Crear Asset» respondía «revisa el análisis» sobre un
  análisis que ya no existe.

### Added

- **`./deploy/reiniciar.sh`**, con tres niveles: cambiar la contraseña de una
  cuenta, reabrir el asistente sin perder lo publicado, o borrarlo todo. Es la
  «orden explícita en la línea de comandos» que la especificación pedía para
  reconfigurar y que **no se había escrito**: `/setup` devuelve 404 en cuanto
  el nodo está configurado, así que quedarse fuera obligaba a borrar los
  volúmenes. Documentado en `docs/recuperar.md`.

### Fixed en las herramientas

- **`--asistente` decía «Hecho» sin hacer nada**, y **`backup.sh` podía
  archivar el directorio equivocado**. La misma causa: en Git Bash sobre
  Windows, una ruta absoluta pasada como argumento suelto a
  `docker compose exec` se convierte en ruta de Windows antes de que Docker la
  vea. El comando se ejecuta, sale con cero y actúa sobre otra cosa.

  Las rutas van ahora dentro de un `sh -c`, y —lo que importa— **cada acción
  comprueba su propio efecto**: el reinicio verifica que el marcador ha
  desaparecido, y la copia que el archivo no ha salido vacío. Una copia que no
  contiene lo que crees sólo se descubre el día que hace falta restaurarla.

### Documented

- **La imagen todo-en-uno pierde todo al borrar el contenedor**, y no lo
  decía. `docker run` sin `-v` crea un volumen anónimo, y al volver a lanzar
  la imagen Docker crea otro: el nodo configurado, su administrador y lo
  publicado desaparecen, y lo único que se ve es que el asistente vuelve a
  salir. El README lleva ahora el `-v` y la imagen lo avisa al arrancar.

  Se avisa **siempre**, sin intentar detectarlo: desde dentro de un
  contenedor un volumen con nombre y uno anónimo se ven idénticos
  —`/dev/sde /var/lib/ods ext4` los dos—, así que una detección sólo podía
  acertar por casualidad. La primera versión de este aviso callaba justo en el
  caso peligroso.

  La composición de seis contenedores **sí persiste**: comprobado con un
  `down` y un `up -d`, con sus activos, políticas y contratos intactos.

### Removed

- Lo que quedaba de la capa de IA en la consola: la tarjeta «Flujo guiado», el
  botón «Analizar URL», el «Informe de auditoría del documento», «Regenerar
  política» y el «Informe de política sugerida». Sus rutas se habían podado en
  la fase 2 y quedaron los botones, que no hacían nada.

  Se mantiene el campo «Uso para IA» de la política: es una cláusula sobre si
  el dato puede usarse para entrenar, que es metadato y no una función.


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
