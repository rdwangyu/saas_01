# Generate tabbar icons (81x81 PNG) for the WeChat mini program.
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File gen_tabbar_icons.ps1
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$dir = 'C:\Users\DELL\Desktop\dev\saas_01\face\src\images\tabbar'
New-Item -ItemType Directory -Force -Path $dir | Out-Null

function New-PointF([float]$x, [float]$y) {
  New-Object System.Drawing.PointF($x, $y)
}

function Draw-Icon([string]$name, [string]$hex, [string]$type) {
  $bmp = New-Object System.Drawing.Bitmap 81, 81
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $g.Clear([System.Drawing.Color]::Transparent)
  $c = [System.Drawing.ColorTranslator]::FromHtml($hex)
  $brush = New-Object System.Drawing.SolidBrush $c
  $white = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
  $pen = New-Object System.Drawing.Pen $c, 5
  $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  $pen.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round

  switch ($type) {
    'company' {
      # house: roof + body + door
      $roof = [System.Drawing.PointF[]]@(
        (New-PointF 40.5 12),
        (New-PointF 12 40),
        (New-PointF 69 40)
      )
      $g.FillPolygon($brush, $roof)
      $g.FillRectangle($brush, 21, 36, 39, 31)
      $g.FillRectangle($white, 33, 48, 15, 19)
    }
    'case' {
      # photo: frame + sun + mountains
      $g.DrawRectangle($pen, 15, 18, 51, 45)
      $g.FillEllipse($brush, 47, 25, 11, 11)
      $tri1 = [System.Drawing.PointF[]]@(
        (New-PointF 19 57),
        (New-PointF 37 36),
        (New-PointF 53 57)
      )
      $g.FillPolygon($brush, $tri1)
      $tri2 = [System.Drawing.PointF[]]@(
        (New-PointF 41 57),
        (New-PointF 53 45),
        (New-PointF 62 57)
      )
      $g.FillPolygon($brush, $tri2)
    }
    'project' {
      # progress: three ascending bars
      $g.FillRectangle($brush, 15, 44, 14, 22)
      $g.FillRectangle($brush, 33.5, 32, 14, 34)
      $g.FillRectangle($brush, 52, 20, 14, 46)
    }
    'user' {
      # person: head + shoulders
      $g.FillEllipse($brush, 28, 11, 25, 25)
      $g.FillEllipse($brush, 15, 42, 51, 33)
    }
  }

  $g.Dispose()
  $bmp.Save((Join-Path $dir $name), [System.Drawing.Imaging.ImageFormat]::Png)
  $bmp.Dispose()
}

$gray = '#9CA3AF'
$blue = '#3A7BFD'

Draw-Icon 'company.png' $gray 'company'
Draw-Icon 'company-active.png' $blue 'company'
Draw-Icon 'case.png' $gray 'case'
Draw-Icon 'case-active.png' $blue 'case'
Draw-Icon 'project.png' $gray 'project'
Draw-Icon 'project-active.png' $blue 'project'
Draw-Icon 'user.png' $gray 'user'
Draw-Icon 'user-active.png' $blue 'user'

Write-Output 'tabbar icons generated'
