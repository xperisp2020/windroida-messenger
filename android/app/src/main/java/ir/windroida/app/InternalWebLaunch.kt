package ir.windroida.app

import android.content.Intent
import android.util.Base64
import java.security.MessageDigest
import java.security.SecureRandom

/**
 * Authenticates one-off WebView launches initiated by this app process.
 * The nonce is random, in-memory, and consumed exactly once; exported Activity extras alone are never trusted.
 * If Android kills the process between issuing and consuming it, the launch safely fails closed.
 */
object InternalWebLaunch {
    const val EXTRA_NONCE = "wd_internal_nonce"
    @Volatile private var pendingNonce: String? = null

    fun newNonce(): String {
        val bytes = ByteArray(32)
        SecureRandom().nextBytes(bytes)
        return Base64.encodeToString(bytes, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)
    }

    @Synchronized
    fun issue(): String {
        val nonce = newNonce()
        pendingNonce = nonce
        return nonce
    }

    /** Returns the nonce only when it matches the app-process pending value; consumes it once. */
    @Synchronized
    fun consume(intent: Intent?): String? {
        val supplied = intent?.getStringExtra(EXTRA_NONCE) ?: return null
        val expected = pendingNonce ?: return null
        val matches = MessageDigest.isEqual(
            expected.toByteArray(Charsets.UTF_8),
            supplied.toByteArray(Charsets.UTF_8)
        )
        if (!matches) return null
        pendingNonce = null
        return supplied
    }
}
