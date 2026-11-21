package ir.windroida.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.net.NetworkInterface
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject
import java.net.Inet4Address
import java.util.Collections

/** Keeps the phone's own Windroida messenger server alive while the user explicitly hosts. */
class HostService : Service() {
    companion object {
        const val ACTION_START = "ir.windroida.app.host.START"
        const val ACTION_STOP = "ir.windroida.app.host.STOP"
        private const val CHANNEL = "windroida_host"
        private const val NOTIFICATION_ID = 2
        private const val PREFS = "wd_host"

        fun start(context: Context) {
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit().putBoolean("enabled", true).apply()
            ContextCompat.startForegroundService(
                context, Intent(context, HostService::class.java).setAction(ACTION_START)
            )
        }

        fun stop(context: Context) {
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit().putBoolean("enabled", false).apply()
            context.startService(Intent(context, HostService::class.java).setAction(ACTION_STOP))
        }

        fun isEnabled(context: Context): Boolean =
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean("enabled", false)
    }

    private val prefs by lazy { getSharedPreferences(PREFS, Context.MODE_PRIVATE) }
    private val pythonLock = Any()
    @Volatile private var stopRequested = false
    private var worker: Thread? = null
    private var wakeLock: PowerManager.WakeLock? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        getSystemService(NotificationManager::class.java).createNotificationChannel(
            NotificationChannel(CHANNEL, "میزبانی Windroida", NotificationManager.IMPORTANCE_LOW)
        )
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP || !isEnabled(this)) {
            stopHosting()
            return START_NOT_STICKY
        }

        stopRequested = false
        startForegroundCompat(hostNotification("در حال آماده‌سازی سرور…"))
        acquireWakeLock()
        if (worker?.isAlive != true) {
            worker = Thread({ startHosting() }, "windroida-android-host").also {
                it.isDaemon = true
                it.start()
            }
        }
        return START_STICKY
    }

    private fun startForegroundCompat(notification: Notification) {
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun acquireWakeLock() {
        if (wakeLock?.isHeld == true) return
        try {
            wakeLock = getSystemService(PowerManager::class.java)
                .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Windroida:Host").also {
                    it.setReferenceCounted(false)
                    it.acquire()
                }
        } catch (_: Exception) {
            wakeLock = null
        }
    }

    private fun releaseWakeLock() {
        try {
            wakeLock?.takeIf { it.isHeld }?.release()
        } catch (_: Exception) {
        }
        wakeLock = null
    }

    private fun startHosting() {
        try {
            synchronized(pythonLock) {
                if (stopRequested) return
                if (!Python.isStarted()) Python.start(AndroidPlatform(this))
                if (stopRequested) return

                val addresses = localIPv4Addresses()
                val result = Python.getInstance().getModule("android_host")
                    .callAttr("start_host", filesDir.absolutePath, addresses.joinToString(","))
                    .toString()
                val status = JSONObject(result)
                if (!status.optBoolean("running") || !status.optBoolean("tls")) {
                    throw IllegalStateException("سرور امن شروع نشد")
                }
                if (stopRequested) {
                    Python.getInstance().getModule("android_host").callAttr("stop_host")
                    return
                }
                prefs.edit()
                    .putBoolean("running", true)
                    .putString("ips", addresses.joinToString(","))
                    .putInt("web_port", status.optInt("web_port", 8081))
                    .putInt("tcp_port", status.optInt("tcp_port", 8765))
                    .putString("error", "")
                    .apply()
            }
            updateNotification()
        } catch (error: Throwable) {
            prefs.edit()
                .putBoolean("running", false)
                .putString("error", error.message ?: error.javaClass.simpleName)
                .apply()
            stopRequested = true
            releaseWakeLock()
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
        }
    }

    private fun stopHosting() {
        stopRequested = true
        prefs.edit().putBoolean("running", false).apply()
        Thread({
            synchronized(pythonLock) {
                try {
                    if (Python.isStarted()) {
                        Python.getInstance().getModule("android_host").callAttr("stop_host")
                    }
                } catch (_: Exception) {
                }
            }
            releaseWakeLock()
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
        }, "windroida-stop-host").start()
    }

    private fun localIPv4Addresses(): List<String> {
        return try {
            Collections.list(NetworkInterface.getNetworkInterfaces())
                .filter { it.isUp && !it.isLoopback }
                .flatMap { Collections.list(it.inetAddresses) }
                .filterIsInstance<Inet4Address>()
                .filter { !it.isLoopbackAddress && !it.isLinkLocalAddress && it.isSiteLocalAddress }
                .map { it.hostAddress ?: "" }
                .filter { it.isNotBlank() }
                .distinct()
                .sorted()
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun hostNotification(message: String): Notification {
        val open = PendingIntent.getActivity(
            this, 20, Intent(this, HostActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val stop = PendingIntent.getService(
            this, 21, Intent(this, HostService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, CHANNEL)
            .setSmallIcon(android.R.drawable.stat_sys_upload_done)
            .setContentTitle("Windroida · میزبانی")
            .setContentText(message)
            .setContentIntent(open)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .addAction(android.R.drawable.ic_media_pause, "توقف", stop)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun updateNotification() {
        val ips = prefs.getString("ips", "").orEmpty()
        val message = if (ips.isBlank()) "سرور فعال است؛ فقط روی همین گوشی در دسترس است"
        else "سرور فعال · " + ips.split(",").joinToString("، ")
        getSystemService(NotificationManager::class.java).notify(
            NOTIFICATION_ID, hostNotification(message)
        )
    }

    override fun onDestroy() {
        stopRequested = true
        releaseWakeLock()
        super.onDestroy()
    }
}
