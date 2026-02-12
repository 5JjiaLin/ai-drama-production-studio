@echo off
chcp 65001 >nul
echo ========================================
echo   AI剧本批量拆解工具 - Docker版
echo ========================================
echo.

REM 检查Docker是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Docker，请先安装Docker Desktop
    echo 下载地址: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM 检查.env文件是否存在
if not exist .env (
    echo [提示] 首次使用需要配置API Key
    echo.
    if exist .env.example (
        copy .env.example .env >nul
        echo [成功] 已创建.env文件，请编辑此文件填写你的API Key
        echo.
        echo 按任意键打开.env文件进行编辑...
        pause >nul
        notepad .env
        echo.
        echo 编辑完成后，按任意键继续启动...
        pause >nul
    ) else (
        echo [错误] 找不到.env.example文件
        pause
        exit /b 1
    )
)

echo [1/3] 正在构建Docker镜像...
docker-compose build

if errorlevel 1 (
    echo [错误] Docker镜像构建失败
    pause
    exit /b 1
)

echo.
echo [2/3] 正在启动服务...
docker-compose up -d

if errorlevel 1 (
    echo [错误] 服务启动失败
    pause
    exit /b 1
)

echo.
echo [3/3] 等待服务就绪...
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo   启动成功！
echo ========================================
echo.
echo 访问地址: http://localhost:3000
echo.
echo 管理命令:
echo   - 查看日志: docker-compose logs -f
echo   - 停止服务: docker-compose down
echo   - 重启服务: docker-compose restart
echo.
echo 按任意键打开浏览器...
pause >nul
start http://localhost:3000
