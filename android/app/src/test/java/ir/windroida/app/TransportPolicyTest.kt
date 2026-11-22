package ir.windroida.app

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TransportPolicyTest {
    @Test fun allowsOnlyPinnedHttps() {
        assertTrue(TransportPolicy.allowsPrivilegedFeatures("https://chat.example:8081", "sha256-pin"))
        assertTrue(TransportPolicy.allowsPrivilegedFeatures("HTTPS://chat.example", "sha256-pin"))
        assertFalse(TransportPolicy.allowsPrivilegedFeatures("http://chat.example:8081", "sha256-pin"))
        assertFalse(TransportPolicy.allowsPrivilegedFeatures("https://chat.example:8081", ""))
        assertFalse(TransportPolicy.allowsPrivilegedFeatures("https://chat.example:8081", null))
        assertFalse(TransportPolicy.allowsPrivilegedFeatures(null, "sha256-pin"))
        assertFalse(TransportPolicy.allowsPrivilegedFeatures("", "sha256-pin"))
    }
}
