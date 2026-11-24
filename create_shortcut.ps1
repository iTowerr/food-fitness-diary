# create_shortcut.ps1 — вынести ярлык приложения на рабочий стол
$ws = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$link = Join-Path $desktop 'Дневник питания и тренировок.lnk'
$sc = $ws.CreateShortcut($link)
$pydir = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312'
$proj  = 'C:\Users\zahar\Documents\FoodFitnessDiary'
$sc.TargetPath      = Join-Path $pydir 'pythonw.exe'
$sc.Arguments       = '"' + (Join-Path $proj 'main.py') + '"'
$sc.WorkingDirectory = $proj
$sc.IconLocation    = (Join-Path $proj 'icon.ico') + ',0'
$sc.Description     = 'Дневник питания и тренировок — Дерябин Захар Олегович, 22О'
$sc.Save()
Write-Output ("OK: " + (Test-Path $link))
Write-Output $link
