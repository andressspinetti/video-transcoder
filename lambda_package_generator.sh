#!/bin/zsh
source ~/.zshrc
ROOT_DIR="$(pwd)"
LAMBDA_DIR="$ROOT_DIR/lambda_function"
VIRTUALENV='venv_lambda'
LAYERS_PATH="$LAMBDA_DIR/lambda_layers/python/lib/python3.6/site-packages"
rmvirtualenv $VIRTUALENV
mkdir -p $LAYERS_PATH

# Setup fresh virtualenv and install requirements
mkvirtualenv $VIRTUALENV --python=python3.6
workon $VIRTUALENV
pip install -r requirements-lambda.txt -t $LAYERS_PATH/.
deactivate

# Create zip file
ZIP_FILE='lambda.zip'
cd $LAYERS_PATH
zip -r9 $LAMBDA_DIR/$ZIP_FILE *
cd $LAMBDA_DIR
zip -g $ZIP_FILE main.py
