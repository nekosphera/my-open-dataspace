#!/usr/bin/env bash
# Recuperar un nodo al que ya no puedes entrar.
#
#     ./deploy/reiniciar.sh --contrasena <correo>   la contraseña de alguien
#     ./deploy/reiniciar.sh --asistente             volver a /setup, sin perder datos
#     ./deploy/reiniciar.sh --todo                  borrarlo todo y empezar de cero
#
# Tres niveles, del que menos destruye al que más. Empieza por el primero: casi
# siempre el problema es que nadie recuerda la contraseña, y para eso no hace
# falta tirar un nodo entero.
#
# Esto es la «orden explícita en la línea de comandos» que la especificación
# pide para reconfigurar: `/setup` devuelve 404 en cuanto el nodo está
# configurado, y sin esto no había forma de volver a abrirlo.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${RAIZ}"

if [[ -t 1 ]]; then
  NEGRITA=$'\e[1m'; ROJO=$'\e[31m'; FIN=$'\e[0m'
else
  NEGRITA=''; ROJO=''; FIN=''
fi

# El camino que se ha escrito para llegar hasta aquí, para que la ayuda no
# mande a uno distinto del que funciona desde donde está la persona. Decía
# siempre `./deploy/reiniciar.sh`, que desde dentro de `deploy/` no existe.
YO="${0}"
[[ "${YO}" == /* ]] && YO="./$(basename "${YO}")"

uso() {
  cat <<AYUDA
Recuperar un nodo al que ya no puedes entrar.

  ${YO} --contrasena <correo>
      Le pone una contraseña nueva a esa cuenta. No toca nada más.
      Empieza por aquí.

  ${YO} --asistente
      Vuelve a abrir /setup para elegir organización y administrador otra vez.
      Conserva lo publicado, los participantes y el registro de operaciones.

  ${YO} --todo
      Borra los volúmenes y empieza de cero. Se pierde todo: base de datos,
      identidades, catálogo y ficheros publicados.

  --sin-preguntas   no pide confirmación (para guiones)
AYUDA
}

confirmar() {
  local aviso="$1"
  if [[ "${SIN_PREGUNTAS}" == "true" ]]; then
    return 0
  fi
  if [[ ! -t 0 ]]; then
    echo "Sin terminal para confirmar. Usa --sin-preguntas si estás seguro." >&2
    exit 1
  fi
  printf '%s%s%s\n' "${ROJO}" "${aviso}" "${FIN}"
  read -r -p "Escribe SI para continuar: " respuesta
  [[ "${respuesta}" == "SI" ]] || { echo "Cancelado."; exit 1; }
}

# --- Argumentos -----------------------------------------------------------
ACCION=""
CORREO=""
SIN_PREGUNTAS=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --contrasena) ACCION="contrasena"; CORREO="${2:-}"; shift 2 ;;
    --asistente)  ACCION="asistente";  shift ;;
    --todo)       ACCION="todo";       shift ;;
    --sin-preguntas) SIN_PREGUNTAS=true; shift ;;
    -h|--help)    uso; exit 0 ;;
    *) echo "No entiendo «$1»." >&2; uso >&2; exit 1 ;;
  esac
done

# Sin acción, la ayuda **y** el motivo. Antes sólo salía la ayuda, y quien la
# leía se quedaba pensando que el guion había corrido y no había hecho nada.
if [[ -z "${ACCION}" ]]; then
  uso
  echo >&2
  echo "No has dicho qué hacer. Elige una de las tres de arriba." >&2
  exit 2
fi

# --- La contraseña de una cuenta -----------------------------------------
if [[ "${ACCION}" == "contrasena" ]]; then
  [[ -n "${CORREO}" ]] || { echo "Dime de qué cuenta: --contrasena <correo>" >&2; exit 1; }

  if [[ -t 0 ]]; then
    read -r -s -p "Contraseña nueva para ${CORREO}: " NUEVA; echo
    read -r -s -p "Otra vez: " REPETIDA; echo
    [[ "${NUEVA}" == "${REPETIDA}" ]] || { echo "No coinciden." >&2; exit 1; }
  else
    NUEVA="${ODS_NUEVA_CONTRASENA:-}"
    [[ -n "${NUEVA}" ]] || { echo "Sin terminal: pásala en ODS_NUEVA_CONTRASENA." >&2; exit 1; }
  fi

  # El mismo perfil que exige el asistente, comprobado aquí para que el fallo
  # salga ahora y no cuando alguien intente entrar.
  if ! printf '%s' "${NUEVA}" | grep -qE '^(?=.*[A-Z])(?=.*[0-9]).{9,}$' 2>/dev/null; then
    if [[ ${#NUEVA} -lt 9 ]]; then
      echo "Demasiado corta: nueve caracteres o más." >&2
      exit 1
    fi
  fi

  echo "Cambiando la contraseña de ${CORREO}…"
  ODS_RESET_EMAIL="${CORREO}" ODS_RESET_PASSWORD="${NUEVA}" \
    docker compose exec -T \
      -e ODS_RESET_EMAIL -e ODS_RESET_PASSWORD \
      app python app/tools/reset_password.py
  echo "Hecho. Entra en /login.html con esa cuenta."
  exit 0
fi

# --- Volver a abrir el asistente -----------------------------------------
if [[ "${ACCION}" == "asistente" ]]; then
  confirmar "Se va a reabrir /setup. Lo publicado y el registro se conservan, pero elegirás organización y administrador otra vez."
  echo "Reabriendo el asistente…"

  # El marcador es lo único que decide si /setup existe. Borrarlo es
  # exactamente «reconfigurar», y por eso vive en el volumen y no en el árbol.
  #
  # Las rutas van dentro del `sh -c`: como argumentos sueltos, Git Bash en
  # Windows las convierte en rutas de Windows antes de que Docker las vea, y
  # entonces el `rm -f` borra un fichero que no existe **y sale con éxito**.
  docker compose exec -T app sh -c 'rm -f /var/lib/ods/setup-complete.json /var/lib/ods/site.json'

  # Y se comprueba. `rm -f` no se queja nunca, así que sin esto el guion diría
  # «Hecho» con el asistente todavía cerrado.
  if docker compose exec -T app sh -c 'test -f /var/lib/ods/setup-complete.json'; then
    echo "No se pudo borrar el marcador de configuración." >&2
    echo "Mira qué hay:  docker compose exec app sh -c 'ls -la /var/lib/ods'" >&2
    exit 1
  fi

  docker compose restart app >/dev/null
  echo "Hecho. Abre /setup y responde otra vez las cuatro preguntas."
  exit 0
fi

# --- Borrarlo todo --------------------------------------------------------
if [[ "${ACCION}" == "todo" ]]; then
  confirmar "$(cat <<'AVISO'
Esto BORRA los volúmenes del nodo:
  - la base de datos, con los activos, políticas y contratos
  - Keycloak, con todas las cuentas
  - el catálogo consolidado
  - los ficheros publicados y el registro de operaciones

No hay vuelta atrás. Si quieres una copia antes: ./deploy/backup.sh
AVISO
)"
  echo "Borrando…"
  docker compose down -v

  # Y los conectores de los participantes, que Compose no conoce.
  #
  # Los levanta el nodo a demanda, así que no están en la composición y
  # `down -v` los deja en pie —apuntando a una base de datos que acaba de
  # desaparecer—. Se reconocen por su etiqueta y no por su nombre: es lo que
  # garantiza que no se toca ningún otro contenedor de la máquina.
  sueltos="$(docker ps -aq --filter 'label=org.myopendataspace.connector=true' 2>/dev/null || true)"
  if [[ -n "${sueltos}" ]]; then
    echo "Retirando los conectores de los participantes…"
    docker rm -f ${sueltos} >/dev/null
  fi

  echo "Levantando de nuevo…"
  docker compose up -d --build
  PUERTO="$(sed -n 's/^ODS_HTTP_PORT=//p' .env 2>/dev/null | tr -d '"' | head -1)"
  echo
  echo "${NEGRITA}Listo.${FIN} Abre http://localhost:${PUERTO:-8080}/setup"
  exit 0
fi
