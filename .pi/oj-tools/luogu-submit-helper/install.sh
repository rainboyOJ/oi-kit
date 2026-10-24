#!/usr/bin/env bash
set -euo pipefail

repository_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_path="${repository_dir}/luogu-submit"
target_dir="${HOME}/.local/bin"
target_path="${target_dir}/luogu-submit"
old_source_path="${repository_dir}/luogu"
old_target_path="${target_dir}/luogu"

if [[ ! -x "${source_path}" ]]; then
    echo "错误: 找不到可执行脚本 ${source_path}" >&2
    exit 1
fi

mkdir -p "${target_dir}"
if [[ -e "${target_path}" && ! -L "${target_path}" ]]; then
    echo "错误: ${target_path} 已存在且不是符号链接，未覆盖。" >&2
    exit 1
fi

ln -sfn "${source_path}" "${target_path}"
echo "已安装: ${target_path} -> ${source_path}"

if [[ -L "${old_target_path}" ]] \
    && [[ "$(readlink -- "${old_target_path}")" == "${old_source_path}" ]]; then
    unlink "${old_target_path}"
    echo "已移除旧命令链接: ${old_target_path}"
fi

case ":${PATH}:" in
    *":${target_dir}:"*) ;;
    *)
        echo "提示: ${target_dir} 尚未加入 PATH。"
        echo "请把下面一行加入 shell 配置后重新打开终端:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        ;;
esac
