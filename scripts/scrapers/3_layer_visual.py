import json
import pandas as pd
import numpy as np

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

# -------------------------
# 1. LOAD DATA (FULL MATCH TIMELINE)
# -------------------------
path = "/home/mcilek/Github/maximcilek/lewis-university-research/data/analysis/double_fault_model.jsonl"

df = pd.read_json(path, lines=True)

print("Raw shape:", df.shape)
print(df.corr(numeric_only=True)["is_double_fault"])