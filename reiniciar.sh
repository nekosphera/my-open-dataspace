#!/usr/bin/env bash
# Recuperar un nodo al que ya no puedes entrar.
#
#     ./reiniciar.sh --contrasena <correo>   la contraseña de alguien
#     ./reiniciar.sh --asistente             volver a /setup, sin perder datos
#     ./reiniciar.sh --todo                  borrarlo todo y empezar de cero
#
# Esto sólo lleva a deploy/reiniciar.sh, que es donde está el guion de verdad.
# Está aquí porque se instala con `./install.sh` desde la raíz, así que es aquí
# donde se busca cuando algo va mal, y encontrarse un «No such file or
# directory» cuando ya no puedes entrar en tu nodo es el peor momento posible.
set -euo pipefail

exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/deploy/reiniciar.sh" "$@"
