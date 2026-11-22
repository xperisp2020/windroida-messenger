package ir.windroida.app

/** Fail-closed allowlist for WebView permission resources. */
object WebPermissionPolicy {
    fun allowedResources(requested: Array<String>, audioCapture: String, videoCapture: String): Array<String>? {
        if (requested.isEmpty() || requested.any { it != audioCapture && it != videoCapture }) return null
        return requested
    }
}
