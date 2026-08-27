#!/bin/sh
# Decide en que direccion escucha Caddy antes de arrancarlo.
#
# Son tres casos y la composicion no sabe ramificar:
#
#   sin dominio            -> :80            HTTP simple, modo de evaluacion
#   dominio + ODS_TLS=auto -> <dominio>      Caddy pide el certificado y renueva
#   dominio + ODS_TLS=off  -> http://<dom>   HTTP simple con dominio; el esquema
#                                            explicito es lo que impide que
#                                            Caddy intente ACME
#
# Sin esto, ODS_TLS estaba declarado en .env.example y no lo leia nadie: poner
# "off" con un dominio seguia pidiendo certificado, que es exactamente el tipo
# de opcion que miente.
set -eu

dominio="${ODS_DOMAIN:-}"
tls="${ODS_TLS:-auto}"

if [ -z "${dominio}" ]; then
  ODS_SITE_ADDRESS=":80"
elif [ "${tls}" = "off" ]; then
  ODS_SITE_ADDRESS="http://${dominio}"
else
  ODS_SITE_ADDRESS="${dominio}"
fi
export ODS_SITE_ADDRESS

echo "[caddy] sirviendo en ${ODS_SITE_ADDRESS} (ODS_TLS=${tls})"
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile "$@"
