#!/usr/bin/env bash
# 启动 smanager-server 常驻 API
set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

ENV_SCRIPT="${ENV_SCRIPT:-/g7/anxq/Zhangjt/workspace/load_env.sh}"
if [[ -f "$ENV_SCRIPT" ]]; then
  # conda activate/deactivate 钩子可能引用未定义变量，不能用 set -u
  # shellcheck disable=SC1090
  source "$ENV_SCRIPT"
else
  echo "错误: 找不到环境脚本 $ENV_SCRIPT" >&2
  exit 1
fi

if [[ "${CONDA_DEFAULT_ENV:-}" != "wrfTool" ]]; then
  echo "错误: 需要 wrfTool 环境，当前为 ${CONDA_DEFAULT_ENV:-未激活}" >&2
  exit 1
fi

mkdir -p logs state

if [[ ! -f config.yaml ]]; then
  cp config.example.yaml config.yaml
  echo "已生成 config.yaml，请按需修改后重启"
fi

exec python -u serverd.py
