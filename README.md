# claude-code-study

Claude Code를 활용한 Python Data/ML 학습 프로젝트입니다.

## 시작하기

```bash
# 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -e ".[dev]"
```

## 프로젝트 구조

```
src/            # 재사용 가능한 Python 모듈
tests/          # pytest 테스트
notebooks/      # 탐색용 Jupyter 노트북
data/
  raw/          # 원본 데이터 (gitignore 처리됨)
  processed/    # 전처리된 데이터
```

## 주요 명령어

```bash
pytest                  # 전체 테스트 실행
pytest tests/foo.py     # 단일 파일 테스트
ruff check .            # 린트
ruff format .           # 포맷
mypy src/               # 타입 검사
jupyter notebook        # Jupyter 실행
```

## 기술 스택

- **Python** 3.9+
- **데이터**: numpy, pandas
- **ML**: scikit-learn
- **시각화**: matplotlib
- **개발**: pytest, ruff, mypy
