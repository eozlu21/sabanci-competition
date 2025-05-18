#!/bin/bash
#SBATCH -J sabanci-optim
#SBATCH -p avg
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=128G
#SBATCH --time=1-00:00:00
#SBATCH -o sabanci-%j.out
#SBATCH -e sabanci-%j.err
#SBATCH --mail-type=ALL
#SBATCH --mail-user=eozlu21@ku.edu.tr

# Micromamba setup
eval "$(micromamba shell hook --shell bash)"
micromamba activate optim

echo "Running main.py..."
python main.py
