package ir.windroida.app

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.assertFalse
import org.junit.Test

class WebPermissionPolicyTest {
    @Test fun allowsOnlyKnownCaptureResources() {
        assertArrayEquals(arrayOf("audio"), WebPermissionPolicy.allowedResources(arrayOf("audio"), "audio", "video"))
        assertArrayEquals(arrayOf("audio", "video"), WebPermissionPolicy.allowedResources(arrayOf("audio", "video"), "audio", "video"))
    }

    @Test fun rejectsUnknownOrEmptyResources() {
        assertNull(WebPermissionPolicy.allowedResources(emptyArray(), "audio", "video"))
        assertNull(WebPermissionPolicy.allowedResources(arrayOf("unknown"), "audio", "video"))
        assertNull(WebPermissionPolicy.allowedResources(arrayOf("audio", "unknown"), "audio", "video"))
    }

    @Test fun pendingGrantRequiresSameTrustedLivePageAndRuntimeGrants() {
        assertTrue(WebPermissionPolicy.canGrantPending(true, true, true, true))
        assertFalse(WebPermissionPolicy.canGrantPending(false, true, true, true))
        assertFalse(WebPermissionPolicy.canGrantPending(true, false, true, true))
        assertFalse(WebPermissionPolicy.canGrantPending(true, true, false, true))
        assertFalse(WebPermissionPolicy.canGrantPending(true, true, true, false))
    }
}
