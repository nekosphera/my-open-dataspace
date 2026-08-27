# Decisiones tomadas durante la implementación

Las decisiones de producto están cerradas en la especificación. Aquí se anotan
sólo las que la especificación no cubría, resueltas eligiendo la opción más
simple que cumple los criterios de aceptación.

Formato: qué se decidió, por qué, y qué habría que cambiar si se decidiera al
revés.

---

## D-001 — Historial: commits por fase durante el desarrollo, un solo commit al publicar

**Decisión.** Se trabaja con un commit por fase, como pide la regla de
ejecución. Antes de pasar el repositorio a público (fase 8) se aplasta todo en
un único commit inicial.

**Por qué.** Las dos exigencias —«commit al terminar cada fase» y «un único
commit inicial»— se refieren a momentos distintos: la primera al desarrollo, la
segunda al árbol publicado. Aplastar al final las cumple ambas y conserva la
trazabilidad mientras se trabaja.

**Si se decidiera al revés.** Habría que renunciar a poder revisar fase por
fase, o publicar un historial de desarrollo que no aporta nada a quien instale.

---

## D-002 — El catálogo federado se toma del repositorio `catalejo`, no de `mydataspace/catalogue`

**Decisión.** `federation/` sale del repositorio público `catalejo`.

**Por qué.** `mydataspace` mantenía una copia vendorizada en `catalogue/` que
sólo contiene la biblioteca de perfiles y el humo. El repositorio original trae
además el federador, los vocabularios DCAT-AP y ODRL con sus formas SHACL, y la
configuración de rotación de registros. Es el árbol completo y es el que recibe
las mejoras aguas arriba.

**Si se decidiera al revés.** Habría que reconstruir a mano el federador y los
vocabularios, que es justo lo que la especificación pide no hacer.

---

## D-003 — El árbol de trabajo vive en `repos/my-open-dataspace`

**Decisión.** El repositorio nuevo se crea junto a los de origen, en su propio
directorio, sin relación de git con ninguno de ellos.

**Por qué.** Deja evidente que es un árbol independiente y que los de origen no
se tocan.

---

## D-004 — El vocabulario pasa a `urn:ods:` en vez de a un dominio

**Decisión.** El espacio de nombres de los términos propios, y los
identificadores de los perfiles y de sus formas SHACL, dejan de ser URLs
`https://www.<dominio>/ns#` y pasan a IRIs `urn:ods:`.

**Por qué.** Un IRI de vocabulario no tiene por qué resolver, y ninguna de
las dos alternativas servía: mantener el dominio de origen publica una
dirección de producción en un repositorio público, e inventar uno nuevo
—`myopendataspace.org`— reclama un dominio que el proyecto no posee y que
alguien podría registrar y usar. Un `urn:` no obliga a poseer nada ni a
mantener un servidor vivo para que un catálogo siga validando.

**Si se decidiera al revés.** Habría que comprar y mantener el dominio, y
publicar en él los documentos de perfil, para que la única ventaja —que un
lector pueda pegar el IRI en un navegador— existiera de verdad.

---

## D-005 — Un `urn:` para la identidad que firma la auditoría

**Decisión.** El registro de operaciones lo firma `AUDIT_ISSUER`, que sale de
`ODS_PUBLIC_URL` o, a falta de ella, de `ODS_ORG_ID`. Antes lo firmaba un DID
resuelto por `did:web` contra un dominio propio.

**Por qué.** La sección 9 poda la resolución `did:web`, pero la sección 9
también conserva expresamente «el registro de operaciones y denegaciones
consultable desde la consola». Las dos cosas se cumplen a la vez si el
registro sigue firmado y encadenado y quien firma es el propio nodo, que es
la única identidad que quien instala controla.

**Si se decidiera al revés.** Volver al DID exige que quien instale posea un
dominio y publique en él un documento `did.json`, que es exactamente el tipo
de requisito previo que la instalación en cinco minutos no puede tener.

---

## D-006 — El federador vive dentro de `app`, no en un séptimo contenedor

**Decisión.** El federador de catálogos se ejecuta dentro del contenedor
`app`.

**Por qué.** La sección 3 fija seis contenedores y ninguno más. El federador
necesita justo lo que `app` ya tiene: el intervalo de sincronización, la
lista de nodos conocidos y el botón de «actualizar ahora» de la consola.
Sacarlo a un contenedor propio obliga a duplicar esa configuración y a
inventar un canal para el botón.

**Si se decidiera al revés.** Serían siete contenedores, contra la
especificación, a cambio de poder reiniciar el federador sin reiniciar el
portal — que no es un problema que este producto tenga.

---

## D-007 — La sonda de despliegue y la matriz de cuentas salen del RBAC

**Decisión.** `setup_keycloak_rbac.sh` deja de traer una matriz de usuarios y
crea una sola cuenta: la de `ODS_ADMIN_EMAIL`. La cuenta de sonda que el
recorrido de interfaz usaba desaparece.

**Por qué.** La matriz traía tres direcciones de correo reales escritas en el
código. La sonda se derivaba del dominio de la primera de ellas, un mecanismo
que sólo tiene sentido cuando un repositorio sirve a varios dominios a la
vez; aquí cada nodo es uno.

**Si se decidiera al revés.** Habría que inventar una dirección de sonda, que
o bien es de un dominio de ejemplo —y entonces el correo no llega— o bien es
del dominio de quien instala sin que lo haya pedido.

---

## D-008 — La consola del nodo es una y enseña lo que el nodo sabe hacer

**Decisión.** `write_connector_pages` genera siempre la consola con perfil de
proveedor **y** consumidor. Deja de generarse con el perfil de la persona
recién aprobada. Lo que cada persona puede hacer lo decide su token, y quien
lo hace cumplir es el RBAC del conector: leer con `dataspace-user`, escribir
con `dataspace-admin`, negociar con `dataspace-negotiator`.

**Por qué.** La consola es un solo fichero que comparte todo el nodo —lo dice
el propio código cuando retira un conector: «La consola no se borra: es una
sola y la comparte todo el nodo»—. Generarla con el perfil de una persona se
lo aplicaba a todas: aprobar a un consumidor le quitaba la pestaña de publicar
a quien administra el nodo, y el formulario, aunque siguiera en el HTML, ya no
se podía enviar porque vivía dentro de un panel oculto con campos
obligatorios. Se ve sólo entrando.

**Si se decidiera al revés.** Habría que generar una consola por persona
—`console-<quien>.html`, servida según el token— o decidir las capacidades en
el navegador en vez de al generar la página. Lo segundo es lo correcto a
futuro; lo primero multiplica un fichero generado por cada participante. Ahora
mismo, quien pulse algo que no le corresponde recibe el 403 del conector, que
dice qué rol falta, y la consola lo enseña tal cual.

---

## D-009 — El catálogo público difunde sólo lo que tiene contrato

**Decisión.** `/api/v1/catalog` deja fuera los activos que ninguna definición
de contrato cubre. Siguen visibles para su dueño en «Ver mis activos», que lee
del conector directamente.

**Por qué.** Un activo sin contrato no está ofrecido: nadie puede negociarlo y
el conector lo rechazaría. Difundirlo manda a todos los nodos vecinos una
oferta que no existe, y le pasa a cualquiera que cree el activo y todavía no
le haya hecho el contrato —un paso intermedio normal de la consola—.

**Si se decidiera al revés.** El catálogo sería un inventario en vez de una
oferta, y quien lo lea desde otro nodo tendría que negociar para descubrir
que no había nada que negociar.

---

## D-010 — Hay una prueba que abre un navegador

**Decisión.** `tests/e2e/navegador_alta_y_acceso.py` conduce Chrome por el
protocolo de DevTools y va en la puerta de integración. Si no hay navegador,
sale con código 2 y el paso avisa de que se saltó; nunca se ve como verde.

**Por qué.** Las pruebas de API llamaban a las rutas correctas directamente y
daban verde mientras la consola no podía leer ni publicar nada, quien
administra el nodo aterrizaba en la página pública y no había ninguna pantalla
donde aprobar un alta. Ninguna de esas tres cosas se ve sin ejecutar el
JavaScript de la página, y ejecutarlo es abrir un navegador.

**Si se decidiera al revés.** Quedarían fuera de la puerta justo los fallos
que este producto ha tenido: los que están entre el navegador y el servidor, y
no dentro de ninguno de los dos.

---

## D-011 — Un alta es un participante del conector del nodo, no un conector nuevo

**Decisión.** El alta deja de generar `connector-<sha1 del correo>` con su
cliente, su cartera, su registro y su participante. Quien se da de alta entra
en el conector que el nodo ya tiene, con el perfil que haya pedido.

**Por qué.** La especificación lo cierra en dos sitios: decisión 5 de la
sección 2 y sección 4. Aquel identificador no era un conector —hay un único EDC
por nodo—, sino una etiqueta; y como el catálogo consolidado atribuye cada
oferta al nodo que la publica, a la persona recién dada de alta todos los
activos le salían como propios y no podía negociar nada. El producto le había
dicho que tenía conector.

**Si se decidiera al revés.** Habría que levantar un EDC por participante,
con su puerto, su base y su identidad, que es justo lo que el no-objetivo «el
segundo y tercer conector» descarta para la v0.1.

---

## D-012 — Publicar y administrar el nodo son dos permisos distintos

**Decisión.** Rol `dataspace-provider` y grupo `dataspace-providers`. El
conector acepta `dataspace-provider` o `dataspace-admin` para escribir.
Aprobar altas queda sólo en `dataspace-admins`.

**Por qué.** Eran lo mismo: para dejar publicar a alguien había que meterlo en
`dataspace-admins`, y ese grupo daba permiso para aprobar y denegar altas
ajenas y leer los datos de quien esperaba. Además `REQUEST_REVIEWER_GROUPS`
incluía `connector-users`, al que entra toda persona aprobada, así que en la
práctica cualquiera podía revisar altas.

**Si se decidiera al revés.** Un nodo con dos proveedores tendría dos
administradores, y no habría forma de dar de alta a alguien para publicar sin
darle también la lista de solicitudes pendientes.

---

## D-013 — El conector alcanza su propio nodo por dentro

**Decisión.** El conector recibe `EDC_UPSTREAM_PUBLIC_URL` y
`EDC_UPSTREAM_INTERNAL_URL` y traduce el primero por el segundo antes de ir a
buscar el dato. La lista de destinos permitidos se comprueba **sobre la
dirección declarada**, no sobre la traducida.

**Por qué.** Un activo alojado en el nodo lleva su dirección pública, y tiene
que llevarla: es la que viaja en el catálogo federado y la que otro nodo usa.
Desde el contenedor del conector esa dirección no lleva al portal. Sin la
traducción, descargar cualquier producto del propio nodo —el de ejemplo
incluido— falla siempre.

**El orden importa y por eso hay una prueba.** Si se tradujera antes de mirar
la lista, declarar un activo apuntando al prefijo público bastaría para
alcanzar cualquier ruta interna, y el control diría que sí a algo que no ha
mirado.

**Si se decidiera al revés.** Habría que guardar la dirección interna en el
`dataAddress` y la pública en los metadatos, que arregla lo que escribe el
servidor pero no lo que publica una persona pegando la URL pública de un
fichero que ha subido a este mismo nodo —que es el caso corriente—.

---

## D-014 — La pestaña «Nodos conocidos» no se ofrece en esta entrega

**Decisión.** El botón desaparece de la consola. El panel, su formulario de
alta, la lista con la última sincronización de cada nodo y «actualizar ahora»
**se quedan en la página y en el código**, intactos y probados. Se apaga en un
solo sitio: `visibleFor.operationNodesPanel` en `initOperationTabs`. Volver a
ofrecerla es cambiar ese `false` por `true`.

**Por qué.** Lo pide quien lleva el producto para esta entrega. Se apaga la
puerta, no se tira la habitación: borrarla obligaría a reescribirla entera para
la siguiente versión, y lo que hay funciona.

**Qué se pierde mientras tanto.** La única forma desde la interfaz de dar de
alta otro nodo, que es lo que el criterio 8 de la sección 12 necesita. La
federación periódica sigue corriendo con los nodos ya dados de alta, y las
rutas siguen ahí: `POST /api/v1/nodes`, `POST /api/v1/nodes/sync` y
`DELETE /api/v1/nodes/<id>`. `docs/dos-nodos.md` explica el procedimiento con
ellas.

**Si se decidiera al revés.** Borrar el panel dejaría el árbol más limpio y
costaría rehacerlo entero cuando vuelva a hacer falta; el coste de dejarlo es
un panel que nadie ve.

---

## D-015 — Un conector por participante, dentro del tiempo de ejecución del nodo

**Decisión.** Cada participante autorizado tiene su conector. La separación es
de datos y de permisos: `connector_id` en las tablas del conector, sellado
desde el claim del token y filtrado al leer. No hay un contenedor por persona.

**Esto sustituye a la D-011**, que decía lo contrario —un alta es acceso al
conector del nodo— siguiendo la decisión 5 de la sección 2 tal y como estaba
escrita. La enmienda 16 de la especificación, del 28 de agosto de 2026, cambia
esa decisión.

**Por qué así y no con un contenedor por participante.** La sección 3 fija seis
contenedores. Un contenedor por persona exige orquestación dinámica desde
dentro del nodo —el socket de Docker montado en `app`, puertos, una base y un
cliente OIDC por conector—, que es una superficie de privilegio grande a cambio
de un aislamiento que aquí no hace falta: lo que separa a dos participantes es
que no vean ni toquen lo del otro, y eso lo dan la columna y el filtro.

**Dónde está el límite, dicho para que nadie se lleve una sorpresa.** Comparten
proceso, base de datos y puerto. Un fallo del conector los para a todos. No hay
aislamiento de recursos entre participantes. El README lo dice.

**Quién ve el nodo entero.** `dataspace-admin`, por `EDC_CATALOG_ROLES`. Es lo
que permite que la cuenta de servicio componga el catálogo público del nodo, y
lo que corresponde a quien lo opera.
