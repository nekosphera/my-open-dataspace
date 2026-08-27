# Barrido de secretos

**Herramienta:** [detect-secrets](https://github.com/Yelp/detect-secrets) 1.5.0
**Alcance:** los ficheros versionados. No el árbol de trabajo: lo que importa
es lo que se publicaría, y un `.env` local o un `.pytest_cache` no se publican.

Fuera del barrido quedan dos, y por la misma razón: **existen para hablar del
barrido, así que barrerlos duplica cada hallazgo.** La línea base guarda los
hashes —encontrarlos ahí los declararía hallazgos nuevos, y cada regeneración
produciría una línea base distinta de la anterior, indefinidamente— y esta
misma página cita el código que explica. No se esconde nada: lo que citan está
barrido en su fichero de origen, que es donde importa.

```bash
python -m detect_secrets scan \
  $(git ls-files \
      | grep -v -e '\.secrets\.baseline' -e 'revision/secretos\.md') \
  > .secrets.baseline
```

**Resultado: 9 hallazgos, los 9 falsos positivos.** Cada uno, con por qué:

## `app/ui/setup.html` — 4

Líneas 96, 97, 106 y 117. Son las traducciones de la interfaz del asistente:

```js
l_password: "Password",
h_password: "Nine characters or more, with an upper-case letter, a digit and a symbol.",
weak_password: "The password does not meet the requirements.",
```

Etiquetas y mensajes de error. La palabra «password» junto a una cadena, que
es exactamente el patrón que la herramienta busca.

## `app/ui/registration.js` — 2

Líneas 11 y 24, lo mismo: el mensaje que se le enseña a alguien cuya
contraseña no cumple el perfil, en español y en inglés.

## `tests/test_first_run_wizard.py` — 3

Líneas 74, 76 y 77. Son los casos que el asistente **tiene que rechazar**:

```python
({"orgName": "X", "adminEmail": "a@b.org", "adminPassword": "corta"}, "weak_password"),
({"orgName": "X", "adminEmail": "a@b.org", "adminPassword": "sinmayusculas1!"}, "weak_password"),
```

No llegan a ningún sistema: la prueba carga el módulo con su estado en un
directorio temporal, sin Keycloak, y comprueba que la validación los rechaza
antes de escribir nada.

---

## Lo que el barrido sí encontró y se corrigió

**`tests/e2e/golden_path.py` creaba el administrador con una contraseña
escrita en el fichero** —`Prueba2026!`—. Contra un nodo de usar y tirar da
igual. Contra el nodo de alguien que ejecutó el recorrido «para ver si
funciona» y luego se lo quedó, no: ese nodo tiene un administrador cuya
contraseña está publicada en el repositorio.

Ahora se genera una distinta en cada ejecución y no se imprime.

## Cómo se mantiene

`.secrets.baseline` está versionado y `tests/test_secret_scan.py` lo compara
con el árbol: **falla cuando aparece un hallazgo que no está en la línea
base**. Es lo que impide que la línea base se convierta en una alfombra, que
es el destino de toda lista de excepciones que nadie mira.

Para volver a barrer después de un cambio legítimo, el comando de arriba. Y
**explicar aquí** cada hallazgo nuevo antes de darlo por bueno: una línea base
sin esta página al lado es una lista de cosas que alguien decidió ignorar sin
decir por qué.
