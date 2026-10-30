import pandas as pd

df = pd.read_csv("data/literature_extracted/high_value_data.csv")
print("Crack occurrence breakdown:")
print(df["crack_occurred"].value_counts(dropna=False))

print("\nDoping breakdown:")
print(df["is_doped"].value_counts(dropna=False))

print("\nCrack occurrence AMONG DOPED samples only:")
print(df[df["is_doped"].astype(str).str.lower() == "yes"]["crack_occurred"].value_counts(dropna=False))