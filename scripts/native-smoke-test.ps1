$ErrorActionPreference = "Stop"
$base = "http://192.168.1.200"

Write-Host "Native smoke test @ $base"

$checks = @(
  "/version",
  "/sensor/a1_ph_voltage__v_",
  "/sensor/dallas_temp__c_",
  "/sensor/api_wifi_rssi",
  "/text_sensor/api_wifi_ssid",
  "/text_sensor/kh_status",
  "/text_sensor/kh_mode",
  "/text_sensor/last_error"
)

foreach ($c in $checks) {
  try {
    $r = Invoke-WebRequest -Uri ($base + $c) -UseBasicParsing -TimeoutSec 8
    Write-Host ("OK  " + $c + "  =>  " + $r.Content)
  }
  catch {
    Write-Host ("ERR " + $c + "  =>  " + $_.Exception.Message)
  }
}

Write-Host "Trigger quick 60s..."
Invoke-WebRequest -Uri ($base + "/button/start_kh_quick_60s/press") -Method Post -UseBasicParsing -TimeoutSec 8 | Out-Null
Start-Sleep -Seconds 1
$r1 = Invoke-WebRequest -Uri ($base + "/text_sensor/kh_status") -UseBasicParsing -TimeoutSec 8
$r2 = Invoke-WebRequest -Uri ($base + "/text_sensor/kh_mode") -UseBasicParsing -TimeoutSec 8
Write-Host ("STATUS => " + $r1.Content)
Write-Host ("MODE   => " + $r2.Content)

Write-Host "Stop KH cycle after smoke..."
Invoke-WebRequest -Uri ($base + "/button/kh_stop/press") -Method Post -UseBasicParsing -TimeoutSec 8 | Out-Null
Start-Sleep -Milliseconds 300
$r3 = Invoke-WebRequest -Uri ($base + "/text_sensor/kh_status") -UseBasicParsing -TimeoutSec 8
$r4 = Invoke-WebRequest -Uri ($base + "/text_sensor/kh_mode") -UseBasicParsing -TimeoutSec 8
Write-Host ("STATUS => " + $r3.Content)
Write-Host ("MODE   => " + $r4.Content)

Write-Host "Relay state endpoints check..."
foreach ($s in @("/binary_sensor/p1_active", "/binary_sensor/p2_active", "/binary_sensor/air_active", "/binary_sensor/ads_online")) {
  try {
    $r = Invoke-WebRequest -Uri ($base + $s) -UseBasicParsing -TimeoutSec 8
    Write-Host ("OK  " + $s + "  =>  " + $r.Content)
  }
  catch {
    Write-Host ("ERR " + $s + "  =>  " + $_.Exception.Message)
  }
}
