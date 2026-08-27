package org.eclipse.dataspace;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.net.InetSocketAddress;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.Scanner;
import java.util.Map;
import java.util.HashMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

/**
 * Identity Hub service for managing digital identities and credentials
 */
public class IdentityHubService {
    private static final Logger logger = LoggerFactory.getLogger(IdentityHubService.class);
    private boolean initialized = false;
    private Connection dbConnection;
    private HttpServer httpServer;
    private final AtomicLong credentialSequence = new AtomicLong();
    // In-memory fallback when DB is not available (useful for tests)
    private final ConcurrentHashMap<String, String> participantsMap = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, String> credentialsMap = new ConcurrentHashMap<>();

    public void initialize() {
        if (initialized) {
            logger.info("Identity Hub service is already initialized");
            return;
        }

        logger.info("Initializing Identity Hub service");
        try {
            // Read DB configuration from environment variables
            String dbUrl = System.getenv().getOrDefault("DATABASE_URL",
                    "jdbc:postgresql://localhost:5432/identity_hub");
            String dbUser = System.getenv().getOrDefault("DATABASE_USER", "edc_user");
            String dbPassword = System.getenv().getOrDefault("DATABASE_PASSWORD", "edc_password");

            // Attempt to initialize JDBC connection; if it fails we'll fall back to
            // in-memory maps
            try {
                dbConnection = DriverManager.getConnection(dbUrl, dbUser, dbPassword);
                ensureSchema();
                logger.info("Connected to Identity Hub DB: {}", dbUrl);
            } catch (SQLException sqle) {
                logger.warn("Could not connect to DB ({}), falling back to in-memory store: {}", dbUrl,
                        sqle.getMessage());
                dbConnection = null;
            }

            // Start a simple HTTP server for REST endpoints
            int port = Integer.parseInt(System.getenv().getOrDefault("IDENTITY_HUB_PORT", "8089"));
            httpServer = HttpServer.create(new InetSocketAddress(port), 0);
            httpServer.createContext("/participants", new ParticipantsHandler());
            httpServer.createContext("/credentials", new CredentialsHandler());
            httpServer.createContext("/credentials/verify", new VerifyHandler());
            httpServer.setExecutor(null);
            httpServer.start();

            initialized = true;
            logger.info("Identity Hub service initialized and HTTP server started on port {}", port);
        } catch (Exception e) {
            logger.error("Failed to initialize Identity Hub service", e);
            throw new RuntimeException(e);
        }
    }

    public void shutdown() {
        if (httpServer != null) {
            httpServer.stop(0);
            httpServer = null;
        }
        if (dbConnection != null) {
            try {
                dbConnection.close();
            } catch (SQLException e) {
                logger.warn("Failed to close DB connection cleanly", e);
            } finally {
                dbConnection = null;
            }
        }
        initialized = false;
    }

    private void ensureSchema() throws SQLException {
        try (Statement st = dbConnection.createStatement()) {
            st.execute(
                    "CREATE TABLE IF NOT EXISTS participants (id VARCHAR(255) PRIMARY KEY, credential_type VARCHAR(255), created_at TIMESTAMP)");
            st.execute(
                    "CREATE TABLE IF NOT EXISTS credentials (id VARCHAR(255) PRIMARY KEY, participant_id VARCHAR(255), data TEXT, created_at TIMESTAMP)");
        }
    }

    public boolean registerParticipant(String participantId, String credentialType) {
        checkInitialized();
        if (isBlank(participantId)) {
            logger.warn("Cannot register participant with blank participantId");
            return false;
        }

        String normalizedCredentialType = credentialType == null ? "" : credentialType;
        logger.info("Registering participant: {} with credential type: {}", participantId, credentialType);
        if (dbConnection != null) {
            String sql = "INSERT INTO participants(id, credential_type, created_at) VALUES (?, ?, ?) ON CONFLICT (id) DO NOTHING";
            try (PreparedStatement ps = dbConnection.prepareStatement(sql)) {
                ps.setString(1, participantId);
                ps.setString(2, normalizedCredentialType);
                ps.setTimestamp(3, Timestamp.from(Instant.now()));
                ps.executeUpdate();
                return true;
            } catch (SQLException e) {
                logger.error("Failed to register participant", e);
                return false;
            }
        } else {
            participantsMap.putIfAbsent(participantId, normalizedCredentialType);
            return true;
        }
    }

    public String issueCredential(String participantId, String credentialData) {
        checkInitialized();
        if (isBlank(participantId) || isBlank(credentialData)) {
            logger.warn("Cannot issue credential with blank participantId or credentialData");
            return null;
        }

        if (!participantExists(participantId)) {
            logger.warn("Cannot issue credential: participant does not exist: {}", participantId);
            return null;
        }

        logger.info("Issuing credential to participant: {}", participantId);
        String credentialId = "cred_" + System.currentTimeMillis() + "_" + credentialSequence.incrementAndGet();
        if (dbConnection != null) {
            String sql = "INSERT INTO credentials(id, participant_id, data, created_at) VALUES (?, ?, ?, ?)";
            try (PreparedStatement ps = dbConnection.prepareStatement(sql)) {
                ps.setString(1, credentialId);
                ps.setString(2, participantId);
                ps.setString(3, credentialData);
                ps.setTimestamp(4, Timestamp.from(Instant.now()));
                ps.executeUpdate();
                return credentialId;
            } catch (SQLException e) {
                logger.error("Failed to issue credential", e);
                return null;
            }
        } else {
            credentialsMap.put(credentialId, participantId + "::" + credentialData);
            return credentialId;
        }
    }

    public boolean verifyCredential(String credentialId) {
        checkInitialized();
        if (isBlank(credentialId)) {
            return false;
        }

        logger.info("Verifying credential: {}", credentialId);
        if (dbConnection != null) {
            String sql = "SELECT id FROM credentials WHERE id = ?";
            try (PreparedStatement ps = dbConnection.prepareStatement(sql)) {
                ps.setString(1, credentialId);
                try (ResultSet rs = ps.executeQuery()) {
                    return rs.next();
                }
            } catch (SQLException e) {
                logger.error("Credential verification failed", e);
                return false;
            }
        } else {
            return credentialsMap.containsKey(credentialId);
        }
    }

    private void checkInitialized() {
        if (!initialized) {
            throw new IllegalStateException("Identity Hub must be initialized first");
        }
    }

    private String readRequestBody(InputStream is) throws IOException {
        try (Scanner s = new Scanner(is, StandardCharsets.UTF_8).useDelimiter("\\A")) {
            return s.hasNext() ? s.next() : "";
        }
    }

    private boolean participantExists(String participantId) {
        if (dbConnection != null) {
            String sql = "SELECT id FROM participants WHERE id = ?";
            try (PreparedStatement ps = dbConnection.prepareStatement(sql)) {
                ps.setString(1, participantId);
                try (ResultSet rs = ps.executeQuery()) {
                    return rs.next();
                }
            } catch (SQLException e) {
                logger.error("Participant lookup failed", e);
                return false;
            }
        }

        return participantsMap.containsKey(participantId);
    }

    private Map<String, String> parseFormBody(String body) {
        Map<String, String> values = new HashMap<>();
        if (body == null || body.isEmpty()) {
            return values;
        }

        for (String part : body.split("&")) {
            String[] kv = part.split("=", 2);
            if (kv.length == 2) {
                values.put(URLDecoder.decode(kv[0], StandardCharsets.UTF_8),
                        URLDecoder.decode(kv[1], StandardCharsets.UTF_8));
            }
        }

        return values;
    }

    private Map<String, String> parseQuery(String query) {
        return parseFormBody(query);
    }

    private void writeResponse(HttpExchange exchange, int statusCode, String body) throws IOException {
        byte[] payload = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "text/plain; charset=utf-8");
        exchange.sendResponseHeaders(statusCode, payload.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(payload);
        }
    }

    private boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    class ParticipantsHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("POST".equalsIgnoreCase(exchange.getRequestMethod())) {
                String body = readRequestBody(exchange.getRequestBody());
                Map<String, String> values = parseFormBody(body);
                String participantId = values.get("participantId");
                String credentialType = values.get("credentialType");
                boolean ok = false;
                if (participantId != null) {
                    ok = registerParticipant(participantId, credentialType == null ? "" : credentialType);
                }
                String resp = ok ? "registered" : "error";
                writeResponse(exchange, ok ? 201 : 400, resp);
            } else {
                exchange.sendResponseHeaders(405, -1);
            }
        }
    }

    class CredentialsHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("POST".equalsIgnoreCase(exchange.getRequestMethod())) {
                String body = readRequestBody(exchange.getRequestBody());
                Map<String, String> values = parseFormBody(body);
                String participantId = values.get("participantId");
                String data = values.get("data");
                if (participantId != null && data != null) {
                    String credId = issueCredential(participantId, data);
                    String resp = credId == null ? "error" : credId;
                    writeResponse(exchange, credId == null ? 500 : 201, resp);
                } else {
                    exchange.sendResponseHeaders(400, -1);
                }
            } else {
                exchange.sendResponseHeaders(405, -1);
            }
        }
    }

    class VerifyHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if ("GET".equalsIgnoreCase(exchange.getRequestMethod())) {
                String query = exchange.getRequestURI().getQuery();
                Map<String, String> queryValues = parseQuery(query);
                String credentialId = queryValues.get("id");
                if (credentialId != null) {
                    boolean ok = verifyCredential(credentialId);
                    String resp = ok ? "valid" : "invalid";
                    writeResponse(exchange, 200, resp);
                } else {
                    exchange.sendResponseHeaders(400, -1);
                }
            } else {
                exchange.sendResponseHeaders(405, -1);
            }
        }
    }
}
