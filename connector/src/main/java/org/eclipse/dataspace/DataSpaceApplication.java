package org.eclipse.dataspace;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Entry point of the node's connector.
 *
 * It used to start an "Identity Hub" beside the connector: an HTTP server on
 * port 8089, without authentication, whose "credentials" were database rows
 * and which nothing called. Identity is the token Keycloak signs, checked by
 * the connector itself, so it was removed rather than secured.
 */
public class DataSpaceApplication {
    private static final Logger logger = LoggerFactory.getLogger(DataSpaceApplication.class);

    public static void main(String[] args) {
        logger.info("Starting the data space connector");
        
        try {
            // Initialize the Data Space Connector
            DataSpaceConnector connector = new DataSpaceConnector();
            connector.initialize();
            logger.info("Data Space Connector initialized successfully");
            
            Runtime.getRuntime().addShutdownHook(new Thread(() -> {
                logger.info("Shutdown requested. Stopping services...");
                connector.stop();
            }));
            
            // Start the connector
            connector.start();
            logger.info("Data Space Connector started");
            
            logger.info("Data space connector is running");
            
        } catch (Exception e) {
            logger.error("Failed to start Eclipse Data Space application", e);
            System.exit(1);
        }
    }
}
