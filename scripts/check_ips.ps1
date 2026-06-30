Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike '127.*' } |
    Select-Object InterfaceAlias, InterfaceIndex, IPAddress, PrefixLength, PrefixOrigin |
    Format-Table -AutoSize

Write-Host '--- 172.65.* ---'
Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -like '172.65.*' } |
    Format-Table -AutoSize

Write-Host '--- DHCP on connected ---'
Get-NetIPInterface -AddressFamily IPv4 |
    Where-Object { $_.ConnectionState -eq 'Connected' } |
    Select-Object InterfaceIndex, InterfaceAlias, Dhcp |
    Format-Table -AutoSize

Write-Host '--- DNS ---'
Get-DnsClientServerAddress -AddressFamily IPv4 |
    Where-Object { $_.ServerAddresses } |
    Select-Object InterfaceIndex, InterfaceAlias, ServerAddresses |
    Format-Table -AutoSize
