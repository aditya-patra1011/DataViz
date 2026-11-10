import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("com.chaquo.python")
}

// The app runs the same core/ package and sample data as the rest of the repo, so there is
// only one copy to maintain. This task brings them into the build.
val syncSharedFiles = tasks.register<Sync>("syncSharedFiles") {
    into(layout.buildDirectory.dir("shared"))
    from(rootProject.file("../core")) {
        include("**/*.py")
        into("python/core")
    }
    from(rootProject.file("../data/samples")) {
        include("*.csv")
        into("assets/samples")
    }
}

tasks.matching {
    it.name != syncSharedFiles.name &&
        (it.name == "preBuild" || it.name.contains("Python") || it.name.contains("Assets"))
}.configureEach { dependsOn(syncSharedFiles) }

android {
    namespace = "com.adityapatra.dataviz"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.adityapatra.dataviz"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "0.1"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    // Python and pandas are built separately for each kind of processor, so each version
    // carries only one copy: "phone" for real Android phones, "emulator" for a laptop.
    flavorDimensions += "device"
    productFlavors {
        create("phone") {
            dimension = "device"
            ndk { abiFilters += "arm64-v8a" }
        }
        create("emulator") {
            dimension = "device"
            ndk { abiFilters += "x86_64" }
        }
    }

    buildTypes {
        getByName("release") {
            // Removes unused Kotlin and library code
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"))
            // Signed with the local debug key so it can be installed directly. Publishing on
            // Google Play would need a private release key instead.
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    buildFeatures {
        compose = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    sourceSets.getByName("main").assets.srcDir(layout.buildDirectory.dir("shared/assets"))
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

chaquopy {
    defaultConfig {
        version = "3.11"
        pip {
            install("-r", rootProject.file("../requirements-android.txt").path)
        }
    }
    sourceSets {
        getByName("main") {
            srcDir(layout.buildDirectory.dir("shared/python").get().asFile)
        }
    }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2025.10.01"))
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.11.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.9.4")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.10.2")

    androidTestImplementation("androidx.test:core:1.7.0")
    androidTestImplementation("androidx.test:runner:1.7.0")
    androidTestImplementation("androidx.test.ext:junit:1.3.0")
}
