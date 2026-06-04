# FNL Runbook

FNL 保障遵循“服务器优先”：先扫描服务器已有数据，只有缺失或损坏时才由跳板机下载并上传。

## Verify Server Coverage

```bash
python3 packages/cli/smanager.py fnl-verify --run-id <run_id>
python3 packages/cli/smanager.py fnl-coverage --start 2026060400 --end 2026061100
```

若只想看需要修复的记录：

```bash
python3 packages/cli/smanager.py fnl-coverage --repair-only --limit 200
```

## Repair

```bash
python3 packages/cli/smanager.py fnl-repair --run-id <run_id>
```

修复流程：

1. 后端调用服务器 `flowctl fnl-verify`。
2. 只对 `missing`、`bad_magic`、`too_small`、`link_broken` 时次执行 `FNL_DOWNLOAD_COMMAND`。
3. 跳板机本地校验 GRIB magic 和最小大小。
4. 优先 `rsync` 上传，缺失时降级 `scp`。
5. 上传后再次调用服务器校验。

## Configuration

关键环境变量：

- `FNL_DOWNLOAD_COMMAND`
- `JUMPBOX_FNL_CACHE_DIR`
- `SERVER_FNL_UPLOAD_DIR`
- `FNL_MIN_MB`
- `FNL_UPLOAD_METHOD`

`FNL_DOWNLOAD_COMMAND` 会收到：

- `FNL_VALID_TIME`
- `FNL_FILE_NAME`
- `FNL_OUTPUT_PATH`

命令成功后必须在 `FNL_OUTPUT_PATH` 生成目标 grib2 文件。
