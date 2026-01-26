from COC_demand import * 
from CW_inventory import * 
from CWdata import *
from PIC_inventory import *
from PICdata import *
from PIC_demand import *
import copy


# CW CALCULATION
cw_inventory_init = get_cw_init()
cw_inventory_monthly_update = get_cw_monthly_update()
cw_details = get_cw_data()
coc_demand = get_coc_demand()

class CW_ProductionManager:
    def __init__(self):
        self.coc_demand = copy.deepcopy(coc_demand)
        self.cw_inventory = copy.deepcopy(cw_inventory_init)
        self.cw_inventory_monthly_update = cw_inventory_monthly_update
        self.cw_details = cw_details

    def get_coc_demand_by_month(self, date):
        """
        coc_demand:
        {
        ...
            (666, '400G QSFP112 DR4 Sipho LPO Gen1.1-GG Y AOC'): 
                {'demands': 
                    {'2025-12': 54414.2573333333, 
                    '2026-01': 16716.6303686344, 
                    '2026-02': 24640.462, 
                    '2026-03': 13552.0, 
                    '2026-04': 16118.6666666666, 
                    '2026-05': 27104.0, 
                    '2026-06': 44146.6666666667, 
                    '2026-07': 75973.3333333333, 
                    '2026-08': 110880.0, 
                    '2026-09': 123200.0, 
                    '2026-10': 123200.0, 
                    '2026-11': 123200.0, 
                    '2026-12': 123200.0
                    }
                }
        ...
        }
        """
        month_demand = []
        for key, value in self.coc_demand.items():
            if date in value['demands']:
                month_demand.append((key, value['demands'][date]))
            
        return month_demand
    
    
    
    def refresh_cw_inventory_early_month(self, date):
        """
        Return format of cw_inventory_monthly_update:
        {
            'MAT1': {'2025-12': 100, '2026-01': 200, ...},
            'MAT2': {'2025-12': 50, '2026-01': 75, ...},
            ...
        }
        """
        for mat in self.cw_inventory_monthly_update:
            if date in self.cw_inventory_monthly_update[mat]:
                check_in = self.cw_inventory_monthly_update[mat][date]
                self.cw_inventory[mat] += check_in
                continue
                

        return self.cw_inventory
    
    def get_cw_details(self, cust, prod): 
        """
        Return format of cw_details:
        {
        ...
            (cust, prod): [
                {'mat': mat1, 'priority': prio1, 'using': using1},
                {'mat': mat2, 'priority': prio2, 'using': using2},
                ...
            ],
        ...
        }
        """
        return self.cw_details[(cust, prod)]
    
    def sort_coc_demand_in_month(self, date):
        # 获取当月date所有订单信息
        month_demand = self.get_coc_demand_by_month(date)
        """
        过滤掉所有demand_num为0的订单
        """
        # 按照物料和优先级进行归类，例如：(mat, priority) : [(cust, prod, demand_num), ...]
        classified_demand = {}
        for (cust, prod), demand_num in month_demand:
            if demand_num == 0:
                continue
            mat_details = self.get_cw_details(cust, prod)
            for m in mat_details:
                mat = m['mat']
                priority = m['priority']
                key = (mat, priority)
                if key not in classified_demand:
                    classified_demand[key] = []
                # classified_demand[key].append((cust, prod, demand_num))
                classified_demand[key].append((cust, prod))
        
        # 按照物料的优先级进行排序，优先级数字越小优先级越高
        sorted_demand = {
            key: classified_demand[key]
            for key in sorted(classified_demand.keys(), key=lambda k: k[1])
        }
        """
        sorted_demand = {
            (mat1, priority1): [(cust1, prod1), (cust2, prod2), ...], 
            (mat2, priority2): [(cust3, prod3), (cust4, prod4), ...], 
            ...
        }
        """

        return sorted_demand
    

    """
    定义一个独立的全局订单需求状态字典，用于记录每个订单的需求状态，包括已完成的需求和未完成的需求。
    格式为：order_remaining = {(cust, prod): remaining_num, ...}
    """




    # 按照优先级顺序对订单进行初次生产
    def produce_coc_demand_in_month(self, date):

        # 获取订单初始需求
        init_coc_demand = self.get_coc_demand_by_month(date)
        # 此时的init_coc_demand是列表，转换为字典
        init_coc_demand = {item[0]: item[1] for item in init_coc_demand}

        
        # 产量记录
        production_num = {}

        # """
        # 物料对不上的列表
        # """
        no_mathch_list = []

        """
        记录当前月生产情况字典
        production_record = {
            (mat, priority): {
                (cust, prod): {
                    'demanded': demand_num,
                    'remaining': remaining_num
                },

        }
        """
        production_record = {}

        """
        当月生产完成订单列表
        """
        completed_orders = [] # [(cust, prod, demand_num), ...]

        # 刷新PIC库存，基于月初的库存更新
        self.refresh_cw_inventory_early_month(date)

        # 获取当前月所有订单的初始需求状态
        # order_remaining = {(cust, prod): demand_num, ...}
        order_remaining = self.get_coc_demand_by_month(date)
        # 此时的order_remaining是列表，转换为字典
        order_remaining = {item[0]: item[1] for item in order_remaining}
        
        
        """ 
        按照priority从小到大的顺序进行生产，直到库存不足或订单完成，同一个优先级会对应多个物料mat，每个（mat,priority）
        会对应多个订单(cust,prod,demand_num)，根据每个订单的需求量按比例分配物料，分配完后更新库存，统计产量，记录每个订单未完成
        的需求量，继续下一个优先级的生产，直到所有优先级生产完毕或者库存不足为止。      
        """
        # 获取排序后的订单信息
        sorted_demand = self.sort_coc_demand_in_month(date)

        """
        sorted_demand = {
            (mat1, priority1): [(cust1, prod1), (cust2, prod2), ...], 
            (mat2, priority2): [(cust3, prod3), (cust4, prod4), ...], 
            ...
        }
        现在有个很严重的问题，同一个订单(cust, prod)会在多个(mat, priority)中出现，但是demand_num不是通用的，这会导致同一个订单
        在mat1生产后，本来应该有mat2继续生产剩余的部分，但是mat2的demand_num并没有更新，导致mat2还是从零开始重新生产，这是不对的，
        所以需要在每个优先级中，对每个订单的demand_num进行更新，确保在生产mat1后，mat2的demand_num是剩余的部分，而不是从0开始。
        """


        for key, value in sorted_demand.items():
            mat, priority = key
            # 判断订单是否已经完成，如果完成就进入下一个订单
            value = [item for item in value if (item[0], item[1]) not in completed_orders]

            # 先判断库存物料是否足够当前value中的所有订单生产
            total_needed = 0
            for cust, prod in value:
                # 获取订单的未完成需求数量
                demand_num = order_remaining.get((cust, prod), 0)
                mat_details = self.get_cw_details(cust, prod)
                for m in mat_details:
                    if m['mat'] == mat:
                        using = m['using']
                        mat_demand = demand_num * using
                        total_needed += mat_demand
                        break
            available_inventory = self.cw_inventory.get(mat, 0)
            if available_inventory < total_needed:
                # 库存不足，跳过该优先级的生产
                print(f"{date} Production - Mat: {mat}, Priority: {priority} 物料不足，进入按比例生产阶段")

                # 按照比例分配物料进行生产
                """
                ratio_map = {
                    (mat, priority): {
                        (cust, prod): ratio
                    }
                }
                """
                ratio_map = self.compute_ratios(init_coc_demand, sorted_demand, order_remaining)            
                for cust, prod in value:                                
                    ratio = ratio_map[key][(cust, prod)]
                    allocate_amount = int(self.cw_inventory.get(mat, 0) * ratio)
                    # 分配量处以用量，得到实际可生产的数量
                    mat_details = self.get_cw_details(cust, prod)
                    for m in mat_details:
                        if m['mat'] == mat:
                            using = m['using']
                            if using == 0:
                                produce_amount = allocate_amount # 目前默认满足的物料using=0,实际对应using=1
                            else:
                                produce_amount = int(allocate_amount / using)
                            break
                    
                    # 更新库存
                    if mat in self.cw_inventory:
                        self.cw_inventory[mat] -= allocate_amount
                    else:
                        no_mathch_list.append(mat)
                    # 更新未完成订单的需求量 原需求-已生产
                    order_remaining[(cust, prod)] -= produce_amount
                    # 更新产量记录
                    if (cust, prod) not in production_num:
                        production_num[(cust, prod)] = {}
                    if (mat, priority) not in production_num[(cust, prod)]:
                        production_num[(cust, prod)][(mat, priority)] = 0
                    production_num[(cust, prod)][(mat, priority)] += produce_amount

                    if order_remaining[(cust, prod)] <= 0:
                        order_remaining[(cust, prod)] = 0
                    # 如果订单完成，加入完成列表
                    if order_remaining[(cust, prod)] == 0:
                        completed_orders.append((cust, prod))

                    # 记录生产结果
                    if (mat, priority) not in production_record:
                        production_record[(mat, priority)] = {}
                    if (cust, prod) not in production_record[(mat, priority)]:
                        production_record[(mat, priority)][(cust, prod)] = {
                            'demanded': coc_demand[(cust, prod)]['demands'][date],
                            'remaining': order_remaining[(cust, prod)]
                        }
                    else:
                        production_record[(mat, priority)][(cust, prod)]['remaining'] = order_remaining[(cust, prod)]

                    
            else:  # available_inventory >= total_needed
                # 记录生产完成的订单 同时 把这些订单的实时需求量归零 
                print(f"{date} Production - Mat: {mat}, Priority: {priority} 物料充足，全部生产完成")
                for cust, prod in value:
                    completed_orders.append((cust, prod))
                    if (cust, prod) not in production_num:
                        production_num[(cust, prod)] = {}
                    if (mat, priority) not in production_num[(cust, prod)]:
                        production_num[(cust, prod)][(mat, priority)] = 0
                    production_num[(cust, prod)][(mat, priority)] += order_remaining[(cust, prod)]
                    order_remaining[(cust, prod)] = 0



                # 更新库存
                self.cw_inventory[mat] -= total_needed
                # 记录生产结果
                if (mat, priority) not in production_record:
                    production_record[(mat, priority)] = {}
                for cust, prod in value:    
                    if (cust, prod) not in production_record[(mat, priority)]:
                        production_record[(mat, priority)][(cust, prod)] = {
                            'demanded': coc_demand[(cust, prod)]['demands'][date],
                            'remaining': 0
                        }
                    else:
                        production_record[(mat, priority)][(cust, prod)]['remaining'] = 0
        
        # 在production_record中统筹计算每个订单的生产情况
        monthly_production_summary = {}

        for key, value in production_record.items():
            mat, priority = key
            for cust, prod in value.keys():
                if (cust, prod) not in monthly_production_summary.keys():
                    monthly_production_summary[(cust, prod)] = {}
                monthly_production_summary[(cust, prod)]["demanded"] = production_record[(mat, priority)][(cust, prod)]['demanded']
                monthly_production_summary[(cust, prod)]["remaining"] = production_record[(mat, priority)][(cust, prod)]['remaining']
                
        
        # 返回当月生产情况
        return monthly_production_summary, production_record, production_num, init_coc_demand


    
    """
    production_record = {
            (mat, priority): {
                (cust, prod): {
                    'demanded': demanded_num,
                    'remaining': remaining_num
                }
            }
    }

    重新组织production_record，把(cust, prod)放到外层，内层记录使用每个物料的生产情况
    """
    def reorganize_production_record(self, production_record):
        reorganized_record = {}
        for (mat, priority), orders in production_record.items():
            for (cust, prod), info in orders.items():
                if (cust, prod) not in reorganized_record:
                    reorganized_record[(cust, prod)] = {}
                reorganized_record[(cust, prod)][(mat, priority)] = info
        return reorganized_record





    def compute_ratios(self, init_coc_demand, sorted_demand, order_remaining):
        ratio_map = {}
        for key, orders in sorted_demand.items():
            total = sum(init_coc_demand.get((cust, prod), 0) for cust, prod in orders)

            # 计算每个订单的比例
            ratio_map[key] = {}
            for cust, prod in orders:
                ratio = (order_remaining.get((cust, prod), 0) / total) if total > 0 else 0
                ratio_map[key][(cust, prod)] = ratio
        return ratio_map
            




# ============= test ==============
if __name__ == "__main__":
    manager = CW_ProductionManager()
    test_date = ["2025-12","2026-01","2026-02","2026-03","2026-04","2026-05","2026-06","2026-07","2026-08","2026-09","2026-10"
                 ,"2026-11","2026-12"]
    # 全年生产情况记录字典
    annual_production_summary = {}
    # 全年生产细节记录字典
    annual_production_record = {}
    # 全年生产数量记录字典
    annual_production_num = {}
    # 全年需求记录字典
    annual_init_coc_demand = {}


    for date in test_date:
        if date not in annual_production_summary.keys():
            annual_production_summary[date] = {}
        if date not in annual_production_record.keys():
            annual_production_record[date] = {}
        if date not in annual_production_num.keys():
            annual_production_num[date] = {}
        if date not in annual_init_coc_demand.keys():
            annual_init_coc_demand[date] = {}
        
        # 记录当月生产情况
        monthly_production_summary, production_record, production_num, init_coc_demand = manager.produce_coc_demand_in_month(date)
        # 合并到全年生产情况记录
        annual_production_summary[date].update(monthly_production_summary)
        # 重新组织production_record，把(cust, prod)放到外层，内层记录使用每个物料的生产情况
        annual_production_record[date].update(manager.reorganize_production_record(production_record))
        # 合并到全年生产数量记录
        annual_production_num[date].update(production_num)
        # 合并到全年需求记录
        annual_init_coc_demand[date].update(init_coc_demand)
    
    # 输出全年生产情况到.txt文件
    with open("CW_annual_production_summary.txt", "w") as f:
        for date, summary in annual_production_summary.items():
            f.write(f"Date: {date}\n")
            for (cust, prod), info in summary.items():
                f.write(f"  Customer: {cust}, Product: {prod}, Demanded: {info['demanded']}, Remaining: {info['remaining']}\n")
            f.write("\n")
    # 输出重新组织的全年生产细节到.txt文件
    with open("CW_annual_production_record.txt", "w") as f:
        for date, record in annual_production_record.items():
            f.write(f"Date: {date}\n")
            for (cust, prod), orders in record.items():
                f.write(f"  Customer: {cust}, Product: {prod}\n")
                for (mat, priority), info in orders.items():
                    f.write(f"    Material: {mat}, Priority: {priority}, Demanded: {info['demanded']}, Remaining: {info['remaining']}\n")
            f.write("\n")
    # 输出全年生产数量到.txt文件
    with open("CW_annual_production_num.txt", "w") as f:
        for date, num in annual_production_num.items():
            f.write(f"Date: {date}\n")
            for (cust, prod), orders in num.items():
                order_production_in_all = 0
                f.write(f"  Customer: {cust}, Product: {prod}\n")
                for (mat, priority), info in orders.items():
                    f.write(f"    Material: {mat}, Priority: {priority}, Produced: {info}\n")
                    order_production_in_all += info
                f.write(f"    Total Produced: {order_production_in_all}\n")
                f.write(f"    Total Demanded: {annual_init_coc_demand[date].get((cust, prod), 0)}\n")
                den = annual_init_coc_demand[date].get((cust, prod), 0)
                ratio = order_production_in_all / den if den > 0 else 0.0
                ratio = ratio * 100
                f.write(f"    completion ratio: {ratio:.2f}%\n")
            f.write("\n")