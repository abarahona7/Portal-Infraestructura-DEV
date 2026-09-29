[CmdletBinding()]
param(
    [switch]$Remove
)

$ErrorActionPreference = 'Stop'
$ruleName = 'SimInfra Vite LAN (TCP 5173)'

$currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($currentIdentity)
$isAdministrator = $principal.IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)

if (-not $isAdministrator) {
    throw 'Abre PowerShell como administrador y vuelve a ejecutar este script.'
}

$existingRule = Get-NetFirewallRule `
    -DisplayName $ruleName `
    -ErrorAction SilentlyContinue

if ($Remove) {
    if ($existingRule) {
        $existingRule | Remove-NetFirewallRule
        Write-Host "Regla eliminada: $ruleName"
    }
    else {
        Write-Host "La regla no existe: $ruleName"
    }
    return
}

$nodePath = (Get-Command node.exe -ErrorAction Stop).Source

if ($existingRule) {
    $existingRule | Remove-NetFirewallRule
}

$ruleParameters = @{
    DisplayName = $ruleName
    Description = 'Acceso al frontend Vite de SimInfra desde la subred local.'
    Enabled = 'True'
    Direction = 'Inbound'
    Action = 'Allow'
    Profile = @('Domain', 'Private')
    Program = $nodePath
    Protocol = 'TCP'
    LocalPort = 5173
    RemoteAddress = 'LocalSubnet'
}

New-NetFirewallRule @ruleParameters | Out-Null

Write-Host "Regla configurada: $ruleName"
Write-Host "Programa: $nodePath"
Write-Host 'Puerto: TCP 5173'
Write-Host 'Origen permitido: subred local en perfiles Dominio y Privado'
