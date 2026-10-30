# Make a comma-free Linux alias to this Windows project for Podman bind mounts.
# Reuses the project files in place; does not copy them or alter Astro projects.
[CmdletBinding()]
param([string]$MachineName = 'astro-machine')

$ErrorActionPreference = 'Stop'
$projectDirectory = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if ($projectDirectory -notmatch '^[A-Za-z]:\\') {
    throw 'Expected a Windows drive path for this WSL2 helper.'
}
$driveLetter = $projectDirectory.Substring(0, 1).ToLowerInvariant()
$linuxDirectory = '/mnt/' + $driveLetter + $projectDirectory.Substring(2).Replace('\', '/')
# Quote an arbitrary path as one POSIX shell argument, including apostrophes.
$quotedDirectory = "'" + $linuxDirectory.Replace("'", "'\''") + "'"
$remoteScript = @'
set -eu
target=__PROJECT_DIRECTORY__
alias_path=/home/user/yt-elt-project
test -f "$target/docker-compose.yaml"
if [ -e "$alias_path" ] || [ -L "$alias_path" ]; then
    if [ ! -L "$alias_path" ] || [ "$(readlink -f "$alias_path")" != "$(readlink -f "$target")" ]; then
        echo "Refusing to replace an existing, different path: $alias_path" >&2
        exit 1
    fi
else
    ln -s "$target" "$alias_path"
fi
test -f "$alias_path/docker/postgres/init-multiple-databases.sh"
echo "Podman project mount ready: $alias_path"
'@
$remoteScript = $remoteScript.Replace('__PROJECT_DIRECTORY__', $quotedDirectory)
$remoteScript = $remoteScript.Replace("`r`n", "`n")
& podman machine ssh $MachineName $remoteScript
if ($LASTEXITCODE -ne 0) {
    throw 'Podman mount preparation failed. Check the running machine and /mnt drive.'
}
