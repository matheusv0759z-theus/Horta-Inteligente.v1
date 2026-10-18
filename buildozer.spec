[app]
title = Horta Inteligente
package.name = hortainteligente
package.domain = org.hortainteligente
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 0.2.0
requirements = python3,kivy
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE
android.api = 35
android.minapi = 26
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
