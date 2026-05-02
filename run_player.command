#!/bin/bash
# 현재 스크립트가 있는 디렉토리로 이동
cd "$(dirname "$0")"

# 가상 환경 활성화 (존재할 경우)
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 프로그램 실행
python3 music_player.py
