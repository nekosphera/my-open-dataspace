package org.eclipse.dataspace;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for Data Space Connector
 */
public class DataSpaceConnectorTest {
    private DataSpaceConnector connector;

    @BeforeEach
    public void setUp() {
        connector = new DataSpaceConnector();
    }

    @Test
    public void testInitialization() {
        assertDoesNotThrow(() -> connector.initialize());
    }

    @Test
    public void testStart() {
        connector.initialize();
        assertDoesNotThrow(() -> connector.start());
        assertTrue(connector.isRunning());
    }

    @Test
    public void testStartWithoutInitialization() {
        assertThrows(IllegalStateException.class, () -> connector.start());
    }

    @Test
    public void testStop() {
        connector.initialize();
        connector.start();
        assertTrue(connector.isRunning());
        connector.stop();
        assertFalse(connector.isRunning());
    }

    @Test
    public void testContentDispositionSupportsUnicodeAssetNames() {
        String header = DataSpaceConnector.contentDisposition(
                "↓ROS, IL-1β and García Villalba.pdf",
                "asset-123"
        );

        assertTrue(header.startsWith("attachment; filename=\"_ROS, IL-1_ and Garc_a Villalba.pdf\""));
        assertTrue(header.contains("filename*=UTF-8''%E2%86%93ROS%2C%20IL-1%CE%B2%20and%20Garc%C3%ADa%20Villalba.pdf"));
        assertTrue(header.chars().allMatch(character -> character >= 0x20 && character <= 0x7e));
    }

    @Test
    public void testContentDispositionRemovesHeaderInjectionCharacters() {
        String header = DataSpaceConnector.contentDisposition("report\r\nX-Evil: yes.pdf", "asset-123");

        assertFalse(header.contains("\r"));
        assertFalse(header.contains("\n"));
        assertTrue(header.contains("filename=\"report_X-Evil_ yes.pdf\""));
    }

    @Test
    public void testUnsafeUpstreamContentTypeFallsBackToBinary() {
        assertEquals("application/pdf", DataSpaceConnector.safeContentType("application/pdf"));
        assertEquals("text/csv; charset=utf-8", DataSpaceConnector.safeContentType("text/csv; charset=utf-8"));
        assertEquals("application/octet-stream", DataSpaceConnector.safeContentType("text/plain\r\nX-Evil: yes"));
        assertEquals("application/octet-stream", DataSpaceConnector.safeContentType("not a media type"));
    }
}
