package ir.windroida.app

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class HostNetworkPolicyTest {
    @Test
    fun acceptsOnlyLocalWirelessAndEthernetInterfaces() {
        listOf("wlan0", "swlan0", "wifi0", "eth0", "en0", "ap0", "p2p0").forEach {
            assertTrue("$it should be eligible for LAN hosting", HostService.isLanInterfaceName(it))
        }
    }

    @Test
    fun rejectsCellularVpnLoopbackAndUnknownInterfaces() {
        listOf("rmnet_data0", "ccmni0", "tun0", "ppp0", "lo", "dummy0").forEach {
            assertFalse("$it must not expose the host", HostService.isLanInterfaceName(it))
        }
    }
}
