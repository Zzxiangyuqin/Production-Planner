import pandas as pd

df = pd.read_excel("/home/daniel/inventory_cal/mat_cal.xlsx", sheet_name="cw")
df = df.replace('\xa0', ' ', regex=True)

data = {}

def get_cw_data():
    for _, row in df.iterrows():
        cust = row["cust"]
        prod = row["prod"]

        key = (cust, prod)

        entry = {
            "mat": row["mat"].strip(),
            "priority": row["prio"],
            "using": row["using"],
        }

        if key not in data:
            data[key] = []
        data[key].append(entry)
    return data

# ============= test ==============
if __name__ == "__main__":
    cw_data = get_cw_data()
    for k, v in cw_data.items():
        print(k, v)