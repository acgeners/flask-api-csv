import pandas as pd

ref_path = "new_data_negocio.csv"
new_path = "validate_data_negocio.csv"

print("Carregando arquivos CSV...")
ref_data = pd.read_csv(ref_path, dtype=str).dropna(how='all')
new_data = pd.read_csv(new_path, dtype=str).dropna(how='all')

# Garante que ambos os DataFrames tenham o mesmo número de colunas
if ref_data.shape[1] != new_data.shape[1]:
    print(f"Ref: {ref_data.shape} / New: {new_data.shape}")
    raise ValueError("Os DataFrames devem ter o mesmo número de colunas.")

# Renomeia temporariamente as colunas para evitar duplicação
ref_data.columns = [f"{col}_ref" for col in ref_data.columns]
new_data.columns = [f"{col}_new" for col in new_data.columns]

# Concatena os DataFrames lado a lado
df_mesclado = pd.concat([new_data, ref_data], axis=1)

# Intercala as colunas
colunas_intercaladas = [col for pair in zip(new_data.columns, ref_data.columns) for col in pair]
df_mesclado = df_mesclado[colunas_intercaladas]

# Exporta para CSV
df_mesclado.to_csv("val_data_negocio.csv", index=False)
print("Arquivo salvo como val_data_negocio.csv")
