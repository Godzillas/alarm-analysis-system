#!/bin/bash

echo "🚀 开始安装项目依赖..."
echo "📦 使用清华大学 PyPI 镜像源"

# 使用国内源安装依赖
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple/ -r requirements.txt

echo "✅ 依赖安装完成"