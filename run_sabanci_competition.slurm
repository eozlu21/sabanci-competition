#!/bin/bash
#SBATCH -J sabanci-job
#SBATCH -A users
#SBATCH -p mid
#SBATCH --qos=users
#SBATCH -c 4
#SBATCH --gres=gpu:1
#SBATCH --mem=32G
#SBATCH --time=1-00:00:00
#SBATCH -o sabanci-%j.out
#SBATCH -e sabanci-%j.err

#SBATCH --mail-type=ALL
#SBATCH --mail-user=eozlu21@ku.edu.tr  # <-- Replace this with your actual email

# Load any required modules
# module load cuda/11.7

# Micromamba setup
eval "$(micromamba shell hook --shell bash)"

ENV_NAME="sabanci-competition"

# Check if environment exists
if ! micromamba env list | grep -q "$ENV_NAME"; then
    echo "Creating micromamba environment: $ENV_NAME"
    micromamba create -y -n $ENV_NAME python=3.10
    micromamba activate $ENV_NAME

    # Install dependencies from requirements.txt
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        echo "ERROR: requirements.txt not found!"
        exit 1
    fi
else
    echo "Environment $ENV_NAME already exists"
fi

# Activate the environment
micromamba activate $ENV_NAME

# Run your Python script
echo "Running main.py..."
python main.py
