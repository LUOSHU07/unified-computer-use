# 安装 / 自检 ucu 依赖
$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
$ucu = Join-Path $root "ucu.py"

Write-Host "== Python =="
python --version
if ($LASTEXITCODE -ne 0) { Write-Host "未找到 python，请先安装 Python 3.10+"; exit 1 }

Write-Host "== 安装依赖 playwright + uiautomation（优先清华镜像）=="
python -m pip install playwright uiautomation -i https://pypi.tuna.tsinghua.edu.cn/simple --disable-pip-version-check
if ($LASTEXITCODE -ne 0) {
    Write-Host "镜像失败，回退官方源..."
    python -m pip install playwright uiautomation --disable-pip-version-check
}

Write-Host "== 自检 =="
python $ucu doctor
