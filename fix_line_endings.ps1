# PowerShell script to fix line endings for Unix/Linux compatibility
# Run this script to convert Windows line endings to Unix line endings

Write-Host "Fixing line endings for Unix/Linux compatibility..." -ForegroundColor Green

# Get all shell scripts and Python files
$files = Get-ChildItem -Recurse -Include "*.sh", "*.py", "*.bash", "*.zsh" | Where-Object { !$_.PSIsContainer }

$fixedCount = 0

foreach ($file in $files) {
    $content = Get-Content $file.FullName -Raw
    if ($content -match "`r`n") {
        Write-Host "Fixing: $($file.Name)" -ForegroundColor Yellow
        $content = $content -replace "`r`n", "`n"
        Set-Content $file.FullName -Value $content -NoNewline
        $fixedCount++
    }
}

Write-Host "Fixed $fixedCount files" -ForegroundColor Green 