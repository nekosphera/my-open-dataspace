package org.eclipse.dataspace;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.reflect.TypeToken;
import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.crypto.RSASSAVerifier;
import com.nimbusds.jose.jwk.JWK;
import com.nimbusds.jose.jwk.JWKSet;
import com.nimbusds.jose.jwk.RSAKey;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.lang.reflect.Type;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.text.ParseException;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.concurrent.Executors;

/**
 * Data Space Connector service for managing data exchange
 */
public class DataSpaceConnector {
    private static final Logger logger = LoggerFactory.getLogger(DataSpaceConnector.class);
    private static final Gson GSON = new Gson();
    private static final Type MAP_TYPE = new TypeToken<Map<String, Object>>() {}.getType();
    private static final Type LIST_OF_MAP_TYPE = new TypeToken<List<Map<String, Object>>>() {}.getType();
    private static final String AUTH_INFO_KEY = "auth.info";
    private static final Duration JWKS_CACHE_TTL = Duration.ofMinutes(10);
    private static final Duration HTTP_TIMEOUT = Duration.ofSeconds(5);

    private boolean initialized = false;
    private boolean running = false;
    private HttpServer managementServer;
    private Connection dbConnection;
    private JWKSet cachedJwkSet;
    private Instant jwksLoadedAt = Instant.EPOCH;

    private final int managementPort = Integer.parseInt(System.getenv().getOrDefault("MANAGEMENT_PORT", "8080"));
    private final String managementPath = System.getenv().getOrDefault("MANAGEMENT_PATH", "/management");
    private final String keycloakIssuerUrl = System.getenv().getOrDefault("KEYCLOAK_ISSUER_URL", "").trim();
    // Sin valor por omision util: el que habia nombraba un servicio del
    // despliegue del que sale este codigo -- identity-hub -- que no existe
    // aqui, de modo que la verificacion de firma fallaba en cada peticion y
    // el conector contestaba 401 sin decir por que. La composicion lo pasa.
    private final String keycloakJwksUrl = System.getenv().getOrDefault("KEYCLOAK_JWKS_URL", "").trim();
    private final String keycloakAudience = System.getenv().getOrDefault("KEYCLOAK_AUDIENCE", "").trim();
    // Modo de evaluacion: sin proveedor de identidad, todo el mundo entra.
    //
    // Existe para la imagen todo-en-uno, que se arranca con un `docker run` y
    // no lleva Keycloak dentro. Es un interruptor de seguridad, asi que:
    //
    //   - se activa solo con la variable puesta a "true", nunca por omision;
    //   - se apaga solo si hay una identidad configurada, porque tener las dos
    //     cosas a la vez significa que alguien lo ha heredado sin querer de
    //     una plantilla de evaluacion;
    //   - se anuncia en el arranque y en cada peticion aceptada por el.
    private final boolean evaluationMode =
            "true".equalsIgnoreCase(System.getenv().getOrDefault("EDC_EVALUATION_MODE", "").trim())
            && System.getenv().getOrDefault("KEYCLOAK_JWKS_URL", "").trim().isEmpty();
    private final boolean rbacEnabled = Boolean.parseBoolean(System.getenv().getOrDefault("EDC_RBAC_ENABLED", "true"));
    private final List<String> rbacReadRoles = parseRoles(System.getenv().getOrDefault("EDC_RBAC_READ_ROLES", "dataspace-user,dataspace-admin"));
    private final List<String> rbacWriteRoles = parseRoles(System.getenv().getOrDefault("EDC_RBAC_WRITE_ROLES", "dataspace-admin"));
    private final List<String> rbacNegotiationRoles = parseRoles(System.getenv().getOrDefault("EDC_RBAC_NEGOTIATION_ROLES", "dataspace-negotiator,dataspace-admin"));
    private final List<String> auditMasterUsers = parseRoles(System.getenv().getOrDefault("EDC_AUDIT_MASTER_USERS", ""));
    private final List<String> downloadAllowedHosts = parseRoles(System.getenv().getOrDefault("EDC_DOWNLOAD_ALLOWED_HOSTS", "localhost"));
    private final int downloadMaxBytes = parsePositiveInt(System.getenv("EDC_DOWNLOAD_MAX_BYTES"), 50 * 1024 * 1024);
    private final String downloadInternalKey = System.getenv().getOrDefault("EDC_DOWNLOAD_INTERNAL_KEY", "").trim();
    private final boolean requireWalletIdentity = Boolean.parseBoolean(System.getenv().getOrDefault("EDC_REQUIRE_WALLET_IDENTITY", "false"));
    private final String walletDidClaim = System.getenv().getOrDefault("EDC_WALLET_DID_CLAIM", "wallet_did");
    private final String vaultAddress = System.getenv().getOrDefault("VAULT_ADDR", "").trim();
    private final String vaultToken = System.getenv().getOrDefault("VAULT_TOKEN", "").trim();
    private final String vaultSecretPath = System.getenv().getOrDefault("VAULT_SECRET_PATH", "").trim();
    private final String vaultDbPasswordField = System.getenv().getOrDefault("VAULT_DB_PASSWORD_FIELD", "database_password");
    private final HttpClient httpClient = HttpClient.newBuilder().connectTimeout(HTTP_TIMEOUT).build();

    private String databaseUrl = System.getenv().getOrDefault("DATABASE_URL", "jdbc:postgresql://postgres:5432/edc_user");
    private String databaseUser = System.getenv().getOrDefault("DATABASE_USER", "edc_user");
    private String databasePassword = System.getenv().getOrDefault("DATABASE_PASSWORD", "edc_password");

    /**
     * Initialize the Data Space Connector
     */
    public void initialize() {
        logger.info("Initializing Data Space Connector");
        if (evaluationMode) {
            logger.warn("=================================================================");
            logger.warn("EVALUATION MODE: authentication is DISABLED. Anyone who can reach");
            logger.warn("this connector can publish, negotiate and download. This is for");
            logger.warn("trying the product out and for teaching. DO NOT run it like this");
            logger.warn("anywhere anyone else can reach.");
            logger.warn("=================================================================");
        } else if ("true".equalsIgnoreCase(System.getenv().getOrDefault("EDC_EVALUATION_MODE", "").trim())) {
            logger.warn("EDC_EVALUATION_MODE is set but KEYCLOAK_JWKS_URL is configured too. "
                    + "Evaluation mode stays OFF: an identity provider is configured, so this "
                    + "is almost certainly a leftover from an evaluation template.");
        }
        if (keycloakJwksUrl.isBlank() && !evaluationMode) {
            logger.warn("KEYCLOAK_JWKS_URL is not set: every bearer token will fail signature "
                    + "verification and the management API will answer 401 to everything.");
        } else if (!keycloakJwksUrl.isBlank()) {
            logger.info("Verifying tokens against {}", keycloakJwksUrl);
        }
        logger.info("RBAC {} (read roles: {}, write roles: {}, negotiation roles: {})",
                rbacEnabled ? "enabled" : "disabled",
                rbacReadRoles,
                rbacWriteRoles,
                rbacNegotiationRoles);
        loadSecretsFromVault();
        initializeDatabase();
        initialized = true;
    }

    /**
     * Start the Data Space Connector
     */
    public void start() {
        if (!initialized) {
            throw new IllegalStateException("Connector must be initialized before starting");
        }
        startManagementApi();
        logger.info("Starting Data Space Connector");
        running = true;
    }

    /**
     * Stop the Data Space Connector
     */
    public void stop() {
        logger.info("Stopping Data Space Connector");
        if (managementServer != null) {
            managementServer.stop(0);
        }
        if (dbConnection != null) {
            try {
                dbConnection.close();
            } catch (SQLException e) {
                logger.warn("Error closing DB connection", e);
            }
        }
        running = false;
    }

    /**
     * Check if connector is running
     */
    public boolean isRunning() {
        return running;
    }

    private void startManagementApi() {
        try {
            managementServer = HttpServer.create(new InetSocketAddress(managementPort), 0);
            managementServer.createContext(managementPath + "/v3/assets", new AssetsHandler());
            managementServer.createContext(managementPath + "/v3/policydefinitions", new PolicyDefinitionsHandler());
            managementServer.createContext(managementPath + "/v3/contractdefinitions", new ContractDefinitionsHandler());
            managementServer.createContext(managementPath + "/v3/negotiations", new NegotiationsHandler());
            managementServer.setExecutor(Executors.newFixedThreadPool(4));
            managementServer.start();
            logger.info("Management API started on port {} path {}", managementPort, managementPath);
        } catch (IOException e) {
            throw new IllegalStateException("Unable to start management API", e);
        }
    }

    private boolean isAuthorized(HttpExchange exchange) {
        exchange.setAttribute(AUTH_INFO_KEY, null);

        if (evaluationMode) {
            // Sin identidad no hay a quien atribuir nada, asi que se atribuye
            // a un sujeto que se llama por su nombre: cualquier registro de
            // operaciones dira quien fue -- «evaluation» -- y no un usuario
            // que no existe.
            exchange.setAttribute(AUTH_INFO_KEY, new AuthInfo(
                    "evaluation",
                    List.of("dataspace-user", "dataspace-negotiator", "dataspace-admin"),
                    Map.of("sub", "evaluation", "evaluationMode", true)));
            return true;
        }

        String authorization = exchange.getRequestHeaders().getFirst("Authorization");
        if (authorization != null && authorization.startsWith("Bearer ")) {
            String token = authorization.substring("Bearer ".length()).trim();
            AuthInfo authInfo = validateBearerToken(token);
            if (authInfo != null) {
                exchange.setAttribute(AUTH_INFO_KEY, authInfo);
                return true;
            }
        }
        return false;
    }

    private AuthInfo getAuthInfo(HttpExchange exchange) {
        Object value = exchange.getAttribute(AUTH_INFO_KEY);
        return value instanceof AuthInfo info ? info : null;
    }

    private String readRequestBody(InputStream is) throws IOException {
        return new String(is.readAllBytes(), StandardCharsets.UTF_8);
    }

    private void writeJson(HttpExchange exchange, int statusCode, Object body) throws IOException {
        byte[] payload = GSON.toJson(body).getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(statusCode, payload.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(payload);
        }
    }

    private void writeEmpty(HttpExchange exchange, int statusCode) throws IOException {
        exchange.sendResponseHeaders(statusCode, -1);
    }

    private void addCorsHeaders(HttpExchange exchange) {
        exchange.getResponseHeaders().set("Access-Control-Allow-Origin", "*");
        exchange.getResponseHeaders().set("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
        exchange.getResponseHeaders().set("Access-Control-Allow-Headers", "Content-Type,Authorization");
    }

    private int parsePositiveInt(String value, int fallback) {
        if (value == null || value.isBlank()) {
            return fallback;
        }
        try {
            int parsed = Integer.parseInt(value.trim());
            return parsed > 0 ? parsed : fallback;
        } catch (NumberFormatException ex) {
            return fallback;
        }
    }

    private boolean isAllowedDownloadUri(URI uri) {
        if (uri == null || uri.getHost() == null || uri.getHost().isBlank()) {
            return false;
        }
        String scheme = uri.getScheme();
        if (!"http".equalsIgnoreCase(scheme) && !"https".equalsIgnoreCase(scheme)) {
            return false;
        }
        String host = uri.getHost().toLowerCase();
        for (String allowed : downloadAllowedHosts) {
            String allowedHost = allowed.toLowerCase();
            if (host.equals(allowedHost) || host.endsWith("." + allowedHost)) {
                return true;
            }
        }
        return false;
    }

    private String extractAssetBaseUrl(Asset asset) {
        if (asset == null || asset.dataAddress() == null) {
            return null;
        }
        Object baseUrl = asset.dataAddress().get("baseUrl");
        if (!(baseUrl instanceof String raw)) {
            return null;
        }
        String trimmed = raw.trim();
        return trimmed.isBlank() ? null : trimmed;
    }

    static String safeFileName(String value, String fallback) {
        String candidate = value == null ? "" : value.trim();
        if (candidate.isBlank()) {
            candidate = fallback;
        }
        String safe = candidate
                .replaceAll("[\\\\/:*?\"<>|\\p{Cntrl}]+", "_")
                .replaceAll("[^\\x20-\\x7E]", "_")
                .replaceAll("_+", "_")
                .trim();
        if (safe.isBlank()) {
            safe = fallback == null ? "download" : fallback.replaceAll("[^A-Za-z0-9._-]", "_");
        }
        return safe.substring(0, Math.min(safe.length(), 150));
    }

    static String contentDisposition(String value, String fallback) {
        String original = value == null || value.isBlank() ? fallback : value.trim();
        String encoded = URLEncoder.encode(original, StandardCharsets.UTF_8)
                .replace("+", "%20")
                .replace("%7E", "~");
        return "attachment; filename=\"" + safeFileName(original, fallback) + "\"; filename*=UTF-8''" + encoded;
    }

    static String safeContentType(String value) {
        if (value == null || value.isBlank() || value.length() > 255 ||
                !value.matches("^[A-Za-z0-9!#$&^_.+\\-]+/[A-Za-z0-9!#$&^_.+\\-]+(?:\\s*;\\s*[A-Za-z0-9!#$&^_.+\\-]+=(?:[A-Za-z0-9!#$&^_.+\\-]+|\"[\\x20-\\x7E]*\"))*$")) {
            return "application/octet-stream";
        }
        return value;
    }

    private void loadSecretsFromVault() {
        if (vaultAddress.isBlank() || vaultToken.isBlank() || vaultSecretPath.isBlank()) {
            logger.info("Vault integration disabled (VAULT_ADDR/VAULT_TOKEN/VAULT_SECRET_PATH not fully configured)");
            return;
        }

        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(vaultAddress + "/v1/" + vaultSecretPath))
                    .timeout(HTTP_TIMEOUT)
                    .header("X-Vault-Token", vaultToken)
                    .GET()
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() >= 300) {
                throw new IllegalStateException("Vault read failed (" + response.statusCode() + ")");
            }

            JsonObject root = GSON.fromJson(response.body(), JsonObject.class);
            JsonObject data = root.getAsJsonObject("data");
            JsonObject innerData = data != null ? data.getAsJsonObject("data") : null;
            if (innerData == null) {
                throw new IllegalStateException("Unexpected Vault response shape");
            }

            if (innerData.has(vaultDbPasswordField) && !innerData.get(vaultDbPasswordField).isJsonNull()) {
                databasePassword = innerData.get(vaultDbPasswordField).getAsString();
            }
            logger.info("Loaded connector secrets from Vault path {}", vaultSecretPath);
        } catch (Exception e) {
            throw new IllegalStateException("Unable to load connector secrets from Vault", e);
        }
    }

    private AuthInfo validateBearerToken(String token) {
        try {
            SignedJWT jwt = SignedJWT.parse(token);
            JWTClaimsSet claimsSet = jwt.getJWTClaimsSet();

            Instant now = Instant.now();
            if (claimsSet.getExpirationTime() == null || claimsSet.getExpirationTime().toInstant().isBefore(now)) {
                return null;
            }
            if (claimsSet.getNotBeforeTime() != null && claimsSet.getNotBeforeTime().toInstant().isAfter(now)) {
                return null;
            }
            if (!keycloakIssuerUrl.isBlank() && !Objects.equals(keycloakIssuerUrl, claimsSet.getIssuer())) {
                return null;
            }

            if (!verifyJwtSignature(jwt)) {
                return null;
            }

            Map<String, Object> claims = claimsSet.getClaims();
            if (!keycloakAudience.isBlank()) {
                List<String> audiences = claimsSet.getAudience();
                boolean matchesAudience = audiences != null && audiences.contains(keycloakAudience);
                if (!matchesAudience && !isAuditMasterUser(claims)) {
                    return null;
                }
            }
            List<String> roles = extractRealmRoles(claims);
            return new AuthInfo(claimsSet.getSubject(), roles, claims);
        } catch (ParseException e) {
            logger.debug("Invalid JWT format: {}", e.getMessage());
            return null;
        } catch (Exception e) {
            logger.warn("JWT validation failed: {}", e.getMessage());
            return null;
        }
    }

    private boolean verifyJwtSignature(SignedJWT jwt) throws IOException, InterruptedException, JOSEException, ParseException {
        String kid = jwt.getHeader().getKeyID();
        if (kid == null || kid.isBlank()) {
            return false;
        }

        JWKSet jwkSet = getJwkSet();
        JWK jwk = jwkSet.getKeyByKeyId(kid);
        if (!(jwk instanceof RSAKey rsaKey)) {
            return false;
        }
        if (!Objects.equals(JWSAlgorithm.RS256, jwt.getHeader().getAlgorithm())) {
            return false;
        }
        return jwt.verify(new RSASSAVerifier(rsaKey));
    }

    private synchronized JWKSet getJwkSet() throws IOException, InterruptedException, ParseException {
        Instant now = Instant.now();
        if (cachedJwkSet != null && jwksLoadedAt.plus(JWKS_CACHE_TTL).isAfter(now)) {
            return cachedJwkSet;
        }

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(keycloakJwksUrl))
                .timeout(HTTP_TIMEOUT)
                .GET()
                .build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() >= 300) {
            throw new IllegalStateException("Cannot load JWKS: " + response.statusCode());
        }
        cachedJwkSet = JWKSet.parse(response.body());
        jwksLoadedAt = now;
        return cachedJwkSet;
    }

    private List<String> parseRoles(String value) {
        if (value == null || value.isBlank()) {
            return List.of();
        }
        List<String> parsed = new ArrayList<>();
        for (String role : value.split(",")) {
            String trimmed = role.trim();
            if (!trimmed.isBlank() && !parsed.contains(trimmed)) {
                parsed.add(trimmed);
            }
        }
        return parsed;
    }

    private boolean isAuditMasterUser(Map<String, Object> claims) {
        if (claims == null || auditMasterUsers.isEmpty()) {
            return false;
        }

        String email = normalizeClaimText(claims.get("email"));
        String preferredUsername = normalizeClaimText(claims.get("preferred_username"));
        String subject = normalizeClaimText(claims.get("sub"));

        for (String allowed : auditMasterUsers) {
            String normalizedAllowed = normalizeClaimText(allowed);
            if (normalizedAllowed.isBlank()) {
                continue;
            }
            if (normalizedAllowed.equals(email) || normalizedAllowed.equals(preferredUsername) || normalizedAllowed.equals(subject)) {
                return true;
            }
        }
        return false;
    }

    private String normalizeClaimText(Object value) {
        if (!(value instanceof String text)) {
            return "";
        }
        return text.trim().toLowerCase();
    }

    private List<String> extractRealmRoles(Map<String, Object> claims) {
        List<String> result = new ArrayList<>();

        Object realmAccess = claims.get("realm_access");
        if (realmAccess instanceof Map<?, ?> accessMap) {
            Object roles = accessMap.get("roles");
            if (roles instanceof List<?> rolesList) {
                for (Object role : rolesList) {
                    if (role instanceof String roleValue && !roleValue.isBlank() && !result.contains(roleValue)) {
                        result.add(roleValue);
                    }
                }
            }
        }

        Object resourceAccess = claims.get("resource_access");
        if (resourceAccess instanceof Map<?, ?> resourceAccessMap) {
            for (Map.Entry<?, ?> entry : resourceAccessMap.entrySet()) {
                String clientId = entry.getKey() instanceof String key ? key : "";
                Object accessObject = entry.getValue();
                if (!(accessObject instanceof Map<?, ?> clientAccess)) {
                    continue;
                }
                Object roles = clientAccess.get("roles");
                if (!(roles instanceof List<?> clientRoles)) {
                    continue;
                }
                for (Object role : clientRoles) {
                    if (role instanceof String roleValue && !roleValue.isBlank()) {
                        if (!result.contains(roleValue)) {
                            result.add(roleValue);
                        }
                        if (!clientId.isBlank()) {
                            String namespacedRole = clientId + ":" + roleValue;
                            if (!result.contains(namespacedRole)) {
                                result.add(namespacedRole);
                            }
                        }
                    }
                }
            }
        }

        return result;
    }

    private boolean hasWalletIdentity(AuthInfo authInfo) {
        if (authInfo == null || authInfo.claims() == null) {
            return false;
        }
        Object claimValue = authInfo.claims().get(walletDidClaim);
        return claimValue instanceof String claimText && !claimText.isBlank();
    }

    private boolean hasRequiredRole(AuthInfo authInfo, List<String> requiredRoles) {
        if (!rbacEnabled || requiredRoles == null || requiredRoles.isEmpty()) {
            return true;
        }
        if (authInfo == null || authInfo.roles() == null || authInfo.roles().isEmpty()) {
            return false;
        }
        for (String requiredRole : requiredRoles) {
            if (authInfo.roles().contains(requiredRole)) {
                return true;
            }
        }
        return false;
    }

    private boolean ensureRoleAccess(HttpExchange exchange, AuthInfo authInfo, List<String> requiredRoles) throws IOException {
        if (authInfo != null
                && "GET".equalsIgnoreCase(exchange.getRequestMethod())
                && isAuditMasterUser(authInfo.claims())) {
            return true;
        }
        if (hasRequiredRole(authInfo, requiredRoles)) {
            return true;
        }
        writeJson(exchange, 403, Map.of(
                "error", "forbidden",
                "requiredRoles", requiredRoles,
                "grantedRoles", authInfo != null ? authInfo.roles() : Collections.emptyList()
        ));
        return false;
    }

    private String authClaimValue(AuthInfo authInfo, String claimName) {
        if (authInfo == null || authInfo.claims() == null || claimName == null || claimName.isBlank()) {
            return "";
        }
        return normalizeClaimText(authInfo.claims().get(claimName));
    }

    private boolean isNegotiationOwner(AuthInfo authInfo, String ownerSubject, String ownerEmail, String ownerUsername) {
        if (authInfo == null) {
            return false;
        }
        if (isAuditMasterUser(authInfo.claims())) {
            return true;
        }

        String subject = normalizeClaimText(authInfo.subject());
        String email = authClaimValue(authInfo, "email");
        String preferredUsername = authClaimValue(authInfo, "preferred_username");

        return (!subject.isBlank() && subject.equals(normalizeClaimText(ownerSubject)))
                || (!email.isBlank() && email.equals(normalizeClaimText(ownerEmail)))
                || (!preferredUsername.isBlank() && preferredUsername.equals(normalizeClaimText(ownerUsername)));
    }

    private boolean hasCompletedNegotiationForAsset(AuthInfo authInfo, String assetId) {
        if (assetId == null || assetId.isBlank()) {
            return false;
        }
        if (authInfo != null && isAuditMasterUser(authInfo.claims())) {
            return true;
        }

        String sql = """
                SELECT owner_subject, owner_email, owner_username
                FROM negotiation_requests
                WHERE asset_id = ?
                  AND UPPER(status) IN ('COMPLETED', 'FINALIZED', 'CONFIRMED', 'APPROVED')
                ORDER BY created_at DESC
                """;
        try (PreparedStatement ps = ensureDatabaseConnection().prepareStatement(sql)) {
            ps.setString(1, assetId);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    if (isNegotiationOwner(
                            authInfo,
                            rs.getString("owner_subject"),
                            rs.getString("owner_email"),
                            rs.getString("owner_username"))) {
                        return true;
                    }
                }
                return false;
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to validate negotiation access for asset " + assetId, e);
        }
    }


    private void initializeDatabase() {
        try {
            dbConnection = DriverManager.getConnection(databaseUrl, databaseUser, databasePassword);
            createSchemaIfNeeded();
            logger.info("Assets persistence enabled on {}", databaseUrl);
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to initialize assets persistence in PostgreSQL", e);
        }
    }

    private synchronized Connection ensureDatabaseConnection() throws SQLException {
        if (dbConnection == null || dbConnection.isClosed() || !dbConnection.isValid(2)) {
            if (dbConnection != null) {
                try {
                    dbConnection.close();
                } catch (SQLException e) {
                    logger.warn("Error closing stale DB connection", e);
                }
            }
            dbConnection = DriverManager.getConnection(databaseUrl, databaseUser, databasePassword);
            logger.info("Reconnected to assets persistence on {}", databaseUrl);
        }
        return dbConnection;
    }

    private void createSchemaIfNeeded() throws SQLException {
        String sql = """
                CREATE TABLE IF NOT EXISTS assets (
                  id VARCHAR(255) PRIMARY KEY,
                  properties TEXT NOT NULL,
                  data_address TEXT NOT NULL,
                  created_at TIMESTAMP NOT NULL,
                  updated_at TIMESTAMP NOT NULL
                )
                """;
        try (PreparedStatement ps = ensureDatabaseConnection().prepareStatement(sql)) {
            ps.execute();
        }

        String policiesSql = """
                CREATE TABLE IF NOT EXISTS policy_definitions (
                  id VARCHAR(255) PRIMARY KEY,
                  policy TEXT NOT NULL,
                  created_at TIMESTAMP NOT NULL,
                  updated_at TIMESTAMP NOT NULL
                )
                """;
        try (PreparedStatement ps = ensureDatabaseConnection().prepareStatement(policiesSql)) {
            ps.execute();
        }

        String contractsSql = """
                CREATE TABLE IF NOT EXISTS contract_definitions (
                  id VARCHAR(255) PRIMARY KEY,
                  access_policy_id VARCHAR(255) NOT NULL,
                  contract_policy_id VARCHAR(255) NOT NULL,
                  assets_selector TEXT NOT NULL,
                  created_at TIMESTAMP NOT NULL,
                  updated_at TIMESTAMP NOT NULL
                )
                """;
        try (PreparedStatement ps = ensureDatabaseConnection().prepareStatement(contractsSql)) {
            ps.execute();
        }

        String negotiationsSql = """
                CREATE TABLE IF NOT EXISTS negotiation_requests (
                  id VARCHAR(255) PRIMARY KEY,
                  consumer_connector_id VARCHAR(255) NOT NULL,
                  provider_connector_id VARCHAR(255) NOT NULL,
                  asset_id VARCHAR(255) NOT NULL,
                  policy_id VARCHAR(255) NOT NULL,
                  owner_subject VARCHAR(255),
                  owner_email VARCHAR(255),
                  owner_username VARCHAR(255),
                  status VARCHAR(64) NOT NULL,
                  created_at TIMESTAMP NOT NULL
                )
                """;
        try (PreparedStatement ps = ensureDatabaseConnection().prepareStatement(negotiationsSql)) {
            ps.execute();
        }

        String negotiationsOwnerColumnsSql = """
                ALTER TABLE negotiation_requests
                ADD COLUMN IF NOT EXISTS owner_subject VARCHAR(255),
                ADD COLUMN IF NOT EXISTS owner_email VARCHAR(255),
                ADD COLUMN IF NOT EXISTS owner_username VARCHAR(255)
                """;
        try (PreparedStatement ps = ensureDatabaseConnection().prepareStatement(negotiationsOwnerColumnsSql)) {
            ps.execute();
        }
    }

    private void saveAsset(Asset asset) {
        String sql = """
                INSERT INTO assets(id, properties, data_address, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE
                SET properties = EXCLUDED.properties,
                    data_address = EXCLUDED.data_address,
                    updated_at = EXCLUDED.updated_at
                """;

        Timestamp now = Timestamp.from(Instant.now());
        try (PreparedStatement ps = ensureDatabaseConnection().prepareStatement(sql)) {
            ps.setString(1, asset.id());
            ps.setString(2, GSON.toJson(asset.properties()));
            ps.setString(3, GSON.toJson(asset.dataAddress()));
            ps.setTimestamp(4, now);
            ps.setTimestamp(5, now);
            ps.executeUpdate();
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to persist asset " + asset.id(), e);
        }
    }

    private Asset findAssetById(String id) {
        String sql = "SELECT id, properties, data_address FROM assets WHERE id = ?";
        try (PreparedStatement ps = ensureDatabaseConnection().prepareStatement(sql)) {
            ps.setString(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return null;
                }
                String propsJson = rs.getString("properties");
                String dataAddressJson = rs.getString("data_address");
                Map<String, Object> properties = GSON.fromJson(propsJson, MAP_TYPE);
                Map<String, Object> dataAddress = GSON.fromJson(dataAddressJson, MAP_TYPE);
                return new Asset(rs.getString("id"), properties, dataAddress);
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to read asset " + id, e);
        }
    }

    private List<Asset> listAssets() {
        String sql = "SELECT id, properties, data_address FROM assets ORDER BY created_at DESC";
        List<Asset> result = new ArrayList<>();
        try (PreparedStatement ps = ensureDatabaseConnection().prepareStatement(sql);
             ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                Map<String, Object> properties = GSON.fromJson(rs.getString("properties"), MAP_TYPE);
                Map<String, Object> dataAddress = GSON.fromJson(rs.getString("data_address"), MAP_TYPE);
                result.add(new Asset(rs.getString("id"), properties, dataAddress));
            }
            return result;
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to list assets", e);
        }
    }

    private void savePolicyDefinition(PolicyDefinition policyDefinition) {
        String sql = """
                INSERT INTO policy_definitions(id, policy, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE
                SET policy = EXCLUDED.policy,
                    updated_at = EXCLUDED.updated_at
                """;

        Timestamp now = Timestamp.from(Instant.now());
        try (PreparedStatement ps = ensureDatabaseConnection().prepareStatement(sql)) {
            ps.setString(1, policyDefinition.id());
            ps.setString(2, GSON.toJson(policyDefinition.policy()));
            ps.setTimestamp(3, now);
            ps.setTimestamp(4, now);
            ps.executeUpdate();
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to persist policy definition " + policyDefinition.id(), e);
        }
    }

    private PolicyDefinition findPolicyDefinitionById(String id) {
        String sql = "SELECT id, policy FROM policy_definitions WHERE id = ?";
        try (PreparedStatement ps = ensureDatabaseConnection().prepareStatement(sql)) {
            ps.setString(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return null;
                }
                Map<String, Object> policy = GSON.fromJson(rs.getString("policy"), MAP_TYPE);
                return new PolicyDefinition(rs.getString("id"), policy);
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to read policy definition " + id, e);
        }
    }

    private List<PolicyDefinition> listPolicyDefinitions() {
        String sql = "SELECT id, policy FROM policy_definitions ORDER BY created_at DESC";
        List<PolicyDefinition> result = new ArrayList<>();
        try (PreparedStatement ps = ensureDatabaseConnection().prepareStatement(sql);
             ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                Map<String, Object> policy = GSON.fromJson(rs.getString("policy"), MAP_TYPE);
                result.add(new PolicyDefinition(rs.getString("id"), policy));
            }
            return result;
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to list policy definitions", e);
        }
    }

    private void saveContractDefinition(ContractDefinition contractDefinition) {
        String sql = """
                INSERT INTO contract_definitions(id, access_policy_id, contract_policy_id, assets_selector, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE
                SET access_policy_id = EXCLUDED.access_policy_id,
                    contract_policy_id = EXCLUDED.contract_policy_id,
                    assets_selector = EXCLUDED.assets_selector,
                    updated_at = EXCLUDED.updated_at
                """;

        Timestamp now = Timestamp.from(Instant.now());
        try (PreparedStatement ps = ensureDatabaseConnection().prepareStatement(sql)) {
            ps.setString(1, contractDefinition.id());
            ps.setString(2, contractDefinition.accessPolicyId());
            ps.setString(3, contractDefinition.contractPolicyId());
            ps.setString(4, GSON.toJson(contractDefinition.assetsSelector()));
            ps.setTimestamp(5, now);
            ps.setTimestamp(6, now);
            ps.executeUpdate();
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to persist contract definition " + contractDefinition.id(), e);
        }
    }

    private ContractDefinition findContractDefinitionById(String id) {
        String sql = "SELECT id, access_policy_id, contract_policy_id, assets_selector FROM contract_definitions WHERE id = ?";
        try (PreparedStatement ps = ensureDatabaseConnection().prepareStatement(sql)) {
            ps.setString(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return null;
                }
                List<Map<String, Object>> selector = GSON.fromJson(rs.getString("assets_selector"), LIST_OF_MAP_TYPE);
                return new ContractDefinition(
                        rs.getString("id"),
                        rs.getString("access_policy_id"),
                        rs.getString("contract_policy_id"),
                        selector
                );
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to read contract definition " + id, e);
        }
    }

    private List<ContractDefinition> listContractDefinitions() {
        String sql = "SELECT id, access_policy_id, contract_policy_id, assets_selector FROM contract_definitions ORDER BY created_at DESC";
        List<ContractDefinition> result = new ArrayList<>();
        try (PreparedStatement ps = ensureDatabaseConnection().prepareStatement(sql);
             ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                List<Map<String, Object>> selector = GSON.fromJson(rs.getString("assets_selector"), LIST_OF_MAP_TYPE);
                result.add(new ContractDefinition(
                        rs.getString("id"),
                        rs.getString("access_policy_id"),
                        rs.getString("contract_policy_id"),
                        selector
                ));
            }
            return result;
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to list contract definitions", e);
        }
    }

    private String extractSingleAssetIdFromSelector(List<Map<String, Object>> selector) {
        if (selector == null) {
            return null;
        }
        for (Map<String, Object> criterion : selector) {
            Object leftOperand = criterion.get("leftOperand");
            Object operator = criterion.get("operator");
            Object rightOperand = criterion.get("rightOperand");
            if (Objects.equals("id", leftOperand) && Objects.equals("=", operator) && rightOperand instanceof String ro) {
                return ro;
            }
            if (Objects.equals("id", leftOperand) && Objects.equals("eq", operator) && rightOperand instanceof String roEq) {
                return roEq;
            }
        }
        return null;
    }

    private void saveNegotiationRequest(NegotiationRequest request) {
        String sql = """
                INSERT INTO negotiation_requests(
                    id, consumer_connector_id, provider_connector_id, asset_id, policy_id,
                    owner_subject, owner_email, owner_username, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE
                SET consumer_connector_id = EXCLUDED.consumer_connector_id,
                    provider_connector_id = EXCLUDED.provider_connector_id,
                    asset_id = EXCLUDED.asset_id,
                    policy_id = EXCLUDED.policy_id,
                    owner_subject = EXCLUDED.owner_subject,
                    owner_email = EXCLUDED.owner_email,
                    owner_username = EXCLUDED.owner_username,
                    status = EXCLUDED.status
                """;
        try (PreparedStatement ps = ensureDatabaseConnection().prepareStatement(sql)) {
            ps.setString(1, request.id());
            ps.setString(2, request.consumerConnectorId());
            ps.setString(3, request.providerConnectorId());
            ps.setString(4, request.assetId());
            ps.setString(5, request.policyId());
            ps.setString(6, request.ownerSubject());
            ps.setString(7, request.ownerEmail());
            ps.setString(8, request.ownerUsername());
            ps.setString(9, request.status());
            ps.setTimestamp(10, Timestamp.from(Instant.now()));
            ps.executeUpdate();
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to persist negotiation request " + request.id(), e);
        }
    }

    private List<NegotiationRequest> listNegotiationRequests(AuthInfo authInfo) {
        String sql = """
                SELECT id, consumer_connector_id, provider_connector_id, asset_id, policy_id,
                       owner_subject, owner_email, owner_username, status
                FROM negotiation_requests
                ORDER BY created_at DESC
                """;
        List<NegotiationRequest> result = new ArrayList<>();
        try (PreparedStatement ps = ensureDatabaseConnection().prepareStatement(sql);
             ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                NegotiationRequest request = new NegotiationRequest(
                        rs.getString("id"),
                        rs.getString("consumer_connector_id"),
                        rs.getString("provider_connector_id"),
                        rs.getString("asset_id"),
                        rs.getString("policy_id"),
                        rs.getString("owner_subject"),
                        rs.getString("owner_email"),
                        rs.getString("owner_username"),
                        rs.getString("status")
                );
                if (isNegotiationOwner(authInfo, request.ownerSubject(), request.ownerEmail(), request.ownerUsername())) {
                    result.add(request);
                }
            }
            return result;
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to list negotiation requests", e);
        }
    }

    private final class AssetsHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            try {
                handleAssets(exchange);
            } catch (Exception e) {
                logger.error("Unhandled assets handler error", e);
                if (exchange.getResponseCode() == -1) {
                    writeJson(exchange, 500, Map.of("error", "internal_error", "detail", e.getMessage()));
                }
            }
        }

        private void handleAssets(HttpExchange exchange) throws IOException {
            addCorsHeaders(exchange);
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                writeEmpty(exchange, 204);
                return;
            }

            if (!isAuthorized(exchange)) {
                writeJson(exchange, 401, Map.of("error", "unauthorized"));
                return;
            }

            String method = exchange.getRequestMethod();
            String path = exchange.getRequestURI().getPath();
            String basePath = managementPath + "/v3/assets";

            if ("POST".equalsIgnoreCase(method) && basePath.equals(path)) {
                AuthInfo authInfo = getAuthInfo(exchange);
                if (!ensureRoleAccess(exchange, authInfo, rbacWriteRoles)) {
                    return;
                }
                if (requireWalletIdentity && !hasWalletIdentity(authInfo)) {
                    writeJson(exchange, 403, Map.of("error", "wallet identity claim required"));
                    return;
                }

                String rawBody = readRequestBody(exchange.getRequestBody());
                JsonObject json = GSON.fromJson(rawBody, JsonObject.class);
                if (json == null) {
                    writeJson(exchange, 400, Map.of("error", "invalid json"));
                    return;
                }

                String id = json.has("@id") && !json.get("@id").isJsonNull()
                        ? json.get("@id").getAsString()
                        : "asset-" + UUID.randomUUID();
                JsonObject propsObj = json.has("properties") && json.get("properties").isJsonObject()
                        ? json.getAsJsonObject("properties")
                        : new JsonObject();
                JsonObject dataAddressObj = json.has("dataAddress") && json.get("dataAddress").isJsonObject()
                        ? json.getAsJsonObject("dataAddress")
                        : new JsonObject();

                Map<String, Object> properties = GSON.fromJson(propsObj, MAP_TYPE);
                Map<String, Object> dataAddress = GSON.fromJson(dataAddressObj, MAP_TYPE);
                Asset asset = new Asset(id, properties, dataAddress);
                saveAsset(asset);
                writeJson(exchange, 200, Map.of("@id", id));
                return;
            }

            if ("GET".equalsIgnoreCase(method) && basePath.equals(path)) {
                if (!ensureRoleAccess(exchange, getAuthInfo(exchange), rbacReadRoles)) {
                    return;
                }
                writeJson(exchange, 200, listAssets());
                return;
            }

            if ("GET".equalsIgnoreCase(method) && path.startsWith(basePath + "/")) {
                AuthInfo authInfo = getAuthInfo(exchange);
                if (!ensureRoleAccess(exchange, authInfo, rbacReadRoles)) {
                    return;
                }
                String suffix = path.substring((basePath + "/").length());

                if (suffix.endsWith("/download")) {
                    String id = suffix.substring(0, suffix.length() - "/download".length());
                    if (id.isBlank() || id.contains("/")) {
                        writeJson(exchange, 400, Map.of("error", "invalid asset id"));
                        return;
                    }

                    Asset asset = findAssetById(id);
                    if (asset == null) {
                        writeJson(exchange, 404, Map.of("error", "asset not found"));
                        return;
                    }

                    if (!hasCompletedNegotiationForAsset(authInfo, asset.id())) {
                        writeJson(exchange, 403, Map.of("error", "completed negotiation required for this asset"));
                        return;
                    }

                    String baseUrl = extractAssetBaseUrl(asset);
                    if (baseUrl == null) {
                        writeJson(exchange, 404, Map.of("error", "asset data address not available"));
                        return;
                    }

                    URI upstreamUri;
                    try {
                        upstreamUri = URI.create(baseUrl);
                    } catch (IllegalArgumentException ex) {
                        writeJson(exchange, 400, Map.of("error", "invalid asset source url"));
                        return;
                    }

                    if (!isAllowedDownloadUri(upstreamUri)) {
                        writeJson(exchange, 403, Map.of("error", "asset source host is not allowed"));
                        return;
                    }

                    try {
                        HttpRequest.Builder upstreamBuilder = HttpRequest.newBuilder()
                            .uri(upstreamUri)
                            .timeout(HTTP_TIMEOUT)
                            .GET();
                        if (!downloadInternalKey.isBlank()) {
                            upstreamBuilder.header("X-Internal-Download-Key", downloadInternalKey);
                        }
                        HttpRequest upstreamRequest = upstreamBuilder.build();
                        HttpResponse<byte[]> upstreamResponse = httpClient.send(upstreamRequest, HttpResponse.BodyHandlers.ofByteArray());
                        if (upstreamResponse.statusCode() >= 400) {
                            writeJson(exchange, 502, Map.of(
                                    "error", "upstream download failed",
                                    "status", upstreamResponse.statusCode()
                            ));
                            return;
                        }

                        byte[] payload = upstreamResponse.body();
                        if (payload.length > downloadMaxBytes) {
                            writeJson(exchange, 413, Map.of("error", "asset too large"));
                            return;
                        }

                        String contentType = safeContentType(upstreamResponse.headers().firstValue("Content-Type").orElse(null));
                        String assetName = asset.properties() != null && asset.properties().get("name") instanceof String name ? name : id;

                        exchange.getResponseHeaders().set("Content-Type", contentType);
                        exchange.getResponseHeaders().set("Content-Disposition", contentDisposition(assetName, id));
                        exchange.sendResponseHeaders(200, payload.length);
                        try (OutputStream os = exchange.getResponseBody()) {
                            os.write(payload);
                        }
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        writeJson(exchange, 502, Map.of("error", "download interrupted"));
                    }
                    return;
                }

                if (suffix.contains("/")) {
                    writeJson(exchange, 404, Map.of("error", "asset not found"));
                    return;
                }

                Asset asset = findAssetById(suffix);
                if (asset == null) {
                    writeJson(exchange, 404, Map.of("error", "asset not found"));
                } else {
                    writeJson(exchange, 200, asset);
                }
                return;
            }

            writeEmpty(exchange, 405);
        }
    }

    private final class PolicyDefinitionsHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            addCorsHeaders(exchange);
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                writeEmpty(exchange, 204);
                return;
            }

            if (!isAuthorized(exchange)) {
                writeJson(exchange, 401, Map.of("error", "unauthorized"));
                return;
            }

            String method = exchange.getRequestMethod();
            String path = exchange.getRequestURI().getPath();
            String basePath = managementPath + "/v3/policydefinitions";

            if ("POST".equalsIgnoreCase(method) && basePath.equals(path)) {
                if (!ensureRoleAccess(exchange, getAuthInfo(exchange), rbacWriteRoles)) {
                    return;
                }
                String rawBody = readRequestBody(exchange.getRequestBody());
                JsonObject json = GSON.fromJson(rawBody, JsonObject.class);
                if (json == null) {
                    writeJson(exchange, 400, Map.of("error", "invalid json"));
                    return;
                }

                String id = json.has("@id") && !json.get("@id").isJsonNull()
                        ? json.get("@id").getAsString()
                        : "policy-" + UUID.randomUUID();
                JsonObject policyObj = json.has("policy") && json.get("policy").isJsonObject()
                        ? json.getAsJsonObject("policy")
                        : new JsonObject();
                Map<String, Object> policy = GSON.fromJson(policyObj, MAP_TYPE);
                PolicyDefinition policyDefinition = new PolicyDefinition(id, policy);
                savePolicyDefinition(policyDefinition);
                writeJson(exchange, 200, Map.of("@id", id));
                return;
            }

            if ("GET".equalsIgnoreCase(method) && basePath.equals(path)) {
                if (!ensureRoleAccess(exchange, getAuthInfo(exchange), rbacReadRoles)) {
                    return;
                }
                writeJson(exchange, 200, listPolicyDefinitions());
                return;
            }

            if ("GET".equalsIgnoreCase(method) && path.startsWith(basePath + "/")) {
                if (!ensureRoleAccess(exchange, getAuthInfo(exchange), rbacReadRoles)) {
                    return;
                }
                String id = path.substring((basePath + "/").length());
                PolicyDefinition policyDefinition = findPolicyDefinitionById(id);
                if (policyDefinition == null) {
                    writeJson(exchange, 404, Map.of("error", "policy definition not found"));
                } else {
                    writeJson(exchange, 200, policyDefinition);
                }
                return;
            }

            writeEmpty(exchange, 405);
        }
    }

    private final class ContractDefinitionsHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            addCorsHeaders(exchange);
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                writeEmpty(exchange, 204);
                return;
            }

            if (!isAuthorized(exchange)) {
                writeJson(exchange, 401, Map.of("error", "unauthorized"));
                return;
            }

            String method = exchange.getRequestMethod();
            String path = exchange.getRequestURI().getPath();
            String basePath = managementPath + "/v3/contractdefinitions";

            if ("POST".equalsIgnoreCase(method) && basePath.equals(path)) {
                if (!ensureRoleAccess(exchange, getAuthInfo(exchange), rbacWriteRoles)) {
                    return;
                }
                String rawBody = readRequestBody(exchange.getRequestBody());
                JsonObject json = GSON.fromJson(rawBody, JsonObject.class);
                if (json == null) {
                    writeJson(exchange, 400, Map.of("error", "invalid json"));
                    return;
                }

                String id = json.has("@id") && !json.get("@id").isJsonNull()
                        ? json.get("@id").getAsString()
                        : "contract-" + UUID.randomUUID();
                String accessPolicyId = json.has("accessPolicyId") && !json.get("accessPolicyId").isJsonNull()
                        ? json.get("accessPolicyId").getAsString()
                        : null;
                String contractPolicyId = json.has("contractPolicyId") && !json.get("contractPolicyId").isJsonNull()
                        ? json.get("contractPolicyId").getAsString()
                        : null;
                JsonArray selectorArray = json.has("assetsSelector") && json.get("assetsSelector").isJsonArray()
                        ? json.getAsJsonArray("assetsSelector")
                        : new JsonArray();
                List<Map<String, Object>> assetsSelector = GSON.fromJson(selectorArray, LIST_OF_MAP_TYPE);

                if (accessPolicyId == null || contractPolicyId == null || assetsSelector == null || assetsSelector.isEmpty()) {
                    writeJson(exchange, 400, Map.of("error", "accessPolicyId, contractPolicyId and assetsSelector are required"));
                    return;
                }

                if (findPolicyDefinitionById(accessPolicyId) == null || findPolicyDefinitionById(contractPolicyId) == null) {
                    writeJson(exchange, 400, Map.of("error", "referenced policy definition does not exist"));
                    return;
                }

                String selectedAssetId = extractSingleAssetIdFromSelector(assetsSelector);
                if (selectedAssetId == null || findAssetById(selectedAssetId) == null) {
                    writeJson(exchange, 400, Map.of("error", "referenced asset does not exist or selector is unsupported"));
                    return;
                }

                ContractDefinition contractDefinition = new ContractDefinition(id, accessPolicyId, contractPolicyId, assetsSelector);
                saveContractDefinition(contractDefinition);
                writeJson(exchange, 200, Map.of("@id", id));
                return;
            }

            if ("GET".equalsIgnoreCase(method) && basePath.equals(path)) {
                if (!ensureRoleAccess(exchange, getAuthInfo(exchange), rbacReadRoles)) {
                    return;
                }
                writeJson(exchange, 200, listContractDefinitions());
                return;
            }

            if ("GET".equalsIgnoreCase(method) && path.startsWith(basePath + "/")) {
                if (!ensureRoleAccess(exchange, getAuthInfo(exchange), rbacReadRoles)) {
                    return;
                }
                String id = path.substring((basePath + "/").length());
                ContractDefinition contractDefinition = findContractDefinitionById(id);
                if (contractDefinition == null) {
                    writeJson(exchange, 404, Map.of("error", "contract definition not found"));
                } else {
                    writeJson(exchange, 200, contractDefinition);
                }
                return;
            }

            writeEmpty(exchange, 405);
        }
    }

    private final class NegotiationsHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            addCorsHeaders(exchange);
            if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
                writeEmpty(exchange, 204);
                return;
            }

            if (!isAuthorized(exchange)) {
                writeJson(exchange, 401, Map.of("error", "unauthorized"));
                return;
            }

            String method = exchange.getRequestMethod();
            String path = exchange.getRequestURI().getPath();
            String basePath = managementPath + "/v3/negotiations";

            if ("POST".equalsIgnoreCase(method) && basePath.equals(path)) {
                AuthInfo authInfo = getAuthInfo(exchange);
                if (!ensureRoleAccess(exchange, authInfo, rbacNegotiationRoles)) {
                    return;
                }
                String rawBody = readRequestBody(exchange.getRequestBody());
                JsonObject json = GSON.fromJson(rawBody, JsonObject.class);
                if (json == null) {
                    writeJson(exchange, 400, Map.of("error", "invalid json"));
                    return;
                }

                String id = json.has("@id") && !json.get("@id").isJsonNull()
                        ? json.get("@id").getAsString()
                        : "negotiation-" + UUID.randomUUID();
                String consumerConnectorId = json.has("consumerConnectorId") && !json.get("consumerConnectorId").isJsonNull()
                        ? json.get("consumerConnectorId").getAsString()
                        : "unknown-consumer";
                String providerConnectorId = json.has("providerConnectorId") && !json.get("providerConnectorId").isJsonNull()
                        ? json.get("providerConnectorId").getAsString()
                        : "unknown-provider";
                String assetId = json.has("assetId") && !json.get("assetId").isJsonNull()
                        ? json.get("assetId").getAsString()
                        : null;
                String policyId = json.has("policyId") && !json.get("policyId").isJsonNull()
                        ? json.get("policyId").getAsString()
                        : null;
                String status = json.has("status") && !json.get("status").isJsonNull()
                        ? json.get("status").getAsString()
                        : "REQUESTED";

                if (assetId == null || policyId == null) {
                    writeJson(exchange, 400, Map.of("error", "assetId and policyId are required"));
                    return;
                }

                NegotiationRequest request = new NegotiationRequest(
                        id,
                        consumerConnectorId,
                        providerConnectorId,
                        assetId,
                        policyId,
                        authInfo != null ? authInfo.subject() : "",
                        authClaimValue(authInfo, "email"),
                        authClaimValue(authInfo, "preferred_username"),
                        status
                );
                saveNegotiationRequest(request);
                writeJson(exchange, 200, Map.of("@id", id, "status", status));
                return;
            }

            if ("GET".equalsIgnoreCase(method) && basePath.equals(path)) {
                AuthInfo authInfo = getAuthInfo(exchange);
                if (!ensureRoleAccess(exchange, authInfo, rbacReadRoles)) {
                    return;
                }
                writeJson(exchange, 200, listNegotiationRequests(authInfo));
                return;
            }

            writeEmpty(exchange, 405);
        }
    }

    private record Asset(String id, Map<String, Object> properties, Map<String, Object> dataAddress) {}
    private record PolicyDefinition(String id, Map<String, Object> policy) {}
    private record ContractDefinition(String id, String accessPolicyId, String contractPolicyId,
                                      List<Map<String, Object>> assetsSelector) {}
    private record NegotiationRequest(String id, String consumerConnectorId, String providerConnectorId,
                                      String assetId, String policyId, String ownerSubject,
                                      String ownerEmail, String ownerUsername, String status) {}
    private record AuthInfo(String subject, List<String> roles, Map<String, Object> claims) {}
}
