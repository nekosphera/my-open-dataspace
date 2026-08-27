package org.eclipse.dataspace;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for Identity Hub Service
 */
public class IdentityHubServiceTest {
    private IdentityHubService identityHub;

    @BeforeEach
    public void setUp() {
        identityHub = new IdentityHubService();
    }

    @AfterEach
    public void tearDown() {
        identityHub.shutdown();
    }

    @Test
    public void testInitialization() {
        assertDoesNotThrow(() -> identityHub.initialize());
    }

    @Test
    public void testRegisterParticipant() {
        identityHub.initialize();
        assertTrue(identityHub.registerParticipant("participant-1", "VerifiableCredential"));
    }

    @Test
    public void testRegisterParticipantWithoutInitialization() {
        assertThrows(IllegalStateException.class, 
            () -> identityHub.registerParticipant("participant-1", "VerifiableCredential"));
    }

    @Test
    public void testIssueCredential() {
        identityHub.initialize();
        identityHub.registerParticipant("participant-1", "VerifiableCredential");
        String credentialId = identityHub.issueCredential("participant-1", "credential-data");
        assertNotNull(credentialId);
        assertTrue(credentialId.startsWith("cred_"));
    }

    @Test
    public void testVerifyCredential() {
        identityHub.initialize();
        identityHub.registerParticipant("participant-1", "VerifiableCredential");
        String credentialId = identityHub.issueCredential("participant-1", "credential-data");
        assertTrue(identityHub.verifyCredential(credentialId));
    }

    @Test
    public void testIssueCredentialForUnknownParticipantReturnsNull() {
        identityHub.initialize();
        assertNull(identityHub.issueCredential("missing-participant", "credential-data"));
    }
}
