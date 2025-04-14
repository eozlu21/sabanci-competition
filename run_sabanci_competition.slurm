#!/bin/bash
#SBATCH -J sabanci-job
#SBATCH -A users
#SBATCH -p mid
#SBATCH --qos=users
#SBATCH -c 4
#SBATCH --gres=gpu:1
#SBATCH --mem=64G
#SBATCH --time=1-00:00:00
#SBATCH -o sabanci-%j.out
#SBATCH -e sabanci-%j.err

#SBATCH --mail-type=ALL
#SBATCH --mail-user=eozlu21@ku.edu.tr

# Micromamba setup
eval "$(micromamba shell hook --shell bash)"

ENV_NAME="sabanci-competition"

echo "Removing old environment (if exists)..."
micromamba env remove -y -n $ENV_NAME

echo "Creating micromamba environment: $ENV_NAME"
micromamba create -y -n $ENV_NAME python=3.10

micromamba activate $ENV_NAME

# Install dependencies from requirements.txt
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    echo "ERROR: requirements.txt not found!"
    exit 1
fi

# Run your Python script
echo "Running main.py..."
python main.py
