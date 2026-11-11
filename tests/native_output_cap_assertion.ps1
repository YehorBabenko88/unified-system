# Test-only classifier. Loading this file only declares the function.
function Test-NativeOutputCapException {
    [OutputType([System.Boolean])]
    param([AllowNull()][object]$ExceptionObject)

    try {
        if ([object]::ReferenceEquals($null, $ExceptionObject)) { return [bool]$false }
        $pending = [System.Collections.Generic.List[object]]::new()
        $depths = [System.Collections.Generic.List[int]]::new()
        $seen = [System.Collections.Generic.List[object]]::new()
        [void]$pending.Add($ExceptionObject)
        [void]$depths.Add(1)

        # Pass one: bounded structure and identity only. Aggregate.Message can
        # recurse through children, so no Message getter is used in this pass.
        while ($pending.Count -gt 0) {
            $index = $pending.Count - 1
            $node = $pending[$index]
            $depth = $depths[$index]
            [void]$pending.RemoveAt($index)
            [void]$depths.RemoveAt($index)
            if ($depth -gt 8 -or $seen.Count -ge 16 -or [object]::ReferenceEquals($null, $node)) {
                return [bool]$false
            }
            foreach ($prior in $seen) {
                if ([object]::ReferenceEquals($prior, $node)) { return [bool]$false }
            }
            [void]$seen.Add($node)
            $nodeType = $node.GetType()
            if ([object]::ReferenceEquals($nodeType, [System.InvalidOperationException])) {
                if (-not ([object]::ReferenceEquals($null, $node.InnerException))) { return [bool]$false }
            } elseif ([object]::ReferenceEquals($nodeType, [System.AggregateException])) {
                $children = $node.InnerExceptions
                $count = $children.Count
                if ($count -lt 1 -or $count -gt (16 - $seen.Count - $pending.Count)) { return [bool]$false }
                for ($childIndex = 0; $childIndex -lt $count; $childIndex++) {
                    [void]$pending.Add($children[$childIndex])
                    [void]$depths.Add($depth + 1)
                }
            } elseif ([object]::ReferenceEquals($nodeType, [System.Management.Automation.MethodInvocationException]) -or
                      [object]::ReferenceEquals($nodeType, [System.Reflection.TargetInvocationException])) {
                $inner = $node.InnerException
                if ([object]::ReferenceEquals($null, $inner) -or ($seen.Count + $pending.Count) -ge 16) {
                    return [bool]$false
                }
                [void]$pending.Add($inner)
                [void]$depths.Add($depth + 1)
            } else {
                return [bool]$false
            }
        }

        # Pass two: descendants precede parents. Oversized leaf/wrapper messages
        # are rejected before an aggregate formats them. Every child aggregate
        # is likewise bounded before its parent Message getter can recurse.
        for ($index = $seen.Count - 1; $index -ge 0; $index--) {
            $node = $seen[$index]
            $message = $node.Message
            if ($message -isnot [string] -or $message.Length -gt 1024) { return [bool]$false }
            if ([object]::ReferenceEquals($node.GetType(), [System.InvalidOperationException])) {
                if (-not ([string]::Equals($message, 'CHILD_OUTPUT_LIMIT', [System.StringComparison]::Ordinal))) {
                    return [bool]$false
                }
            }
        }
        return [bool]$true
    } catch {
        return [bool]$false
    }
}
