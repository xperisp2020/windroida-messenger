package ir.windroida.app

import java.net.URI
import java.util.Locale

/** Strict URL-origin comparisons shared by WebViews, downloads and the offline cache. */
object TrustedOrigin {
    private data class Origin(val scheme: String, val host: String, val port: Int)

    private fun parse(raw: String?): Origin? {
        return try {
            if (raw.isNullOrBlank() || raw.any { it.isWhitespace() || it.code < 0x20 }) return null
            val uri = URI(raw)
            if (!uri.isAbsolute || uri.isOpaque || uri.rawUserInfo != null || uri.rawAuthority.isNullOrEmpty()) return null
            if (uri.rawAuthority.endsWith(":")) return null
            val scheme = uri.scheme?.lowercase(Locale.ROOT) ?: return null
            if (scheme != "http" && scheme != "https") return null
            val rawHost = uri.host ?: return null
            if (rawHost.isBlank()) return null
            val host = rawHost.lowercase(Locale.ROOT)
            val port = when {
                uri.port == -1 && scheme == "https" -> 443
                uri.port == -1 && scheme == "http" -> 80
                uri.port in 1..65535 -> uri.port
                else -> return null
            }
            Origin(scheme, host, port)
        } catch (_: Exception) {
            null
        }
    }

    fun sameOrigin(expected: String?, candidate: String?): Boolean {
        val a = parse(expected)
        return a != null && a == parse(candidate)
    }

    /** Used only for the sibling Ghab/Drive services which intentionally use a different port. */
    fun sameHostAndScheme(expected: String?, candidate: String?): Boolean {
        val a = parse(expected) ?: return false
        val b = parse(candidate) ?: return false
        return a.scheme == b.scheme && a.host == b.host
    }

    fun canonicalOrigin(raw: String?): String? {
        val o = parse(raw) ?: return null
        val host = if (o.host.contains(':') && !o.host.startsWith("[")) "[${o.host}]" else o.host
        return "${o.scheme}://${host}:${o.port}"
    }
}
