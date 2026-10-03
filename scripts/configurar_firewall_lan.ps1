[CmdletBinding()]
param(
    [switch]$Remove
)

$ErrorActionPreference = 'Stop'
$ruleName = 'SimInfra Vite LAN (TCP 5178)'
$legacyRuleName = 'SimInfra Vite LAN (TCP 5176)'

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
$legacyRule = Get-NetFirewallRule `
    -DisplayName $legacyRuleName `
    -ErrorAction SilentlyContinue

if ($Remove) {
    foreach ($rule in @($existingRule, $legacyRule)) {
        if ($rule) {
            $rule | Remove-NetFirewallRule
            Write-Host "Regla eliminada: $($rule.DisplayName)"
        }
    }
    if (-not $existingRule -and -not $legacyRule) {
        Write-Host 'No existen reglas de Vite para los puertos 5178 o 5176.'
    }
    return
}

$nodePath = (Get-Command node.exe -ErrorAction Stop).Source

if ($existingRule) {
    $existingRule | Remove-NetFirewallRule
}
if ($legacyRule) {
    $legacyRule | Remove-NetFirewallRule
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
    LocalPort = 5178
    RemoteAddress = 'LocalSubnet'
}

New-NetFirewallRule @ruleParameters | Out-Null

Write-Host "Regla configurada: $ruleName"
Write-Host "Programa: $nodePath"
Write-Host 'Puerto: TCP 5178'
Write-Host 'Origen permitido: subred local en perfiles Dominio y Privado'
