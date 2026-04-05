$ErrorActionPreference = "Stop"
$base = "http://192.168.1.200"

function Test-EndpointLatency {
  param(
    [string]$Path,
    [int]$Count = 60
  )

  $samples = New-Object System.Collections.Generic.List[Double]
  $errors = 0

  for ($i = 0; $i -lt $Count; $i++) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
      Invoke-WebRequest -Uri ($base + $Path) -UseBasicParsing -TimeoutSec 5 | Out-Null
      $sw.Stop()
      $samples.Add($sw.Elapsed.TotalMilliseconds)
    }
    catch {
      $sw.Stop()
      $errors++
    }
  }

  if ($samples.Count -eq 0) {
    return [PSCustomObject]@{
      path = $Path; ok = 0; errors = $errors; min_ms = $null; avg_ms = $null; p95_ms = $null; max_ms = $null
    }
  }

  $arr = $samples.ToArray() | Sort-Object
  $min = [Math]::Round($arr[0], 2)
  $max = [Math]::Round($arr[$arr.Length - 1], 2)
  $avg = [Math]::Round(($arr | Measure-Object -Average).Average, 2)
  $idx95 = [Math]::Floor(($arr.Length - 1) * 0.95)
  $p95 = [Math]::Round($arr[$idx95], 2)

  return [PSCustomObject]@{
    path = $Path; ok = $samples.Count; errors = $errors; min_ms = $min; avg_ms = $avg; p95_ms = $p95; max_ms = $max
  }
}

Write-Host "Warmup..."
1..5 | ForEach-Object { Invoke-WebRequest -Uri ($base + "/sensor/main_ph") -UseBasicParsing -TimeoutSec 5 | Out-Null; Start-Sleep -Milliseconds 120 }

$targets = @(
  "/sensor/main_ph",
  "/sensor/a1_ph_voltage__v_",
  "/sensor/dallas_temp__c_",
  "/text_sensor/kh_status",
  "/diag/metrics"
)

$results = @()
foreach ($t in $targets) {
  $results += Test-EndpointLatency -Path $t -Count 80
}

Write-Host ""
Write-Host "Latency benchmark:"
$results | Format-Table -AutoSize

Write-Host ""
Write-Host "Device metrics:"
try {
  $m = Invoke-WebRequest -Uri ($base + "/diag/metrics") -UseBasicParsing -TimeoutSec 8
  $m.Content
}
catch {
  Write-Host ("ERR metrics => " + $_.Exception.Message)
}

