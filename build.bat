@echo off
@REM REM 设置控制台编码为 UTF-8
chcp 65001 >nul

REM 获取当前脚本所在的文件夹路径
set "current_dir=%~dp0"

REM 检查是否传入了 distpath、版本信息和工作模式参数
if "%1"=="" (
    echo 请提供 distpath 参数
    exit /b 1
)

if "%2"=="" (
    echo 请提供版本信息
    exit /b 1
)

if "%3"=="" (
    echo 请提供 WORK_MODE 参数
    exit /b 1
)

REM 外部传入的 distpath 参数
set "distpath=%1"

REM 外部传入的版本信息
set "version=%2"

REM 外部传入的 WORK_MODE 参数
set "work_mode=%3"

REM 设置 config.py 文件路径
set "config_file=%current_dir%\app\common\config.py"

REM 读取配置文件内容并更新 VERSION 和 WORK_MODE
powershell -Command ^
    "(Get-Content -Path '%config_file%' -Encoding UTF8) | ForEach-Object { $_ -replace 'VERSION =.*', 'VERSION = \"%version%\"' -replace 'WORK_MODE =.*', 'WORK_MODE = \"%work_mode%\"' } | Set-Content -Path '%config_file%' -Encoding UTF8"

REM 构建资源文件
pyrcc5 "%current_dir%app\resource\resource.qrc" -o "%current_dir%\app\common\resource.py"

REM 稍微等待以确保文件写入完成
timeout /t 3 /nobreak >nul

REM 创建目标目录（如果不存在）
if not exist "%distpath%\%work_mode%\%version%" (
    mkdir "%distpath%\%work_mode%\%version%"
)

REM 执行打包命令，使用生成的目标路径作为 distpath
pyinstaller -y --windowed ^
    --add-data "%current_dir%app\config;./app/config" ^
    --add-data "%current_dir%app\assets;./app/assets" ^
    --icon="%current_dir%app\resource\images\logo.png" ^
    --distpath="%distpath%\%work_mode%\%version%" ^
    Assistent.py

REM 打包完成消息
echo 打包完成，输出目录：%distpath%/%work_mode%/%version%

@REM @REM REM 恢复默认编码clear

@REM chcp 936 >nul
