# Personalizar tu nodo

Este es el motivo de que el proyecto exista: que una organización instale
esto, le ponga lo suyo y no tenga que tocar código para nada de lo que sigue.

Si algo de esta página te obliga a editar un `.py`, es un fallo del proyecto.
Dilo en una incidencia.

## La marca

Nombre, correo, color, logotipo y aviso legal salen del asistente de primer
arranque. Después se cambian en `.env` y se vuelve a levantar:

```bash
ODS_ORG_NAME="Ayuntamiento de Ejemplo"
ODS_BRAND_COLOR="#0b6e4f"
ODS_LOGO_PATH="/assets/brand/logo.svg"
ODS_ICON_PATH="/assets/brand/icono.ico"
ODS_LEGAL_NOTICE="Aviso legal — Ayuntamiento de Ejemplo"
```

El logotipo y el icono son rutas dentro del volumen de marca, no ficheros del
repositorio. Se dejan ahí:

```bash
docker compose cp logo.svg app:/srv/ods/app/ui/assets/brand/logo.svg
```

`app/ui/assets/brand/` está en `.gitignore` a propósito: tu marca es tuya y no
tiene por qué acabar en un `git status` cada vez que actualices.

La interfaz lee todo eso de `runtime-config.js`, que **se genera en cada
arranque** a partir del entorno. No lo edites: se sobrescribe.

## Los perfiles de metadatos y de política

En `profiles/`. Se entregan dos genéricos:

```
profiles/
├─ dcat-ap/1.0.0/    perfil DCAT-AP y sus formas SHACL
├─ odrl/1.0.0/       perfil de política ODRL
├─ ns.jsonld         los términos propios del proyecto
└─ manifest.json     el índice que la consola consulta
```

**Añadir el tuyo es copiar una carpeta.** Ni una línea de código:

1. `cp -r profiles/dcat-ap profiles/mi-perfil`
2. Edita `profiles/mi-perfil/1.0.0/profile.jsonld` y su `shapes.ttl`.
3. Añádelo a `profiles/manifest.json`.
4. Vuelve a levantar.

El validador lee las formas SHACL del perfil, no lleva su propia copia de las
reglas. Si aprietas una restricción, la consola empieza a rechazar por ella sin
que haya que tocar nada más.

Los términos propios cuelgan de `urn:ods:`, no de un dominio: un IRI de
vocabulario no tiene por qué resolver, y hacerlo depender de un dominio obliga
a mantenerlo vivo para que un catálogo siga validando.

## Tus casos de uso

En `seed/`. Lo que hay son dos productos de ejemplo, para que la primera
pantalla no esté vacía y para poder recorrer publicar → negociar → descargar
sin haber subido nada.

Para poner los tuyos:

1. Deja tus ficheros en `seed/data/`.
2. Descríbelos en `seed/manifest.json`, uno por producto, con su política y su
   contrato.
3. `ODS_SEED_DEMO="true"` y vuelve a levantar.

`tests/test_seed_is_shippable.py` comprueba que cada producto del manifiesto
tiene su fichero **y que el fichero está versionado**. Esa segunda parte
existe porque una regla de `.gitignore` sin anclar se llevó los de ejemplo por
delante, y el nodo publicaba dos productos cuya descarga daba 404: peor que no
publicar ninguno, porque parece que funciona.

Para no publicar ninguno: `ODS_SEED_DEMO="false"`.

## Los nodos con los que te federas

Se dan de alta por la API —`POST /api/v1/nodes` con `label` y `baseUrl`—, y
su oferta entra en tu catálogo consolidado en la siguiente sincronización, o al
momento con `POST /api/v1/nodes/sync`. El procedimiento completo, con el token
y las direcciones, está en `docs/dos-nodos.md`.

La pestaña **Nodos conocidos** de la consola no se ofrece en esta entrega. El
panel y todo lo que hay detrás siguen escritos y probados; lo único que falta
es el botón que lleva a él.

Lo único que hace falta del otro lado es que su `/api/v1/catalog` conteste, lo
cual es cierto de cualquier nodo de este producto sin que su administrador
tenga que hacer nada. Ni credenciales cruzadas, ni acuerdos previos, ni abrir
la administración de su conector.

Ver [dos-nodos.md](dos-nodos.md).

## El idioma

`ODS_LANG="es"` o `"en"`. Determina a qué versión de cada página va quien
entra sin elegir; el selector de la esquina sigue funcionando en las dos.

Las páginas son `*.html` y `*-en.html`. Para añadir un tercer idioma hay que
tocar plantillas — eso todavía no es «copiar una carpeta», y está anotado como
limitación.

## Qué NO se personaliza sin tocar código

Dicho aquí para que nadie lo descubra a mitad de una migración:

- **Un tercer idioma.** Hay dos, y añadir otro pasa por las plantillas.
- **El flujo de negociación.** Es el del conector; cambiarlo es cambiar el
  conector.
- **Más de un conector por nodo.** Esta versión entrega uno, proveedor y
  consumidor a la vez. Para varios, se instalan varios nodos y se federan —
  que además es lo que la federación hace bien.
- **La estructura de la consola.** Sus pestañas son fijas.
- **El proveedor de identidad.** Es Keycloak. Su realm se importa y se puede
  editar, pero sustituirlo por otro no está previsto.
