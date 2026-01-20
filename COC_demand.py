import pandas as pd

df = pd.read_excel("/home/daniel/inventory_cal/mat_cal.xlsx", sheet_name="coc_demand")
df = df.replace('\xa0', ' ', regex=True)

data = {}

def get_coc_demand():
    for _, row in df.iterrows():
        cust = row["cust"]
        prod = row["prod"]

        key = (cust, prod)
        data[key] = {
            "demands": {col: row[col] for col in df.columns[2:]
            }}
    return data

# ============= test ==============
if __name__ == "__main__":
    coc_data = get_coc_demand()
    for k, v in coc_data.items():
        print(k, v)
    print(len(coc_data))