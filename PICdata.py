import pandas as pd

df = pd.read_excel("/home/daniel/inventory_cal/mat_cal.xlsx", sheet_name="pic")
df = df.replace('\xa0', ' ', regex=True)

data = {}

def get_pic_data():
    for _, row in df.iterrows():
        cust = row["cust"]
        prod = row["prod"]
        if row["prio"] == "默认满足":
            row["prio"] = 0

        key = (cust, prod)

        entry = {
            "mat": row["mat"],
            "priority": row["prio"],
            "using": row["using"],
        }

        if key not in data:
            data[key] = []
        data[key].append(entry)

    return data

# ============= test ==============
if __name__ == "__main__":
    pic_data = get_pic_data()

    print(pic_data)