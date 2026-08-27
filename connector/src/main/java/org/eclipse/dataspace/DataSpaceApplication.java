package org.eclipse.dataspace;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Main application class for Eclipse Data Space Connector with Identity Hub integration
 */
public class DataSpaceApplication {
    private static final Logger logger = LoggerFactory.getLogger(DataSpaceApplication.class);

    public static void main(String[] args) {
        logger.info("Starting Eclipse Data Space Connector with Identity Hub");
        
        try {
            // Initialize the Data Space Connector
            DataSpaceConnector connector = new DataSpaceConnector();
            connector.initialize();
            logger.info("Data Space Connector initialized successfully");
            
            // Initialize Identity Hub
            IdentityHubService identityHub = new IdentityHubService();
            identityHub.initialize();
            logger.info("Identity Hub service initialized successfully");

            Runtime.getRuntime().addShutdownHook(new Thread(() -> {
                logger.info("Shutdown requested. Stopping services...");
                connector.stop();
                identityHub.shutdown();
            }));
            
            // Start the connector
            connector.start();
            logger.info("Data Space Connector started");
            
            logger.info("Eclipse Data Space application is running");
            
        } catch (Exception e) {
            logger.error("Failed to start Eclipse Data Space application", e);
            System.exit(1);
        }
    }
}
