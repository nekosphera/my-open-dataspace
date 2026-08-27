# Antes de pulsar «público»

La lista de la sección 14, punto por punto, con quién la comprueba.

> **Publicado el 2026-08-27** en
> [github.com/nekosphera/my-open-dataspace](https://github.com/nekosphera/my-open-dataspace):
> un commit, 108 ficheros, público.
>
> Lo que esta lista comprobaba antes de empujar se comprueba igual después:
> las mismas pruebas corren en cada cambio, y la que exigía que no hubiera
> remoto ahora exige que el único que haya sea el de destino. Un remoto
> añadido para una prueba y olvidado publica el trabajo en el repositorio de
> otro.

## Lo que ya está comprobado

Cada línea la sostiene una prueba que corre en la puerta de calidad, no un
repaso a ojo. `tests/test_ready_to_publish.py`, salvo donde se indica otra.

| Punto de la sección 14 | Estado | Quién lo sostiene |
|---|---|---|
| Barrido automático de secretos, con su resultado guardado | ✅ | `.secrets.baseline` + `test_secret_scan.py` |
| Prueba de «sin dependencias ocultas» en verde | ✅ | `test_no_hidden_dependencies.py` |
| `docs/procedencia.md` completo, con repositorio y commit | ✅ | `test_ready_to_publish.py` |
| Ni una IP, dominio, ruta de servidor ni correo real | ✅ | `test_no_hidden_dependencies.py` |
| Ni rastro de la marca de origen en el código | ✅ | `test_no_hidden_dependencies.py` |
| Licencia y atribuciones en su sitio | ✅ | |
| README con los tres caminos de instalación | ✅ | |
| Política de seguridad con canal **y plazos concretos** | ✅ | |
| Guía de contribución y código de conducta | ✅ | |
| Plantillas de incidencia | ✅ | |
| Aviso de alcance literal y visible en el README | ✅ | |
| README con captura | ✅ | |
| Ningún commit heredado de los repositorios de origen | ✅ | |
| Ningún enlace del portal lleva a una página que no existe | ✅ | `test_the_portal_is_the_product.py` |
| Ninguna página habla de la vertical podada | ✅ | `test_the_portal_is_the_product.py` |

### El barrido de secretos

9 hallazgos, **los 9 falsos positivos**, cada uno explicado en
[secretos.md](secretos.md). Son etiquetas de interfaz que llevan la palabra
«password» y contraseñas de prueba que sólo se le dan a un validador para que
las rechace.

**Lo que sí encontró y se corrigió:** el recorrido completo creaba el
administrador con una contraseña escrita en el fichero. Contra un nodo de usar
y tirar da igual; contra el nodo de alguien que lo ejecutó «para ver si
funciona» y luego se lo quedó, no. Ahora se genera una distinta en cada
ejecución y no se imprime.

## La captura — hecha, y lo que enseñó

Se toma con `./deploy/capturas.sh` contra un nodo levantado y configurado como
«Organización de Ejemplo». Usa Chrome o Edge en modo headless: no hace falta
instalar nada, si has llegado hasta aquí tienes un navegador. Y se niega a
capturar un nodo que todavía no ha pasado por el asistente, porque entonces
todas las páginas redirigen a `/setup` y las tres capturas saldrían iguales.

**Lo que la captura enseñó, y ninguna prueba había visto:** el portal público
seguía siendo, entero, el del despliegue de origen. «Espacio de datos de salud
urbana», «indicadores sintéticos de calidad ambiental, confort, afluencia,
energía, incendios y radiación electromagnética», y dos botones grandes que
llevaban a páginas que la poda había borrado. Y la tabla del catálogo decía
«No se encontraron productos de datos federados» en un nodo que tenía dos
publicados, porque leía de un servicio de gobernanza externo que este producto
no tiene.

La poda miró el código —imports, rutas, dependencias— y no miró la prosa. El
barrido de términos prohibidos buscaba `ehds`, `fhir`, `healthdcat`: ninguno
aparece en un párrafo escrito en castellano sobre salud urbana.

Está corregido —portal reescrito, catálogo leyendo de los nodos de verdad— y
lo vigilan ahora `tests/test_the_portal_is_the_product.py`, que comprueba dos
cosas que no se habían comprobado nunca: que **ningún enlace lleva a una
página que no existe**, y que **ninguna página habla de la vertical podada**.

Es exactamente para esto para lo que la sección 14 pide una captura.

## Lo que falta, y no lo puedo cerrar yo

### 1. La instalación probada por alguien que no sea el autor

La sección 14 pide que alguien que no ha visto el código instale esto en una
máquina limpia siguiendo **sólo el README**, y esto es lo que yo puedo decir
con honestidad:

- El recorrido completo pasa —**14 comprobaciones**— contra la composición y
  contra la imagen todo-en-uno.
- La instalación de cero está cronometrada: **53 segundos** de `./install.sh`
  a producto de datos publicado.
- Pero lo he probado yo, que escribí el código. **Eso no es lo que la sección
  14 pide, y no puede darse por equivalente.** Lo que una prueba propia no
  detecta nunca es el paso que uno da sin pensar porque sabe cómo funciona.

Falta que lo haga otra persona.

### 2. Volver a cronometrar cuando las imágenes estén publicadas

Los 53 segundos son con las imágenes ya construidas en local. El recorrido que
describe el README empieza por descargarlas, y ese todavía no se ha medido.

## El historial — hecho

`docs/decisiones.md` D-001: commits por fase durante el desarrollo, un único
commit inicial al publicar.

**`main` tiene un solo commit, y es el commit raíz.** Se comprueba así:

```bash
git rev-list --max-parents=0 HEAD    # tiene que dar el mismo sha que HEAD
```

**La historia de trabajo no se ha perdido: está en la rama local
`historia-de-trabajo`, con sus 22 commits.** No se empuja. Sus mensajes
documentan por qué cada cosa está como está —los seis fallos que sólo se ven
arrancando, las tres opciones que estaban declaradas y no hacían nada, los
cuatro de la imagen todo-en-uno, el `.gitignore` que se llevó los datos de
ejemplo por delante— y eso no vuelve a escribirse.

El aplastado no cambió ni un byte del contenido: el árbol es el mismo objeto
antes y después, `00bb8c08`. Si alguna vez hace falta rehacerlo:

```bash
git checkout historia-de-trabajo
git branch historia-de-trabajo-2
git checkout --orphan publicacion
git add -A && git commit
git branch -M publicacion main
```

### Lo que queda por hacer se mete **dentro** de ese commit

La captura del README y lo que salga de la instalación por otra persona son
cambios que todavía faltan. Si se añaden como commits nuevos, `main` deja de
tener uno solo y la propiedad se pierde sin que nadie lo note.

```bash
git add -A
git commit --amend --no-edit
```

Y si el cambio merece contarse, `historia-de-trabajo` es donde se cuenta.

## El orden

| | Paso | Estado |
|---|---|---|
| 1 | La captura del README | ✅ hecha |
| 2 | Aplastar el historial | ✅ hecho |
| 3 | Configurar el remoto y empujar | ✅ **hecho el 2026-08-27** |
| 4 | Cortar `v0.1.0` | ⬜ publica las imágenes |
| 5 | Que alguien más instale desde cero siguiendo sólo el README | ⬜ lo hace Francisco desde otra máquina |

El paso 5 se hace ahora contra el repositorio publicado, que es la prueba de
verdad: clonar de GitHub y seguir el README, sin nada de esta máquina.

Los pasos 4 y 5 publican, y el 4 no tiene vuelta atrás: el repositorio de
destino ya es público. Antes de ellos, esta lista tiene que estar entera en
verde — incluidos los dos puntos que yo no puedo cerrar.
