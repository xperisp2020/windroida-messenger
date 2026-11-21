package ir.windroida.app

import android.app.Activity
import android.app.AlertDialog
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import java.io.File
import java.security.MessageDigest
import java.security.cert.CertificateFactory
import java.security.cert.X509Certificate

/** Local controls for starting and managing this phone's Windroida host. */
class HostActivity : Activity() {
    private lateinit var status: TextView
    private lateinit var addresses: TextView
    private lateinit var credentials: TextView
    private lateinit var startButton: Button
    private lateinit var stopButton: Button
    private lateinit var copyAddressButton: Button
    private lateinit var copyCertificateButton: Button
    private lateinit var fingerprintText: TextView
    private lateinit var copyFingerprintButton: Button
    private lateinit var copyCredentialsButton: Button
    private lateinit var deleteCredentialsButton: Button
    private lateinit var useNativeButton: Button
    private lateinit var useWebButton: Button
    private lateinit var restoreButton: Button

    private val handler = Handler(Looper.getMainLooper())
    private val refresh = object : Runnable {
        override fun run() {
            render()
            handler.postDelayed(this, 900)
        }
    }

    private val hostPrefs by lazy { getSharedPreferences("wd_host", Context.MODE_PRIVATE) }
    private val returnPrefs by lazy { getSharedPreferences("wd_host_return", Context.MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        title = "میزبانی Windroida"
        val density = resources.displayMetrics.density
        fun dp(value: Int) = (value * density).toInt()
        fun text(value: String, size: Float, bold: Boolean = false): TextView =
            TextView(this).apply {
                this.text = value
                textSize = size
                setTextColor(Color.WHITE)
                if (bold) setTypeface(typeface, android.graphics.Typeface.BOLD)
                setPadding(0, dp(7), 0, dp(7))
            }
        fun button(value: String, action: () -> Unit) = Button(this).apply {
            text = value
            isAllCaps = false
            setOnClickListener { action() }
        }

        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(22), dp(20), dp(28))
            setBackgroundColor(Color.rgb(15, 20, 36))
        }
        column.addView(text("میزبانی روی همین گوشی", 23f, true))
        column.addView(text(
            "با فعال‌کردن میزبانی، گوشی سرور پیام‌رسان و چت می‌شود و کاربران دیگر از طریق شبکه محلی وصل می‌شوند. سرویس‌های Ghab و Cloud Drive در میزبان اندرویدی هنوز فعال نیستند. میزبانی مداوم باتری مصرف می‌کند؛ برای پایداری، گوشی را به شارژ وصل و محدودیت باتری برنامه را بردار.",
            14f
        ))
        status = text("در حال بررسی وضعیت…", 15f, true)
        column.addView(status)
        addresses = text("", 14f)
        addresses.textDirection = TextView.TEXT_DIRECTION_LTR
        addresses.setTextIsSelectable(true)
        column.addView(addresses)
        startButton = button("شروع میزبانی") { HostService.start(this) }
        stopButton = button("توقف میزبانی") { HostService.stop(this) }
        column.addView(startButton)
        column.addView(stopButton)
        copyAddressButton = button("کپی آدرس اتصال") {
            val value = firstHostUrl()
            if (value.isNotBlank()) copy(value, "آدرس سرور کپی شد")
            else toast("ابتدا میزبانی را شروع کن")
        }
        column.addView(copyAddressButton)
        copyCertificateButton = button("کپی لینک گواهی TLS برای ویندوز") {
            val value = firstCertificateUrl()
            if (value.isNotBlank()) copy(value, "لینک گواهی TLS کپی شد")
            else toast("ابتدا میزبانی را شروع کن")
        }
        column.addView(copyCertificateButton)
        fingerprintText = text("اثر انگشت گواهی: پس از شروع نمایش داده می‌شود.", 12f)
        fingerprintText.textDirection = TextView.TEXT_DIRECTION_LTR
        fingerprintText.setTextIsSelectable(true)
        column.addView(fingerprintText)
        copyFingerprintButton = button("کپی اثر انگشت گواهی") {
            val value = readCertificateFingerprint()
            if (value.isNotBlank()) copy(value, "اثر انگشت گواهی کپی شد")
            else toast("گواهی هنوز آماده نیست")
        }
        column.addView(copyFingerprintButton)
        column.addView(text(
            "لینک دریافت گواهی فقط برای راه‌اندازی اولیه از HTTP استفاده می‌کند؛ خود پیام‌رسان فقط از HTTPS امن استفاده می‌کند. پیش از نصب گواهی در ویندوز، اثر انگشت فایل دریافت‌شده را با مقدار نمایش‌داده‌شده در این صفحه مقایسه کن.",
            12f
        ))
        column.addView(text("حساب مالک سرور", 18f, true))
        credentials = text("", 14f)
        credentials.textDirection = TextView.TEXT_DIRECTION_LTR
        credentials.setTextIsSelectable(true)
        column.addView(credentials)
        copyCredentialsButton = button("کپی اطلاعات حساب مالک") {
            val value = adminCredentials()
            if (value.isNotBlank()) copy(value, "اطلاعات حساب کپی شد")
            else toast("اطلاعات رمز اولیه موجود نیست؛ از رمز فعلی حساب مالک استفاده کن")
        }
        column.addView(copyCredentialsButton)
        deleteCredentialsButton = button("حذف فایل رمز اولیه") {
            AlertDialog.Builder(this)
                .setTitle("حذف رمز اولیه")
                .setMessage("فایل رمز اولیه از فضای خصوصی برنامه حذف شود؟ قبل از حذف، مطمئن شو رمز مالک را یادداشت کرده‌ای.")
                .setNegativeButton("انصراف", null)
                .setPositiveButton("حذف") { _, _ ->
                    val file = File(filesDir, "windroida/data/admin_password.txt")
                    if (file.delete()) toast("فایل رمز اولیه حذف شد") else toast("فایلی برای حذف وجود ندارد")
                    render()
                }
                .show()
        }
        column.addView(deleteCredentialsButton)
        column.addView(text(
            "رمز اولیه فقط در فضای خصوصی برنامه نگهداری می‌شود. پس از یادداشت‌کردن و تغییر رمز، فایل رمز اولیه را حذف کن.",
            12f
        ))
        column.addView(text("اتصال خود گوشی به میزبان", 18f, true))
        useNativeButton = button("استفاده از این سرور در نسخه بومی") { useLocalHost("native") }
        useWebButton = button("مدیریت سرور در نسخه وب") { useLocalHost("web") }
        column.addView(useNativeButton)
        column.addView(useWebButton)
        restoreButton = button("بازگشت به سرور قبلی") { restorePreviousServer() }
        column.addView(restoreButton)
        column.addView(text(
            "این مرحله اتصال در شبکه محلی را فراهم می‌کند. دسترسی از اینترنت، دعوت‌نامه امن، عبور از NAT و QR هنوز در حال توسعه‌اند.",
            12f
        ))

        val scroll = ScrollView(this)
        scroll.addView(column)
        setContentView(scroll)
        render()
    }

    override fun onResume() {
        super.onResume()
        handler.removeCallbacks(refresh)
        handler.post(refresh)
    }

    override fun onPause() {
        handler.removeCallbacks(refresh)
        super.onPause()
    }

    private fun render() {
        val running = hostPrefs.getBoolean("running", false)
        val enabled = HostService.isEnabled(this)
        val error = hostPrefs.getString("error", "").orEmpty()
        val ips = hostPrefs.getString("ips", "").orEmpty().split(",").filter { it.isNotBlank() }
        val port = hostPrefs.getInt("web_port", 8081)
        status.text = when {
            running -> "وضعیت: سرور فعال و HTTPS روشن است"
            error.isNotBlank() -> "خطا در شروع سرور: $error"
            enabled -> "وضعیت: در حال شروع سرور…"
            else -> "وضعیت: متوقف"
        }
        addresses.text = if (running) {
            if (ips.isEmpty()) "آدرس شبکه پیدا نشد؛ اتصال محلی: https://127.0.0.1:$port"
            else ips.joinToString("\n") { "https://$it:$port" }
        } else "پس از شروع میزبانی، آدرس‌های اتصال اینجا نمایش داده می‌شوند."
        val fingerprint = readCertificateFingerprint()
        fingerprintText.text = if (fingerprint.isBlank()) "اثر انگشت گواهی: در دسترس نیست" else "SHA-256: $fingerprint"
        copyFingerprintButton.isEnabled = running && fingerprint.isNotBlank()
        val credentialsText = adminCredentials()
        credentials.text = if (credentialsText.isNotBlank()) credentialsText
        else "رمز اولیه جدیدی وجود ندارد. از رمز فعلی حساب مالک استفاده کن."
        startButton.isEnabled = !enabled
        stopButton.isEnabled = enabled
        copyAddressButton.isEnabled = running && ips.isNotEmpty()
        copyCertificateButton.isEnabled = running && ips.isNotEmpty()
        copyCredentialsButton.isEnabled = credentialsText.isNotBlank()
        deleteCredentialsButton.isEnabled = credentialsText.isNotBlank()
        useNativeButton.isEnabled = running
        useWebButton.isEnabled = running
        restoreButton.isEnabled = returnPrefs.getBoolean("saved", false)
    }

    private fun firstHostUrl(): String {
        val ip = hostPrefs.getString("ips", "").orEmpty().split(",").firstOrNull { it.isNotBlank() }
            ?: return ""
        return "https://$ip:${hostPrefs.getInt("web_port", 8081)}"
    }

    private fun firstCertificateUrl(): String {
        val url = firstHostUrl()
        return if (url.isBlank()) "" else url.replaceFirst("https://", "http://") + "/windroida.crt"
    }

    private fun readCertificateFingerprint(): String {
        val file = File(filesDir, "windroida/data/server.crt")
        return try {
            if (!file.isFile) return ""
            val certificate = file.inputStream().use {
                CertificateFactory.getInstance("X.509").generateCertificate(it) as X509Certificate
            }
            MessageDigest.getInstance("SHA-256").digest(certificate.encoded)
                .joinToString(":") { "%02X".format(it) }
        } catch (_: Exception) {
            ""
        }
    }

    private fun adminCredentials(): String {
        val file = File(filesDir, "windroida/data/admin_password.txt")
        return try {
            if (file.isFile) file.readText(Charsets.UTF_8).trim() else ""
        } catch (_: Exception) {
            ""
        }
    }

    private fun copy(value: String, message: String) {
        val clipboard = getSystemService(ClipboardManager::class.java)
        clipboard.setPrimaryClip(ClipData.newPlainText("Windroida", value))
        toast(message)
    }

    private fun toast(message: String) = Toast.makeText(this, message, Toast.LENGTH_SHORT).show()

    private fun useLocalHost(mode: String) {
        if (!hostPrefs.getBoolean("running", false)) {
            toast("ابتدا میزبانی را شروع کن")
            return
        }
        if (!returnPrefs.getBoolean("saved", false)) {
            returnPrefs.edit()
                .putBoolean("saved", true)
                .putString("server", Prefs.server(this))
                .putString("pin", Prefs.pin(this))
                .putString("token", Prefs.token(this))
                .putString("mode", Prefs.mode(this))
                .putInt("drive_port", getSharedPreferences("wd", Context.MODE_PRIVATE).getInt("drive_port", 0))
                .putInt("ghab_port", getSharedPreferences("wd", Context.MODE_PRIVATE).getInt("ghab_port", 0))
                .apply()
        }
        val port = hostPrefs.getInt("web_port", 8081)
        Prefs.setServer(this, "https://127.0.0.1:$port")
        Prefs.setPin(this, "")
        Prefs.setToken(this, "")
        Prefs.setMode(this, mode)
        val target = if (mode == "web") MainActivity::class.java else NativeActivity::class.java
        startActivity(Intent(this, target).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK))
        finish()
    }

    private fun restorePreviousServer() {
        if (!returnPrefs.getBoolean("saved", false)) return
        Prefs.setServer(this, returnPrefs.getString("server", "").orEmpty())
        Prefs.setPin(this, returnPrefs.getString("pin", "").orEmpty())
        Prefs.setToken(this, returnPrefs.getString("token", "").orEmpty())
        getSharedPreferences("wd", Context.MODE_PRIVATE).edit()
            .putInt("drive_port", returnPrefs.getInt("drive_port", 0))
            .putInt("ghab_port", returnPrefs.getInt("ghab_port", 0))
            .apply()
        val mode = returnPrefs.getString("mode", "native").orEmpty()
        Prefs.setMode(this, mode)
        returnPrefs.edit().clear().apply()
        val target = if (mode == "web") MainActivity::class.java else NativeActivity::class.java
        startActivity(Intent(this, target).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK))
        finish()
    }
}
