-- Una sola base para todo el nodo, con un esquema por consumidor.
--
-- PostgreSQL crea `dataspace` desde POSTGRES_DB; lo que falta es la de
-- Keycloak, que necesita la suya propia: comparte instancia pero no esquema,
-- y mezclar sus tablas con las del conector hace imposible respaldar o
-- restaurar una sin la otra.
CREATE DATABASE keycloak OWNER dataspace;
