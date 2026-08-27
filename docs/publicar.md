# Publicar una versión

## Cómo se corta

Etiquetar. Nada más:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Eso dispara `.github/workflows/release.yml`, que hace cuatro cosas **en este
orden y sin saltarse ninguna**:

1. Ejecuta la puerta de calidad entera —`tests.yml`, incluido el recorrido
   completo contra un nodo levantado de verdad—.
2. Construye y sube las tres imágenes, para Intel y ARM, firmadas y con su
   inventario de componentes.
3. Analiza vulnerabilidades y guarda el informe.
4. Crea la publicación con sus notas.

**Si el recorrido completo falla, no hay versión.** Eso no es una frase: el
trabajo que construye declara `needs: pruebas`, así que un rojo impide que se
suba una sola imagen. `tests/test_release_gate.py` vigila que siga siendo
cierto, porque se rompe de maneras que no dan error —un `continue-on-error`
puesto un viernes para desatascar una publicación, un `if: always()`, quitar el
`needs`— y cada una deja el flujo verde publicando algo que no ha pasado por
la puerta.

## Las tres imágenes

| Imagen | Para qué |
|---|---|
| `myopendataspace/my-open-dataspace` | Todo-en-uno, evaluación y docencia. Es la que enlaza el README. |
| `myopendataspace/app` | Portal, consola, API y federador. Para la composición. |
| `myopendataspace/connector` | El conector EDC. Para la composición. |

Las tres, además, en GitHub Container Registry con el mismo nombre bajo
`ghcr.io/nekosphera/`.

**Etiquetas.** Cada versión sale con cuatro: `1.2.3`, `1.2`, `1` y `latest`.
Quien quiera reproducibilidad fija la completa; quien quiera parches
automáticos y ninguna sorpresa fija la menor.

## Verificar una imagen antes de usarla

Las imágenes se firman con la identidad del propio flujo de trabajo —sin
claves que guardar ni que rotar—, así que se puede comprobar de qué
repositorio y de qué flujo salió cada una:

```bash
cosign verify \
  --certificate-identity-regexp 'https://github.com/nekosphera/my-open-dataspace/.*' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  ghcr.io/nekosphera/app:0.1.0
```

Y su procedencia e inventario:

```bash
gh attestation verify oci://ghcr.io/nekosphera/app:0.1.0 --owner nekosphera
```

## La imagen todo-en-uno

```bash
docker run -p 8080:8080 myopendataspace/my-open-dataspace
```

Portal, conector, PostgreSQL y Fuseki en un contenedor. **Sin proveedor de
identidad, sin TLS y sin autenticación**: cualquiera que alcance el puerto
puede publicar, negociar y descargar. Lo dice al arrancar, con un cartel que
ocupa media pantalla, y no se puede quitar por descuido: el modo de evaluación
se apaga solo si detecta una identidad o un dominio configurados, porque tener
las dos cosas a la vez significa que alguien lo ha heredado de una plantilla
sin darse cuenta.

Es lo que un contenedor no debería hacer —cuatro procesos, sin reinicio por
proceso, un fallo de cualquiera se lleva el contenedor— y por eso existe sólo
para evaluación. La composición de seis contenedores es la que se instala.

## Qué hace falta configurar en GitHub

Para GHCR, nada: el flujo usa el testigo que GitHub ya le da.

Para Docker Hub, dos secretos en el repositorio:

- `DOCKERHUB_USUARIO`
- `DOCKERHUB_TOKEN` — un testigo de acceso, no la contraseña de la cuenta.

**Sin ellos el flujo no falla**: sube sólo a GHCR y sigue. Es deliberado, para
que quien bifurque el repositorio pueda cortar sus propias versiones sin tener
credenciales que no son suyas.

## El análisis de vulnerabilidades no bloquea

Se ejecuta en cada versión y su informe se guarda como artefacto, pero no
rompe la publicación. Una vulnerabilidad conocida en una dependencia de la
imagen base aparece a diario, y bloquear cada versión por eso lleva —siempre—
a que alguien desactive el análisis. Un informe que se mira vale más que una
puerta que se acaba quitando.

Lo que sí bloquea es el recorrido completo, porque eso sí depende del código
de este repositorio.
