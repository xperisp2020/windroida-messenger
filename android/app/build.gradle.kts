import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "ir.windroida.app"
    compileSdk = 34
    defaultConfig {
        applicationId = "ir.windroida.app"
        minSdk = 29
        targetSdk = 34
        versionCode = 15
        versionName = "2.3"
    }
    // Release signing is opt-in and must use the owner's private key.
    // Never silently fall back to the public Android debug certificate.
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
        !keyAliasValue.isBlank() &&
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

    // Fail at packaging time when no owner-controlled release key is configured.
    // Debug builds and unit tests remain available without release credentials.
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
}
