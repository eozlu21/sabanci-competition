#!/bin/bash
#SBATCH -J sabanci-optim
#SBATCH -p kuttam                   # Choose partition with idle, CPU-only nodes
#SBATCH -w kuttam01                 # Choose a specific node with guaranteed 32 cores
#SBATCH --ntasks=32                 # Request 32 tasks (each = 1 core)
#SBATCH --cpus-per-task=1           # One thread per task
#SBATCH --mem=128G                  # Memory allocation
#SBATCH --time=1-00:00:00           # 1 day max
#SBATCH -o sabanci-%j.out
#SBATCH -e sabanci-%j.err
#SBATCH --mail-type=ALL
#SBATCH --mail-user=eozlu21@ku.edu.tr

# Micromamba setup
eval "$(micromamba shell hook --shell bash)"
micromamba activate optim

# Install dependencies if needed (optional)
# pip install -r requirements.txt

# Run your Python script
echo "Running main.py..."
python main.py
