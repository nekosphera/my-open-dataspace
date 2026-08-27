#!/usr/bin/env bash
# Arranque de la aplicacion.
#
# Genera la configuracion de interfaz a partir del entorno y despues cede el
# proceso a la API. El generador va primero porque la interfaz sirve
# runtime-config.js en la primera peticion: generarlo despues deja la
# primera carga sin marca.
set -euo pipefail

python app/tools/render_ui_runtime_config.py --env-file /srv/ods/.env || {
  echo "[ods] AVISO no se pudo generar runtime-config.js; se sirve con los valores por omision"
}

exec python app/onboarding_api.py "$@"
