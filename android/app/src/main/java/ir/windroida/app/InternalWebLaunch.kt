package ir.windroida.app

import android.content.Context
import android.content.Intent
import java.security.MessageDigest
import java.security.SecureRandom
import android.util.Base64

/**
 * Authenticates one-off WebView launches initiated by the app itself.
 * The nonce is stored in app-private preferences and consumed exactly once;
 * exported Activity extras alone are never trusted.
 */
object InternalWebLaunch {
    const val EXTRA_NONCE = "wd_internal_nonce"
    private const val PREFS = "wd_internal_launch"
    private const val KEY_PENDING = "pending_nonce"

    fun newNonce(): String {
        val bytes = ByteArray(32)
        SecureRandom().nextBytes(bytes)
        return Base64.encodeToString(bytes, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)
    }

    fun issue(context: Context): String {
        val nonce = newNonce()
        check(context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY_PENDING, nonce).commit()) {
            "Could not persist internal WebView launch nonce"
        }
        return nonce
    }

    /** Returns the nonce only when it matches the app-private pending value; consumes it once. */
    fun consume(context: Context, intent: Intent?): String? {
        val supplied = intent?.getStringExtra(EXTRA_NONCE) ?: return null
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val expected = prefs.getString(KEY_PENDING, null) ?: return null
        val matches = MessageDigest.isEqual(
            expected.toByteArray(Charsets.UTF_8),
            supplied.toByteArray(Charsets.UTF_8)
        )
        if (!matches) return null
        if (!prefs.edit().remove(KEY_PENDING).commit()) return null
        return supplied
    }
}
