import pandas as pd


def process_csv(new_data_path):
    try:
        # Lendo os arquivos CSV
        new_df = pd.read_csv(new_data_path)

        # Configura pandas para exibir todas as colunas na saída
        pd.set_option('display.max_columns', None)  # Exibe todas as colunas
        pd.set_option('display.width', 200)  # Ajusta a largura do terminal para evitar truncamento

        print(f"Tabela exemplo: {new_df.head(5).to_string(index=False)}")

        # Convertendo para JSON dentro de um dicionário
        result_json = {"data": new_df.to_dict(orient="records")}
        print(f"Tipo do dado: {type(result_json)}")
        return result_json  # Agora retorna um dicionário com chave 'data'

    except Exception as e:
        return {"error": str(e)}
