# Recuperar un nodo al que ya no puedes entrar, desde PowerShell.
#
#     .\reiniciar.ps1 --contrasena <correo>   la contraseña de alguien
#     .\reiniciar.ps1 --asistente             volver a /setup, sin perder datos
#     .\reiniciar.ps1 --todo                  borrarlo todo y empezar de cero
#
# El guion de verdad es reiniciar.sh, y PowerShell no ejecuta ficheros .sh:
# escribir `.\reiniciar.sh` ahí no da error ni salida, no hace nada. Esto sólo
# llama a bash por ti.
$ErrorActionPreference = 'Stop'

$bash = (Get-Command bash -ErrorAction SilentlyContinue).Source
if (-not $bash) {
  Write-Error @'
No hay `bash` en el PATH. Viene con Git para Windows:
  https://git-scm.com/download/win
Después vuelve a intentarlo, o abre Git Bash y usa ./reiniciar.sh
'@
  exit 1
}

# Ruta relativa y el directorio del guion como cwd: el bash de Git no entiende
# una ruta `C:\...` como argumento y contestaría «No such file or directory».
# La ayuda del guion nombra `./reiniciar.sh`, que es su forma en bash. Desde
# aqui la forma es esta, y se dice antes de que aparezca aquella.
if ($args.Count -eq 0) {
  Write-Host 'Desde PowerShell:  .\reiniciar.ps1 --contrasena <correo> | --asistente | --todo'
  Write-Host ''
}

Push-Location $PSScriptRoot
try {
  & $bash 'reiniciar.sh' @args
  exit $LASTEXITCODE
} finally {
  Pop-Location
}
