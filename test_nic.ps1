<#
.SYNOPSIS
Validates NIC configuration on Azure Firewall VMs and outputs structured alerts

.NOTES
Requires Azure Automation Runbook with managed identity
#>

# Connect to Azure using Managed Identity
Connect-AzAccount -Identity

# Configuration
$requiredNicSuffixes = @("Pan-Mgmt", "DNET", "INET", "SPOKE")  # Customize as needed
$firewallNamePattern = "*fw*"  # Case-insensitive pattern for firewall VMs
$subscriptionId = (Get-AzContext).Subscription.Id

# Initialize alert collection
$alerts = [System.Collections.Generic.List[PSObject]]::new()

try {
    # Get all VMs in subscription
    $vms = Get-AzVM -ErrorAction Stop
    
    # Filter firewall VMs
    $firewallVMs = $vms | Where-Object { $_.Name -like $firewallNamePattern }
    
    if (-not $firewallVMs) {
        Write-Output "No firewall VMs found matching pattern: $firewallNamePattern"
        exit
    }

    foreach ($vm in $firewallVMs) {
        try {
            $vmName = $vm.Name
            $resourceGroup = $vm.ResourceGroupName
            
            # Get NIC details
            $nics = $vm.NetworkProfile.NetworkInterfaces
            $attachedNicNames = $nics | ForEach-Object { ($_.Id -split '/')[-1] }
            
            # Validate NIC suffixes
            $missingSuffixes = $requiredNicSuffixes | Where-Object {
                $suffix = $_
                -not ($attachedNicNames -like "*$suffix*")
            }

            if ($missingSuffixes.Count -gt 0) {
                $alertPayload = [PSCustomObject]@{
                    Timestamp     = [DateTime]::UtcNow.ToString("o")
                    VMName        = $vmName
                    ResourceGroup = $resourceGroup
                    Subscription  = $subscriptionId
                    MissingNICs   = $missingSuffixes
                    AttachedNICs  = $attachedNicNames
                }
                
                $alerts.Add($alertPayload)
                Write-Output "[ALERT] $($alertPayload | ConvertTo-Json -Compress)"
            }
        }
        catch {
            Write-Error "Error processing VM $vmName : $_"
        }
    }
}
catch {
    Write-Error "Critical error: $_"
    exit 1
}

# Output summary
if ($alerts.Count -gt 0) {
    $summary = @{
        TotalFirewallsChecked = $firewallVMs.Count
        MisconfiguredCount    = $alerts.Count
        AlertDetails          = $alerts
    }
    Write-Output "##[SUMMARY]## $($summary | ConvertTo-Json -Depth 3)"
}
else {
    Write-Output "All $($firewallVMs.Count) firewall VMs have correct NIC configuration"
}
