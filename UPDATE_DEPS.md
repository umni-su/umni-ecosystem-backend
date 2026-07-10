```bash
pip-review --local --interactive
pip freeze > requirements.txt
```

Or

```bash
pip list --outdated
pip install --upgrade {name1}
pip install --upgrade {nameN}
pip freeze > requirements.txt
```