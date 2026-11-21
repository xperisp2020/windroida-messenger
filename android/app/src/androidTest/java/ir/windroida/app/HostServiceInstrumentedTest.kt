package ir.windroida.app

import android.content.Context
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.IOException
import java.net.InetSocketAddress
import java.net.Socket
import java.net.URL
import java.security.SecureRandom
import java.security.cert.X509Certificate
import javax.net.ssl.HttpsURLConnection
import javax.net.ssl.SSLContext
import javax.net.ssl.X509TrustManager
import javax.net.ssl.TrustManager

@RunWith(AndroidJUnit4::class)
class HostServiceInstrumentedTest {
    @Test
    fun startsHttpsMessengerHostAndStopsAllListeners() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val scenario = ActivityScenario.launch(HostActivity::class.java)
        val prefs = context.getSharedPreferences("wd_host", Context.MODE_PRIVATE)
        var webPort = 8081
        var tcpPort = 8765
        try {
            HostService.start(context)
            val startDeadline = System.currentTimeMillis() + 120_000
            while (!prefs.getBoolean("running", false) && System.currentTimeMillis() < startDeadline) {
                val error = prefs.getString("error", "").orEmpty()
                if (error.isNotBlank()) throw AssertionError("Android host failed to start: $error")
                Thread.sleep(250)
            }
            assertTrue("Android foreground host did not become ready", prefs.getBoolean("running", false))
            webPort = prefs.getInt("web_port", 8081)
            tcpPort = prefs.getInt("tcp_port", 8765)
            assertTrue("Messenger TCP listener did not open", canConnect(tcpPort))

            val connection = URL("https://127.0.0.1:$webPort/").openConnection() as HttpsURLConnection
            connection.sslSocketFactory = trustAllContext().socketFactory
            connection.connectTimeout = 8_000
            connection.readTimeout = 8_000
            try {
                assertEquals(200, connection.responseCode)
                val page = connection.inputStream.bufferedReader().use { it.readText() }
                assertTrue("Bundled Windroida web client was not served", page.contains("Windroida", ignoreCase = true))
                assertTrue("Initial owner credential file was not created",
                    java.io.File(context.filesDir, "windroida/data/admin_password.txt").isFile)
            } finally {
                connection.disconnect()
            }
        } finally {
            HostService.stop(context)
            scenario.close()
        }

        val stopDeadline = System.currentTimeMillis() + 30_000
        var stillListening = true
        while (stillListening && System.currentTimeMillis() < stopDeadline) {
            stillListening = canConnect(webPort)
            if (stillListening) Thread.sleep(250)
        }
        assertFalse("HTTPS listener remained open after stopping the host", stillListening)
        assertFalse("Messenger TCP listener remained open after stopping the host", canConnect(tcpPort))
        assertFalse("Host service still reports running", prefs.getBoolean("running", false))
    }

    private fun canConnect(port: Int): Boolean {
        return try {
            Socket().use { it.connect(InetSocketAddress("127.0.0.1", port), 500) }
            true
        } catch (_: IOException) {
            false
        }
    }

    private fun trustAllContext(): SSLContext {
        val trust = object : X509TrustManager {
            override fun checkClientTrusted(chain: Array<X509Certificate>, authType: String) = Unit
            override fun checkServerTrusted(chain: Array<X509Certificate>, authType: String) = Unit
            override fun getAcceptedIssuers(): Array<X509Certificate> = emptyArray()
        }
        return SSLContext.getInstance("TLS").apply {
            init(null, arrayOf<TrustManager>(trust), SecureRandom())
        }
    }
}
