import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}
android {
    namespace = "ir.windroida.app"
    compileSdk = 34
    defaultConfig {
        applicationId = "ir.windroida.app"
        minSdk = 29
        targetSdk = 34
        versionCode = 16
        versionName = "2.4"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        ndk { abiFilters += listOf("armeabi-v7a", "arm64-v8a", "x86_64") }
    }
    sourceSets.getByName("main").assets.srcDir(layout.buildDirectory.dir("generated/host-assets"))
    // A permanent release key of YOUR own (see README-android.md, "امضای ثابت"): Play Protect distrusts debug-signed apps far more.
    // The key never lives in the project: it is read from keystore.properties (local build) or WD_* environment variables (GitHub secrets).
    val ksProps = Properties().apply {
        val f = rootProject.file("keystore.properties")
        if (f.exists()) f.inputStream().use { this.load(it) }
    }
    fun ks(name: String, env: String): String? = ksProps.getProperty(name) ?: System.getenv(env)
    val ksFile = ks("storeFile", "WD_KEYSTORE")?.let { rootProject.file(it) }
    signingConfigs {
        if (ksFile != null && ksFile.exists()) {
            create("release") {
                storeFile = ksFile
                storePassword = ks("storePassword", "WD_KS_PASS")
                keyAlias = ks("keyAlias", "WD_KEY_ALIAS") ?: "windroida"
                keyPassword = ks("keyPassword", "WD_KEY_PASS") ?: ks("storePassword", "WD_KS_PASS")
            }
        }
    }
    buildTypes {
        release {
            isMinifyEnabled = false          // no obfuscation: obfuscated code is itself something scanners distrust
            isShrinkResources = false
            signingConfig = signingConfigs.findByName("release") ?: signingConfigs.getByName("debug")
        }
    }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
}

val syncHostPython = tasks.register<Copy>("syncHostPython") {
    val repoRoot = rootProject.projectDir.parentFile
    from(repoRoot) {
        include(
            "server.py", "common.py", "host_capacity.py", "webgw.py",
            "rooms.py", "mafia_room.py", "mensch_room.py", "mafia.py", "mensch.py",
            "groupadmin.py", "polls.py", "social.py", "chess.py", "games.py"
        )
    }
    into(layout.buildDirectory.dir("generated/chaquopy/main"))
}

val syncHostWebAssets = tasks.register<Copy>("syncHostWebAssets") {
    from(rootProject.projectDir.parentFile.resolve("web"))
    into(layout.buildDirectory.dir("generated/host-assets/windroida-web"))
}

chaquopy {
    defaultConfig {
        version = "3.11"
        pip {
            install("Pillow==11.0.0")
            install("cryptography==42.0.8")
        }
    }
    sourceSets {
        getByName("main") {
            srcDir(layout.buildDirectory.dir("generated/chaquopy/main"))
        }
    }
}

tasks.named("preBuild").configure { dependsOn(syncHostPython, syncHostWebAssets) }
tasks.configureEach {
    if (name.endsWith("PythonSources")) dependsOn(syncHostPython)
    if (name.startsWith("merge") && name.endsWith("Assets")) dependsOn(syncHostWebAssets)
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    // Lottie's LottieAnimationView extends AppCompatImageView: without this the build fails with "Supertypes ... cannot be resolved" in TEmoji.kt
    implementation("androidx.appcompat:appcompat:1.7.0")
    // native video player (plays videos of the chat; uses the pinned certificate through OkHttp)
    implementation("androidx.media3:media3-exoplayer:1.4.1")
    implementation("androidx.media3:media3-ui:1.4.1")
    implementation("androidx.media3:media3-datasource-okhttp:1.4.1")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    // Telegram's animated emoji (Lottie files in assets/emoji)
    implementation("com.airbnb.android:lottie:6.4.0")
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test:core:1.6.1")
}
