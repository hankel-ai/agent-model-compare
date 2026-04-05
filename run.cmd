@echo off
python list_models.py
if "%~1"=="" (
	echo.
    echo run --task prompt --models model1,model2
    exit /b 1
)
python -m src.cli benchmark %*