import pandas as pd

df = pd.read_excel("/home/daniel/inventory_cal/mat_cal.xlsx", sheet_name="pic_demand")
df = df.replace('\xa0', ' ', regex=True)

data = {}

def get_pic_demand():
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
    pic_data = get_pic_demand()
    for k, v in pic_data.items():
        print(k, v)
    print(len(pic_data))