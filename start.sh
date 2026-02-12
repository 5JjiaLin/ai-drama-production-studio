#!/bin/bash

echo "========================================"
echo "  AI剧本批量拆解工具 - Docker版"
echo "========================================"
echo ""

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "[错误] 未检测到Docker，请先安装Docker"
    echo "安装指南: https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查docker-compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "[错误] 未检测到docker-compose，请先安装"
    exit 1
fi

# 检查.env文件是否存在
if [ ! -f .env ]; then
    echo "[提示] 首次使用需要配置API Key"
    echo ""
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "[成功] 已创建.env文件，请编辑此文件填写你的API Key"
        echo ""
        echo "请使用文本编辑器打开 .env 文件并填写API Key"
        echo "编辑完成后，重新运行此脚本"
        exit 0
    else
        echo "[错误] 找不到.env.example文件"
        exit 1
    fi
fi

echo "[1/3] 正在构建Docker镜像..."
docker-compose build

if [ $? -ne 0 ]; then
    echo "[错误] Docker镜像构建失败"
    exit 1
fi

echo ""
echo "[2/3] 正在启动服务..."
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "[错误] 服务启动失败"
    exit 1
fi

echo ""
echo "[3/3] 等待服务就绪..."
sleep 5

echo ""
echo "========================================"
echo "  启动成功！"
echo "========================================"
echo ""
echo "访问地址: http://localhost:3000"
echo ""
echo "管理命令:"
echo "  - 查看日志: docker-compose logs -f"
echo "  - 停止服务: docker-compose down"
echo "  - 重启服务: docker-compose restart"
echo ""

# 尝试打开浏览器（macOS）
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:3000
fi

# 尝试打开浏览器（Linux）
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:3000
    fi
fi
