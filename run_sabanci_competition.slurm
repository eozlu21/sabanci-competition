#!/bin/bash
#SBATCH -J sabanci-optim
#SBATCH --ntasks=32
#SBATCH --cpus-per-task=1
#SBATCH --mem=128G
#SBATCH --time=1-00:00:00
#SBATCH -o sabanci-%j.out
#SBATCH -e sabanci-%j.err
#SBATCH --mail-type=ALL
#SBATCH --mail-user=eozlu21@ku.edu.tr

# Let Slurm choose from any available partition/node
# by not setting -p or -w explicitly

# Micromamba setup
eval "$(micromamba shell hook --shell bash)"
micromamba activate optim

echo "Running main.py..."
python main.py
