while ($true) {
    docker info 2>&1 | Out-Null
    if ($?) {
        Write-Host "Docker is up!"
        break
    }
    Write-Host "Waiting for docker..."
    Start-Sleep -Seconds 2
}
docker compose build 2>&1
docker compose up -d
