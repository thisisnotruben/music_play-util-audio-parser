# README

## Run
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True python main.py
```

## Personal notes
### Freeze dep
```bash
pip freeze > requirements.txt
```
