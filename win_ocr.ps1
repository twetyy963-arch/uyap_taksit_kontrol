param(
    [string]$ImagePath
)

Add-Type -AssemblyName System.Runtime.WindowsRuntime
Add-Type -AssemblyName System.Drawing

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { 
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' 
})[0]

function AwaitTask($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    return $netTask.Result
}

[Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime] | Out-Null

try {
    $bytes = [System.IO.File]::ReadAllBytes($ImagePath)
    $memStream = New-Object System.IO.MemoryStream(,$bytes)
    $randStream = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
    $netStream = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForWrite($randStream)
    $memStream.CopyTo($netStream)
    $netStream.Flush()
    $randStream.Seek(0)

    $decoder = AwaitTask ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($randStream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = AwaitTask ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

    $lang = New-Object Windows.Globalization.Language('tr')
    $ocr = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
    if (-not $ocr) {
        $ocr = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    }

    $result = AwaitTask ($ocr.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

    $words = @()
    foreach ($line in $result.Lines) {
        foreach ($w in $line.Words) {
            $words += @{
                Text = $w.Text
                X = [int]$w.BoundingRect.X
                Y = [int]$w.BoundingRect.Y
                W = [int]$w.BoundingRect.Width
                H = [int]$w.BoundingRect.Height
            }
        }
    }
    
    @{
        Text = $result.Text
        Words = $words
    } | ConvertTo-Json -Depth 4
} catch {
    Write-Error $_.Exception.ToString()
}
