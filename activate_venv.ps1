if ($PSVersionTable.Platform -eq "Unix") {
    & ./.venv/bin/Activate.ps1
}
else {
    & .\.venv\Scripts\Activate.ps1
}