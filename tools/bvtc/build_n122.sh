#!/usr/bin/env bash
# Dựng lại cột N122 (tăng dần: chỉ làm lại phần thay đổi). Thêm --force để làm lại tất cả. Xem tools/bvtc/build.py
exec python3 "$(dirname "$0")/build.py" "$@"
