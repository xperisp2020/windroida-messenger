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
    val ksPassword = ks("storePassword", "WD_KS_PASS")
    val keyAliasValue = ks("keyAlias", "WD_KEY_ALIAS") ?: "windroida"
    val keyPasswordValue = ks("keyPassword", "WD_KEY_PASS") ?: ksPassword
    val releaseSigningReady = ksFile?.isFile == true &&
        !ksPassword.isNullOrBlank() &&
        keyAliasValue.isNotBlank() &&
        !keyPasswordValue.isNullOrBlank()

    signingConfigs {
        if (releaseSigningReady) {
            create("release") {
                storeFile = ksFile
                storePassword = ksPassword
                keyAlias = keyAliasValue
                keyPassword = keyPasswordValue
            }
        }
    }
    buildTypes {
        release {
            isMinifyEnabled = false
            isShrinkResources = false
            if (releaseSigningReady) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }

    // Fail before executing release task dependencies; the CI no-key guard must not need
    // to compile the complete Android/Python release just to prove signing is mandatory.
    gradle.taskGraph.whenReady {
        if (!releaseSigningReady && allTasks.any {
                it.name == "assembleRelease" || it.name == "packageRelease" || it.name == "bundleRelease"
            }) {
            throw GradleException(
                "Release signing is not configured. Supply keystore.properties or WD_KEYSTORE, WD_KS_PASS, WD_KEY_ALIAS and WD_KEY_PASS. Debug signing is never used for release."
            )
        }
    }

    // Release packaging must never fall back to the public Android debug certificate.
    // Keep debug builds and unit tests available when no owner key is configured.
    project.tasks.configureEach {
        if (name == "packageRelease" || name == "bundleRelease") {
            doFirst {
                if (!releaseSigningReady) {
                    throw GradleException(
                        "Release signing is not configured. Supply keystore.properties or WD_KEYSTORE, WD_KS_PASS, WD_KEY_ALIAS and WD_KEY_PASS. Debug signing is never used for release."
                    )
                }
            }
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
