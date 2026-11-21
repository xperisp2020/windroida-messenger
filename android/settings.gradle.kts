pluginManagement {
    repositories {
        // Prefer canonical repositories; avoid a third-party mirror that can fail independently.
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "Windroida"
include(":app")
