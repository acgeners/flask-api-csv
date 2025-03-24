#!/usr/bin/env bash

echo "🔧 Atualizando pip, setuptools e wheel..."
pip install --upgrade pip setuptools wheel

echo "📦 Instalando todos os pacotes..."
pip install -r requirements.txt

