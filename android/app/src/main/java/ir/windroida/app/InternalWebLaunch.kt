package ir.windroida.app

import android.content.Context
import android.content.Intent
import android.util.Base64
import org.json.JSONObject
import java.security.SecureRandom

/**
 * Authenticates app-created intents targeting exported MainActivity.
 * Pending launch nonces are app-private, expire, and are consumed exactly once.
 */
object InternalWebLaunch {
    const val EXTRA_NONCE = "wd_internal_nonce"
    private const val PREFS = "wd_internal_launch"
    private const val KEY_PENDING = "pending_nonces"
    private const val TTL_MS = 7L * 24 * 60 * 60 * 1000
    private val lock = Any()

    fun newNonce(): String {
        val bytes = ByteArray(32)
        SecureRandom().nextBytes(bytes)
        return Base64.encodeToString(bytes, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)
    }

    private fun pending(context: Context): Pair<android.content.SharedPreferences, JSONObject> {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val data = try { JSONObject(prefs.getString(KEY_PENDING, "{}") ?: "{}") } catch (_: Exception) { JSONObject() }
        return prefs to data
    }

    /** Create a single-use app-private capability. Multiple notification intents can coexist. */
    fun issue(context: Context): String = synchronized(lock) {
        val (prefs, data) = pending(context)
        val now = System.currentTimeMillis()
        val keys = data.keys()
        val expired = ArrayList<String>()
        while (keys.hasNext()) {
            val key = keys.next()
            if (data.optLong(key, 0L) < now) expired.add(key)
        }
        expired.forEach { data.remove(it) }
        val nonce = newNonce()
        data.put(nonce, now + TTL_MS)
        check(prefs.edit().putString(KEY_PENDING, data.toString()).commit()) {
            "Could not persist internal launch nonce"
        }
        nonce
    }

    /** Returns the nonce only when it matches a pending app-issued value; consumes it once. */
    fun consume(context: Context, intent: Intent?): String? {
        val supplied = intent?.getStringExtra(EXTRA_NONCE) ?: return null
        if (!Regex("[A-Za-z0-9_-]{40,50}").matches(supplied)) return null
        return synchronized(lock) {
            val (prefs, data) = pending(context)
            val expiry = data.optLong(supplied, 0L)
            if (expiry < System.currentTimeMillis()) {
                if (expiry != 0L) {
                    data.remove(supplied)
                    prefs.edit().putString(KEY_PENDING, data.toString()).commit()
                }
                return@synchronized null
            }
            data.remove(supplied)
            if (!prefs.edit().putString(KEY_PENDING, data.toString()).commit()) return@synchronized null
            supplied
        }
    }
}
