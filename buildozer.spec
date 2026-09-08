[app]
title = Tehran Shadows
package.name = tehranshadows
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3==3.11.9,kivy==2.3.0
orientation = landscape
fullscreen = 1

# No special permissions are needed (no network, storage, camera, etc.)
android.permissions =

android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
