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
