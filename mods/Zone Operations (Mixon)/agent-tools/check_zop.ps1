# Zone Operations (Mixon) - static checks, no game needed.
# Run from anywhere:  powershell -NoProfile -ExecutionPolicy Bypass -File "<mod>\agent-tools\check_zop.ps1"
# Exit code 0 = all checks passed, 1 = something failed (details printed).

$ErrorActionPreference = 'Stop'
$mod = Split-Path -Parent $PSScriptRoot
$gd  = Join-Path $mod 'gamedata'
$fail = 0
function Bad($msg) { Write-Host "FAIL  $msg" -ForegroundColor Red; $script:fail++ }
function Ok($msg)  { Write-Host "ok    $msg" }

# 1. .script files are ASCII only (player text goes to the xml string tables)
$scripts = Get-ChildItem (Join-Path $gd 'scripts') -Filter *.script
foreach ($f in $scripts) {
    $bytes = [IO.File]::ReadAllBytes($f.FullName)
    $pos = [Array]::FindIndex($bytes, [Predicate[byte]]{ param($b) $b -gt 127 })
    if ($pos -ge 0) {
        $line = ([Text.Encoding]::ASCII.GetString($bytes, 0, $pos) -split "`n").Count
        Bad "$($f.Name): non-ASCII byte at line $line"
    }
}
Ok "$($scripts.Count) scripts checked for ASCII"

# 2. engine traps: never list $game_meshes$
$hits = Select-String -Path (Join-Path $gd 'scripts\*.script') -Pattern 'file_list_open_ex' -SimpleMatch
foreach ($h in $hits) {
    if ($h.Line -match 'game_meshes') { Bad "$($h.Filename):$($h.LineNumber): file_list_open_ex on `$game_meshes`$ (native crash)" }
}
Ok "no file_list_open_ex on `$game_meshes`$"

# 3. zop_operations.ltx keeps LF line endings
$ops = Join-Path $gd 'configs\misc\zone_ops\zop_operations.ltx'
if ([IO.File]::ReadAllText($ops).Contains("`r`n")) { Bad "zop_operations.ltx has CRLF line endings (must stay LF)" } else { Ok "zop_operations.ltx is LF" }

# 4. string tables: cp1251, well-formed, same ids in rus and eng
$cp = [Text.Encoding]::GetEncoding(1251)
$ids = @{}
foreach ($lang in 'rus', 'eng') {
    $p = Join-Path $gd "configs\text\$lang\ui_st_zop.xml"
    $text = $cp.GetString([IO.File]::ReadAllBytes($p))
    if ($text -notmatch 'encoding="windows-1251"') { Bad "$lang/ui_st_zop.xml: header is not windows-1251" }
    try {
        $x = New-Object Xml.XmlDocument
        $x.LoadXml(($text -replace '^<\?xml[^>]*\?>', ''))
        $ids[$lang] = @($x.SelectNodes('//string') | ForEach-Object { $_.GetAttribute('id') })
        $dup = $ids[$lang] | Group-Object | Where-Object Count -gt 1
        foreach ($d in $dup) { Bad "$lang/ui_st_zop.xml: duplicate id $($d.Name)" }
        Ok "$lang/ui_st_zop.xml parses, $($ids[$lang].Count) strings"
    } catch { Bad "$lang/ui_st_zop.xml does not parse: $($_.Exception.Message)" }
}
if ($ids.rus -and $ids.eng) {
    $diff = Compare-Object $ids.rus $ids.eng
    foreach ($d in $diff) { Bad "id $($d.InputObject) only in $(if ($d.SideIndicator -eq '<=') {'rus'} else {'eng'})" }
    if (-not $diff) { Ok "rus and eng have the same ids" }
}

# 5. Literal ids in configs and Lua (including embedded XML).
if ($ids.ContainsKey('rus')) {
    $known = [Collections.Generic.HashSet[string]]::new([string[]]$ids.rus, [StringComparer]::Ordinal)
    $configs = Get-ChildItem (Join-Path $gd 'configs') -Recurse -File -Filter *.ltx
    # Mask comments without changing offsets. Quoted strings can contain comment markers.
    $quoted = '"(?:\\[\s\S]|[^"\\])*"|''(?:\\[\s\S]|[^''\\])*'''
    $luaParts = '--\[(?<c>=*)\[[\s\S]*?\]\k<c>\]|--[^\r\n]*|' + $quoted + '|\[(?<s>=*)\[[\s\S]*?\]\k<s>\]'
    $ltxParts = '"[^"\r\n]*"|''[^''\r\n]*''|;[^\r\n]*'
    $checked = 0
    $missing = 0
    foreach ($file in (@($scripts) + @($configs))) {
        $source = $cp.GetString([IO.File]::ReadAllBytes($file.FullName))
        $lua = $file.Extension -eq '.script'
        $parts = if ($lua) { $luaParts } else { $ltxParts }
        $source = [regex]::Replace($source, $parts, {
            param($part)
            if ($part.Value.StartsWith('--') -or $part.Value.StartsWith(';')) {
                return [regex]::Replace($part.Value, '[^\r\n]', ' ')
            }
            return $part.Value
        })
        $offset = 0
        $line = 0
        foreach ($row in ($source -split "\n")) {
            $line++
            foreach ($hit in [regex]::Matches($row, '\bst_zop_[A-Za-z0-9_]+\b')) {
                $id = $hit.Value
                if ($id.EndsWith('_')) { continue }
                if ($lua) {
                    $start = $offset + $hit.Index
                    if ($source.Substring(0, $start) -match '\.\.\s*(?:["'']|\[=*\[)?\z' -or
                        $source.Substring($start + $hit.Length) -match '^(?:["'']|\]=*\])?\s*\.\.') { continue }
                }
                $checked++
                if (!$known.Contains($id)) {
                    $missing++
                    $path = $file.FullName.Substring($mod.Length + 1)
                    Bad "$($path):$($line): $id missing from rus/ui_st_zop.xml"
                }
            }
            $offset += $row.Length + 1
        }
    }
    Write-Host "Literal st_zop_ references: $checked checked, $missing missing"
}

if ($fail) { Write-Host "$fail check(s) failed" -ForegroundColor Red; exit 1 }
Write-Host "all checks passed" -ForegroundColor Green
exit 0
