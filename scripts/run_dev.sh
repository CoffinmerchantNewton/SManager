#!/bin/bash
set -euo pipefail

python_bin="/Users/wangxu/softwares/miniconda3/bin/python"

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

"$python_bin" manage.py migrate
"$python_bin" manage.py seed_demo
"$python_bin" manage.py runserver
