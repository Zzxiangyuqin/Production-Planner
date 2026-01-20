import pandas as pd

df = pd.read_excel("/home/daniel/inventory_cal/mat_cal.xlsx", sheet_name="pic_inventory")
df = df.replace('\xa0', ' ', regex=True)

init_data = {}
monthly_update = {}

def get_pic_init():
    for _, row in df.iterrows():
        mat = row["mat"]
        init_num = row["init"]

        init_data[mat] = init_num

    return init_data

def get_pic_monthly_update():
    for _, row in df.iterrows():
        mat = row["mat"]
        updates = {col: row[col] for col in df.columns[2:]}

        monthly_update[mat] = updates

    return monthly_update



# ============= test ==============
if __name__ == "__main__":
    print("-----initial data-----")
    init_data = get_pic_init()
    for k, v in init_data.items():
        print(k, v)
    print(len(init_data))
    print("-----monthly update-----")
    monthly_update = get_pic_monthly_update()
    for k, v in monthly_update.items():
        print(k, v)
    print(len(monthly_update))