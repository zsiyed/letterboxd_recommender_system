import datetime
from sklearn.decomposition import NMF
from sklearn.model_selection import ParameterGrid
from sklearn.metrics import mean_squared_error
from sklearn.impute import SimpleImputer
import pandas as pd
import numpy as np

# Load and pivot the reviews dataset
df = pd.read_csv("../letterboxd_proj_data/reviews.csv")
user_item_matrix = df.pivot_table(index="user", columns="title", values="rating")

# Fill missing values with column means
imputer = SimpleImputer(strategy='mean')
X_filled = imputer.fit_transform(user_item_matrix)

# Define refined parameter grid based on your earlier success
param_grid = {
    'n_components': [8, 10, 12],        # around 10
    'alpha': [0.01, 0.05, 0.1],         # small regularization
    'l1_ratio': [0.1, 0.3, 0.5],        # small to moderate L1
    'init': ['nndsvda'],
    'max_iter': [300]
}

grid = ParameterGrid(param_grid)
best_score = float('inf')
best_params = None

for params in grid:
    model = NMF(**params, random_state=42)
    try:
        W = model.fit_transform(X_filled)
        H = model.components_
        X_pred = np.dot(W, H)

        # Evaluate only on non-NaN original entries
        mask = ~np.isnan(user_item_matrix.values)
        rmse = np.sqrt(mean_squared_error(X_filled[mask], X_pred[mask]))

        if rmse < best_score:
            best_score = rmse
            best_params = params
    except Exception as e:
        print(f"Error for {params}: {e}")

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
with open("nmf_grid_search_results.txt", "w") as f:
    f.write(f"Grid Search Completed at {now}\n")
    f.write(f"Best RMSE: {best_score:.4f}\n")
    f.write(f"Best Params:\n")
    for key, value in best_params.items():
        f.write(f"  {key}: {value}\n")
print(f"Results written to nmf_grid_search_results.txt at {now}")