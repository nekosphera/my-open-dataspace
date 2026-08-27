# -*- coding: utf-8 -*-
"""El realm tiene que poder importarse, o el nodo no arranca.

Keycloak rechaza cualquier campo que no conozca —«Unrecognized field, not
marked as ignorable»— y **se niega a arrancar entero**. No importa el realm a
medias ni avisa: se cae en bucle, y desde fuera lo único que se ve es un 502
en `/auth` y un contenedor reiniciando.

Lo escribo después de meter un `"_comentario"` en el cliente de la consola
para explicar por qué sus URLs las fija el arranque. Un JSON no admite
comentarios, y ése en concreto tumbó el nodo.

Se comprueba contra la lista de campos que Keycloak dice conocer cuando falla,
que es la fuente más fiable que hay sin levantar un Keycloak.
"""
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
REALM = RAIZ / "deploy" / "keycloak" / "dataspace-realm.json"

# Los 44 que Keycloak enumera al rechazar uno desconocido.
CAMPOS_DE_CLIENTE = {
    "access", "adminUrl", "alwaysDisplayInConsole", "attributes",
    "authenticationFlowBindingOverrides", "authorizationServicesEnabled",
    "authorizationSettings", "baseUrl", "bearerOnly", "clientAuthenticatorType",
    "clientId", "clientTemplate", "consentRequired", "defaultClientScopes",
    "defaultRoles", "description", "directAccessGrantsEnabled",
    "directGrantsOnly", "enabled", "frontchannelLogout", "fullScopeAllowed",
    "id", "implicitFlowEnabled", "name", "nodeReRegistrationTimeout",
    "notBefore", "optionalClientScopes", "origin", "protocol",
    "protocolMappers", "publicClient", "redirectUris", "registeredNodes",
    "registrationAccessToken", "rootUrl", "secret", "serviceAccountsEnabled",
    "standardFlowEnabled", "surrogateAuthRequired", "type",
    "useTemplateConfig", "useTemplateMappers", "useTemplateScope", "webOrigins",
}

CAMPOS_DE_REALM = {
    "realm", "enabled", "displayName", "displayNameHtml", "registrationAllowed",
    "registrationEmailAsUsername", "resetPasswordAllowed", "loginWithEmailAllowed",
    "duplicateEmailsAllowed", "verifyEmail", "editUsernameAllowed", "sslRequired",
    "accessTokenLifespan", "ssoSessionIdleTimeout", "ssoSessionMaxLifespan",
    "roles", "groups", "defaultGroups", "clients", "users", "smtpServer",
    "browserSecurityHeaders", "attributes", "identityProviders",
    "clientScopes", "defaultDefaultClientScopes", "requiredActions",
    "passwordPolicy", "internationalizationEnabled", "supportedLocales",
    "defaultLocale", "eventsEnabled", "adminEventsEnabled",
}


def realm():
    return json.loads(REALM.read_text(encoding="utf-8"))


def test_el_realm_es_json_valido():
    assert REALM.is_file(), "falta el realm que se importa en el arranque"
    realm()


def test_ningun_campo_de_adorno_en_el_realm():
    """Un JSON no admite comentarios, y Keycloak rechaza lo que no conoce."""
    desconocidos = sorted(set(realm()) - CAMPOS_DE_REALM)
    assert not desconocidos, (
        "campos que Keycloak no reconoce en la raíz del realm: "
        + ", ".join(desconocidos)
        + ". Rechazarlos no importa el realm a medias: Keycloak no arranca."
    )


@pytest.mark.parametrize(
    "cliente", realm().get("clients", []), ids=lambda c: c["clientId"]
)
def test_ningun_campo_de_adorno_en_los_clientes(cliente):
    desconocidos = sorted(set(cliente) - CAMPOS_DE_CLIENTE)
    assert not desconocidos, (
        f"{cliente['clientId']}: campos que Keycloak no reconoce: "
        + ", ".join(desconocidos)
        + ". Si querías dejar una explicación, va en el código que lo usa, no "
        "dentro del JSON."
    )


def test_la_consola_declara_a_donde_puede_volver():
    """Destinos explícitos, no relativos.

    Con `redirectUris: ["/*"]` y sin `rootUrl` esto **funciona** mientras la
    identidad y el portal compartan origen, que es lo que hace la composición
    detrás de Caddy. Lo comprobé contra un nodo vivo: Keycloak acepta la
    vuelta a `/login.html`.

    Se declara explícito de todas formas, porque deja de funcionar en cuanto
    alguien separa los orígenes con `ODS_AUTH_URL` —y entonces el síntoma es
    un «No se pudo completar el login» que no se parece a su causa—.
    """
    consola = next(c for c in realm()["clients"] if c["clientId"] == "dataspace-ui")
    assert consola.get("rootUrl"), (
        "el cliente de la consola no declara rootUrl: sus destinos vuelven a "
        "ser relativos y dependen de que la identidad comparta origen con el "
        "portal, que es una suposición que ODS_AUTH_URL puede romper"
    )
    destinos = consola.get("redirectUris") or []
    assert any(d.startswith("http") for d in destinos), (
        f"ningún destino absoluto en redirectUris: {destinos}"
    )


def test_el_arranque_ajusta_las_urls_a_la_direccion_publica():
    """El realm es estático y la dirección pública la elige quien instala."""
    api = (RAIZ / "app" / "onboarding_api.py").read_text(encoding="utf-8")
    assert "def ensure_console_client_urls(" in api, (
        "nadie ajusta las URLs del cliente a ODS_PUBLIC_URL, así que el realm "
        "sólo vale para una instalación en localhost"
    )
    inicio = api.index("def run_startup_repairs():")
    fin = api.index("\n\n\ndef ", inicio)
    assert "ensure_console_client_urls()" in api[inicio:fin], (
        "ensure_console_client_urls existe pero no la llama el arranque"
    )


def test_la_cuenta_de_servicio_del_conector_trae_sus_roles():
    """O hay que asignarlos a mano en la consola de Keycloak."""
    usuarios = realm().get("users", [])
    servicio = [u for u in usuarios if u.get("serviceAccountClientId")]
    assert servicio, "el realm no trae la cuenta de servicio del conector"
    roles = set(servicio[0].get("realmRoles") or [])
    assert {"dataspace-user", "dataspace-negotiator", "dataspace-admin"} <= roles, (
        f"le faltan roles a la cuenta de servicio: {sorted(roles)}"
    )
