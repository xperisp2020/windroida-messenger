package ir.windroida.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TrustedOriginTest {
    @Test fun sameOriginNormalizesDefaultPortAndCase() {
        assertTrue(TrustedOrigin.sameOrigin("https://Example.COM", "https://example.com:443/profile"))
        assertTrue(TrustedOrigin.sameOrigin("http://example.com:80", "http://EXAMPLE.com/path"))
    }

    @Test fun rejectsPrefixAndUserInfoConfusion() {
        val expected = "https://example.com"
        assertFalse(TrustedOrigin.sameOrigin(expected, "https://example.com.attacker.test/"))
        assertFalse(TrustedOrigin.sameOrigin(expected, "https://example.com@attacker.test/"))
        assertFalse(TrustedOrigin.sameOrigin(expected, "https://attacker.test@example.com/"))
        assertFalse(TrustedOrigin.sameOrigin(expected, "https://example.com./"))
        assertFalse(TrustedOrigin.sameOrigin(expected, "https://example.com:/"))
    }

    @Test fun schemeAndPortArePartOfOrigin() {
        assertFalse(TrustedOrigin.sameOrigin("https://example.com", "http://example.com"))
        assertFalse(TrustedOrigin.sameOrigin("https://example.com:8443", "https://example.com:9443"))
    }

    @Test fun siblingServicesMayShareHostButNotOrigin() {
        assertTrue(TrustedOrigin.sameHostAndScheme("https://example.com:8081", "https://example.com:8084"))
        assertFalse(TrustedOrigin.sameOrigin("https://example.com:8081", "https://example.com:8084"))
        assertFalse(TrustedOrigin.sameHostAndScheme("https://example.com", "http://example.com:8084"))
    }

    @Test fun serviceOriginsRequireKnownPorts() {
        val base = "https://example.com:8081"
        assertTrue(TrustedOrigin.isAllowedService(base, "https://example.com:8081/", setOf(8082, 8084)))
        assertTrue(TrustedOrigin.isAllowedService(base, "https://example.com:8082/", setOf(8082, 8084)))
        assertTrue(TrustedOrigin.isAllowedService(base, "https://example.com:8084/", setOf(8082, 8084)))
        assertFalse(TrustedOrigin.isAllowedService(base, "https://example.com:9999/", setOf(8082, 8084)))
        assertFalse(TrustedOrigin.isAllowedService(base, "http://example.com:8082/", setOf(8082, 8084)))
        assertFalse(TrustedOrigin.isAllowedService(base, "https://attacker.example:8082/", setOf(8082, 8084)))
    }

    @Test fun rejectsNonHttpSchemesAndMalformedAuthorities() {
        assertFalse(TrustedOrigin.sameOrigin("https://example.com", "javascript:alert(1)"))
        assertFalse(TrustedOrigin.sameOrigin("https://example.com", "https://example.com:99999/"))
        assertEquals("https://example.com:443", TrustedOrigin.canonicalOrigin("https://EXAMPLE.com"))
    }
}
