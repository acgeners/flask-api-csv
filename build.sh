#!/usr/bin/env bash

# Atualiza pip e wheel
pip install --upgrade pip setuptools wheel

# Instala o sentence-transformers via binário
pip install --only-binary=:all: sentence-transformers==2.2.2

# Instala as dependências padrão
pip install -r requirements.txt
