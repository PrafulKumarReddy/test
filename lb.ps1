
function Get-InternalLoadBalancers {
    $loadBalancers = Get-AzLoadBalancer
    return $loadBalancers | Where-Object {
        ($_.FrontendIpConfigurations | Where-Object { -not $_.PublicIpAddress }).Count -gt 0
    }
}

function Test-HAPortsEnabled {
    param($rule)
    return $rule.Protocol -eq "All" -and $rule.FrontendPort -eq 0 -and $rule.BackendPort -eq 0
}

function Get-FrontendMapping {
    param($ilb, $rule)
    return $ilb.FrontendIpConfigurations | Where-Object { $_.Id -eq $rule.FrontendIpConfiguration.Id }
}

function Get-BackendPoolMapping {
    param($ilb, $rule)
    return $ilb.BackendAddressPools | Where-Object { $_.Id -eq $rule.BackendAddressPool.Id }
}

function Audit-LoadBalancingRule {
    param($ilb, $rule, [ref]$issues)

    Write-Output "\n▶ Rule: $($rule.Name)"

    if (Test-HAPortsEnabled -rule $rule) {
        Write-Output "  ✔ HA Ports Enabled"
    } else {
        $msg = "❌ [$($ilb.Name)][$($rule.Name)] - HA Ports NOT enabled"
        Write-Output "  $msg"
        $issues.Value += $msg
    }

    $frontend = Get-FrontendMapping -ilb $ilb -rule $rule
    if ($frontend) {
        Write-Output "  ✔ Frontend Mapping: $($frontend.Name)"
    } else {
        $msg = "❌ [$($ilb.Name)][$($rule.Name)] - Frontend Mapping Missing"
        Write-Output "  $msg"
        $issues.Value += $msg
    }

    $backend = Get-BackendPoolMapping -ilb $ilb -rule $rule
    if ($backend) {
        Write-Output "  ✔ Backend Pool: $($backend.Name)"

        if ($backend.BackendAddresses.Count -gt 0) {
            Write-Output "  ⚠ IP-address-based backend pool — Subnet validation skipped."
            foreach ($addr in $backend.BackendAddresses) {
                Write-Output "    ✔ IP: $($addr.IpAddress) (Name: $($addr.Name))"
            }
        } else {
            $msg = "❌ [$($ilb.Name)][$($rule.Name)] - No backend members defined"
            Write-Output "  $msg"
            $issues.Value += $msg
        }
    } else {
        $msg = "❌ [$($ilb.Name)][$($rule.Name)] - Backend Pool Missing"
        Write-Output "  $msg"
        $issues.Value += $msg
    }

    if ($rule.Probe.Id) {
        $probeName = $rule.Probe.Id.Split("/")[-1]
        Write-Output "  ✔ Health Probe: $probeName"
    } else {
        $msg = "❌ [$($ilb.Name)][$($rule.Name)] - No Health Probe Attached"
        Write-Output "  $msg"
        $issues.Value += $msg
    }
}

function Audit-InternalLoadBalancers {
    $issues = @()
    $ilbs = Get-InternalLoadBalancers

    foreach ($ilb in $ilbs) {
        Write-Output "\n🔍 Auditing ILB: $($ilb.Name) (RG: $($ilb.ResourceGroupName))"

        foreach ($frontend in $ilb.FrontendIpConfigurations) {
            Write-Output "✔ Frontend IP: $($frontend.PrivateIpAddress) [$($frontend.Name)]"
        }

        foreach ($rule in $ilb.LoadBalancingRules) {
            Audit-LoadBalancingRule -ilb $ilb -rule $rule -issues ([ref]$issues)
        }
    }

    Write-Output "\n==== ⚠️ Audit Issues Found ===="
    if ($issues.Count -eq 0) {
        Write-Output "✅ No issues detected across ILBs."
    } else {
        foreach ($issue in $issues) {
            Write-Output $issue
        }
    }
}

# Entry point
Audit-InternalLoadBalancers
