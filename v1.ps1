# Get all internal load balancers (non-public)
$loadBalancers = Get-AzLoadBalancer | Where-Object {
    ($_.FrontendIpConfigurations | Where-Object { -not $_.PublicIpAddress }).Count -gt 0
}

$issues = @()

foreach ($lb in $loadBalancers) {
    $ilbName = $lb.Name
    $rgName = $lb.ResourceGroupName

    Write-Output ""
    Write-Output "Auditing ILB: $ilbName (Resource Group: $rgName)"

    foreach ($frontend in $lb.FrontendIpConfigurations) {
        Write-Output "Frontend IP: $($frontend.PrivateIpAddress) [$($frontend.Name)]"
    }

    foreach ($rule in $lb.LoadBalancingRules) {
        $ruleName = $rule.Name
        Write-Output ""
        Write-Output "Rule: $ruleName"

        # HA Ports check
        if ($rule.Protocol -eq "All" -and $rule.FrontendPort -eq 0 -and $rule.BackendPort -eq 0) {
            Write-Output "HA Ports Enabled"
        } else {
            $msg = "[$ilbName][$ruleName] - HA Ports not enabled"
            Write-Output $msg
            $issues += $msg
        }

        # Frontend Mapping
        $frontendMapping = $lb.FrontendIpConfigurations | Where-Object { $_.Id -eq $rule.FrontendIPConfiguration.Id }
        if ($frontendMapping) {
            Write-Output "Frontend Mapping: $($frontendMapping.Name)"
        } else {
            $msg = "[$ilbName][$ruleName] - Frontend mapping missing"
            Write-Output $msg
            $issues += $msg
        }

        # Backend Pool Mapping
        $backend = $lb.BackendAddressPools | Where-Object { $_.Id -eq $rule.BackendAddressPool.Id }
        if ($backend) {
            Write-Output "Backend Pool: $($backend.Name)"

            $nicCount = $backend.BackendIPConfigurations.Count
            $ipCount = $backend.LoadBalancerBackendAddresses.Count
            $total = $nicCount + $ipCount

            if ($total -eq 0) {
                $msg = "[$ilbName][$ruleName] - No backend members defined"
                Write-Output $msg
                $issues += $msg
            } else {
                Write-Output "Backend members present: NIC ($nicCount), IP ($ipCount)"
            }
        } else {
            $msg = "[$ilbName][$ruleName] - Backend pool missing"
            Write-Output $msg
            $issues += $msg
        }

        # Health Probe
        if ($rule.Probe.Id) {
            $probeName = $rule.Probe.Id.Split("/")[-1]
            Write-Output "Health Probe: $probeName"
        } else {
            $msg = "[$ilbName][$ruleName] - No health probe attached"
            Write-Output $msg
            $issues += $msg
        }
    }
}

# Summary
Write-Output ""
Write-Output "Audit Summary:"
if ($issues.Count -eq 0) {
    Write-Output "No issues found across internal load balancers."
} else {
    foreach ($issue in $issues) {
        Write-Output $issue
    }
}
