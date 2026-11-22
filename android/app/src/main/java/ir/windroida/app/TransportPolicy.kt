package ir.windroida.app

/** Native credentials and privileged Android capabilities are permitted only on a pinned HTTPS origin. */
object TransportPolicy {
    fun allowsPrivilegedFeatures(server: String?, certificatePin: String?): Boolean =
        !server.isNullOrBlank() &&
            server.startsWith("https://", ignoreCase = true) &&
            !certificatePin.isNullOrBlank()
}
