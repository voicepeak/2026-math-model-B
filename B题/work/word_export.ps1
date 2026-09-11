param([Parameter(Mandatory=$true)][string]$InputDocx,[Parameter(Mandatory=$true)][string]$OutputPdf)
$ErrorActionPreference='Stop'
$docPath=(Resolve-Path -LiteralPath $InputDocx).Path
$pdfPath=[System.IO.Path]::GetFullPath($OutputPdf)
$wordApp=$null
$wordDoc=$null
try {
    $wordApp=New-Object -ComObject Word.Application
    $wordApp.Visible=$false
    $wordApp.DisplayAlerts=0
    $wordDoc=$wordApp.Documents.Open($docPath,$false,$true)
    $wordDoc.Repaginate()
    $wordDoc.ExportAsFixedFormat($pdfPath,17)
    Write-Output "Word version=$($wordApp.Version); pages=$($wordDoc.ComputeStatistics(2)); PDF=$pdfPath"
} finally {
    if ($wordDoc) { $wordDoc.Close(0); [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordDoc) }
    if ($wordApp) { $wordApp.Quit(); [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordApp) }
}
