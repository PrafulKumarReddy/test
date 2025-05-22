# Login and set context if needed
Connect-AzAccount
Set-AzContext -Subscription "Your-Subscription-Name"

# Get all resource groups
$resourceGroups = Get-AzResourceGroup

foreach ($rg in $resourceGroups) {
    $lbs = Get-AzLoadBalancer -ResourceGroupName $rg.ResourceGroupName | Where-Object { $_.FrontendIpConfigurations[0].PrivateIpAddress -ne $null }

    foreach ($lb in $lbs) {
        Write-Output "`nLoad Balancer: $($lb.Name) in RG: $($rg.ResourceGroupName)"

        $hasHA = $false
        foreach ($rule in $lb.LoadBalancingRules) {
            if ($rule.EnableTcpReset -eq $true -and $rule.EnableFloatingIP -eq $true -and $rule.BackendPort -eq 0 -and $rule.FrontendPort -eq 0 -and $rule.Protocol -eq "All") {
                Write-Host "HA Ports Enabled: Rule '$($rule.Name)'" -ForegroundColor Green
                $hasHA = $true
            }
        }

        if (-not $hasHA) {
            Write-Host "No HA Port rule found on $($lb.Name)" -ForegroundColor Red
        }
    }
}
