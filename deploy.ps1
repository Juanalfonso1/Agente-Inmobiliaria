param(
    [string]$m = "update rapido"
)

Write-Host "Agregando cambios..."
git add .

Write-Host "Creando commit..."
git commit -m $m

Write-Host "Subiendo a GitHub..."
git push origin main

Write-Host "Deploy completado."
