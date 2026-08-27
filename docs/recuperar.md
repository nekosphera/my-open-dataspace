# No puedo entrar en mi nodo

> Se ejecuta desde la raíz del repositorio, donde ejecutaste `./install.sh`.
> También está en `deploy/reiniciar.sh`: el de la raíz sólo lleva a aquél.
> Sin decirle qué hacer imprime esta lista y sale con error, no en silencio.
>
> **En PowerShell usa `.einiciar.ps1`**, con los mismos argumentos.
> `.einiciar.sh` ahí no ejecuta nada y no dice nada: PowerShell no corre
> ficheros `.sh`. En Git Bash, en Linux y en macOS, `./reiniciar.sh`.

Tres salidas, de la que menos destruye a la que más. **Empieza por la
primera**: casi siempre el problema es una contraseña, y para eso no hace falta
tirar un nodo entero.

Todas se ejecutan desde la carpeta del repositorio, con el nodo levantado
—salvo la última, que lo levanta ella—.

## 1. No recuerdo la contraseña

```bash
./reiniciar.sh --contrasena admin@tu-organizacion.example
```

Pide una contraseña nueva y la cambia. No toca nada más: ni lo publicado, ni
los participantes, ni el registro.

Si no sabes con qué correo se configuró el nodo, ejecútalo con cualquiera: te
dirá qué cuentas hay.

Y si la cuenta estaba deshabilitada, la vuelve a habilitar — una contraseña
nueva sobre una cuenta deshabilitada es el peor resultado posible, porque
parece que ha funcionado.

## 2. Quiero configurarlo otra vez desde el principio

```bash
./reiniciar.sh --asistente
```

Reabre `/setup` para elegir organización, administrador, idioma y marca otra
vez. **Conserva** los activos publicados, sus políticas y contratos, los
participantes y el registro de operaciones.

Esto es la «orden explícita en la línea de comandos» de la que habla la
especificación: `/setup` devuelve 404 en cuanto el nodo está configurado, y no
puede reabrirse desde la web. Si se pudiera, cualquiera que alcanzara el nodo
se nombraría administrador.

## 3. Quiero empezar de cero

```bash
./reiniciar.sh --todo
```

Borra los volúmenes y vuelve a levantar. **Se pierde todo**: la base de datos
con activos, políticas y contratos, Keycloak con todas las cuentas, el catálogo
consolidado, los ficheros publicados y el registro.

Pide confirmación escribiendo `SI`. Si quieres una copia antes:
`./deploy/backup.sh`.

A mano es lo mismo:

```bash
docker compose down -v
docker compose up -d --build
```

## Antes de nada: mira qué pasa

```bash
./deploy/diagnostico.sh > diagnostico.txt
```

Muchas veces no hay que recuperar nada. Dos causas frecuentes, las dos con el
mismo síntoma —«no puedo entrar»— y ninguna arreglable borrando datos:

- **Un contenedor reiniciando en bucle.** Se ve «Up» un segundo de cada tres y
  en un `docker compose ps` normal parece sano. La columna de reinicios del
  diagnóstico lo delata.
- **Cambiaste `ODS_DB_PASSWORD` en `.env` después de instalar.** PostgreSQL
  sólo fija la contraseña al crear su base: el conector deja de poder entrar y
  se queda reiniciando. Está avisado en `.env.example`, con el `ALTER USER` que
  sí la cambia.

## Sobre la imagen todo-en-uno

Si la lanzaste con `docker run` **sin** `-v`, no hay nada que recuperar:
Docker le dio un volumen anónimo y al borrar el contenedor se fue con él.
Vuelve a lanzarla con un volumen con nombre y no volverá a pasar:

```bash
docker run -p 8080:8080 -v ods-datos:/var/lib/ods \
  ghcr.io/nekosphera/my-open-dataspace:0.1.0
```
