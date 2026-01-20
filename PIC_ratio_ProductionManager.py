from COC_demand import * 
from CW_inventory import * 
from CWdata import *
from PIC_inventory import *
from PICdata import *
from PIC_demand import *
import copy

import numpy as np

# PIC CALCULATION
pic_demand = get_pic_demand()
pic_inventory_init = get_pic_init()
pic_inventory_monthly_update = get_pic_monthly_update()
pic_details = get_pic_data()



class PIC_ProductionManager:
    def __init__(self):
        self.pic_demand = copy.deepcopy(pic_demand)
        self.pic_inventory = copy.deepcopy(pic_inventory_init)
        self.pic_inventory_monthly_update = pic_inventory_monthly_update
        self.pic_details = pic_details


    def get_pic_demand_by_month(self, date):
        """
        pic_demand:
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
        for key, value in self.pic_demand.items():
            if date in value['demands']:
                month_demand.append((key, value['demands'][date]))
            
        return month_demand
    
    
    
    def refresh_pic_inventory_early_month(self, date):
        """
        Return format of pic_inventory_monthly_update:
        {
            'MAT1': {'2025-12': 100, '2026-01': 200, ...},
            'MAT2': {'2025-12': 50, '2026-01': 75, ...},
            ...
        }
        """
        for mat in self.pic_inventory_monthly_update:
            if date in self.pic_inventory_monthly_update[mat]:
                check_in = self.pic_inventory_monthly_update[mat][date]
                self.pic_inventory[mat] += check_in
                continue
                

        return self.pic_inventory
    
    def get_pic_details(self, cust, prod): # PIC 是有0优先级的
        """
        Return format of pic_details:
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
        return self.pic_details[(cust, prod)]
    
    def sort_pic_demand_in_month(self, date):
        # 获取当月date所有订单信息
        month_demand = self.get_pic_demand_by_month(date)
        """
        过滤掉所有demand_num为0的订单
        """
        # 按照物料和优先级进行归类，例如：(mat, priority) : [(cust, prod, demand_num), ...]，同时过滤掉所有demand_num为0的订单
        classified_demand = {}
        for (cust, prod), demand_num in month_demand:
            if demand_num == 0:
                continue
            mat_details = self.get_pic_details(cust, prod)
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
    def produce_pic_demand_in_month(self, date):

        # 获取订单初始需求
        init_pic_demand = self.get_pic_demand_by_month(date)
        # 此时的init_pic_demand是列表，转换为字典
        init_pic_demand = {item[0]: item[1] for item in init_pic_demand}


        
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
        self.refresh_pic_inventory_early_month(date)

        # 获取当前月所有订单的初始需求状态
        # order_remaining = {(cust, prod): demand_num, ...}
        order_remaining = self.get_pic_demand_by_month(date)
        # 此时的order_remaining是列表，转换为字典
        order_remaining = {item[0]: item[1] for item in order_remaining}
        
        # total_data = {}

        """ 
        按照priority从小到大的顺序进行生产，直到库存不足或订单完成，同一个优先级会对应多个物料mat，每个（mat,priority）
        会对应多个订单(cust,prod,demand_num)，根据每个订单的需求量按比例分配物料，分配完后更新库存，统计产量，记录每个订单未完成
        的需求量，继续下一个优先级的生产，直到所有优先级生产完毕或者库存不足为止。      
        """
        # 获取排序后的订单信息
        sorted_demand = self.sort_pic_demand_in_month(date)

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
                mat_details = self.get_pic_details(cust, prod)
                for m in mat_details:
                    if m['mat'] == mat:
                        using = m['using']
                        mat_demand = demand_num * using
                        total_needed += mat_demand
                        break
            available_inventory = self.pic_inventory.get(mat, 0)
            if available_inventory < total_needed:
                print(f"{date} Production - Mat: {mat}, Priority: {priority} 物料不足，进入方程组计算阶段")
                # 库存不足，进入求解方程组阶段
                
                """
                例如：
                订单A：(cust1, prod1)，总订单需求：demand_num1，已经生产：produced_num1
                订单B：(cust2, prod2)，总订单需求：demand_num2，已经生产：produced_num2
                订单C：(cust3, prod3)，总订单需求：demand_num3，已经生产：produced_num3
                设当前生产轮三个订单的产量依次为：X = [x1, x2, x3]，
                约束是：
                    x1+produced_num1 <= demand_num1
                    x2+produced_num2 <= demand_num2
                    x3+produced_num3 <= demand_num3 
                    并且：
                    x1, x2, x3 >= 0
                目标方程是：
                    (x1+produced_num1) / demand_num1 近似等于 (x2+produced_num2) / demand_num2 近似等于 (x3+produced_num3) / demand_num3

                求：
                    x1, x2, x3
                """
                # 给订单编号，从0开始
                total_data = {}
                index = 0
                for (cust, prod) in value:
                    if (cust, prod) not in production_num:
                        production_num[(cust, prod)] = {}
                    if (mat, priority) not in production_num[(cust, prod)]:
                        production_num[(cust, prod)][(mat, priority)] = 0
                    total_data[index] = {}
                    # 计算订单已生产总量
                    produced_num = self.cal_order_produced_num(production_num)
                    # 当前订单已生产
                    already_produced = produced_num.get((cust, prod), 0)
                    # 当前订单总需求
                    all_demand = init_pic_demand.get((cust, prod), 0)
                    # 当前订单最多生产数量
                    max_produce_num = all_demand - already_produced
                    # 当前订单已完成的比例
                    completed_ratio = already_produced / all_demand
                    
                    if (cust, prod) not in total_data[index]:
                        total_data[index][(cust, prod)] = {}
                    total_data[index][(cust, prod)]['completed_ratio'] = completed_ratio
                    total_data[index][(cust, prod)]['max_produce_num'] = max_produce_num
                    total_data[index][(cust, prod)]['already_produced'] = already_produced
                    total_data[index][(cust, prod)]['all_demand'] = all_demand
                    index += 1

                enough_or_solution, order_names = self.not_sufficient(key, total_data, order_remaining, index, completed_orders, production_num, production_record)
                if isinstance(enough_or_solution, str):
                    if enough_or_solution == "pop failed!":
                        raise ValueError(f"negative value, and no order to pop out!")

                    if enough_or_solution == "enough":
                        continue

                else:
                    produce_situation = {}
                    cost_mat = 0
                    for ind in range(len(order_names)):
                        (cust, prod) = order_names[ind]
                        x = enough_or_solution[ind]
                        produce_situation[(cust, prod)] = x
                        # 根据(cust, prod)获取当前订单的物料需求详情
                        mat_details = self.get_pic_details(cust, prod)
                        for m in mat_details:
                            if m['mat'] == mat:
                                using = m['using']
                                cost_mat += x * using
                                break
                    # 开始扣除库存
                    self.pic_inventory[mat] -= cost_mat    

                        
                    for (cust, prod) in produce_situation:
                        produce_amount = produce_situation[(cust, prod)]
                        # 更新未完成订单的需求量 原需求-已生产
                        order_remaining[(cust, prod)] -= produce_amount
                        # 更新产量记录
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
                            'demanded': pic_demand[(cust, prod)]['demands'][date],
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
                self.pic_inventory[mat] -= total_needed
                # 记录生产结果
                if (mat, priority) not in production_record:
                    production_record[(mat, priority)] = {}
                for cust, prod in value:    
                    if (cust, prod) not in production_record[(mat, priority)]:
                        production_record[(mat, priority)][(cust, prod)] = {
                            'demanded': pic_demand[(cust, prod)]['demands'][date],
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
        return monthly_production_summary, production_record, production_num, init_pic_demand


    
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


    """
    r: 调节参数，用于按比例生产
    value: [(cust, prod), ...] 待生产的订单
    total_data 结构：
            {
                0: {
                    (cust, prod): {
                        'completed_ratio': 0.5,
                        'max_produce_num': 100,
                        'already_produced': 50,
                        'all_demand': 100
                    }
                },
                1: {
                    (cust, prod): {
                        'completed_ratio': 0.3,
                        'max_produce_num': 80,
                        'already_produced': 24,
                        'all_demand': 80
                    }
                },
                ...
            }
    """

    def not_sufficient(self, key, total_data, order_remaining, index, completed_orders, production_num, production_record):
        d0 = 0
        p0 = 0
        di = 0
        pi = 0
        # 先判断库存物料是否足够当前value中的所有订单生产
        total_needed = 0
        order_names = []
        mat, priority = key 
        for ind in range(index):
            key_order = next(iter(total_data[ind]))  # 取内层字典的第一个也是唯一的 key
            order_names.append(key_order)
        for (cust, prod) in order_names:
            # 获取订单的未完成需求数量
            demand_num = order_remaining.get((cust, prod), 0)
            mat_details = self.get_pic_details(cust, prod)
            for m in mat_details:
                if m['mat'] == mat:
                    using = m['using']
                    mat_demand = demand_num * using
                    total_needed += mat_demand
                    break
        available_inventory = self.pic_inventory.get(mat, 0)
        if available_inventory < total_needed:
            # 获取completed_ratio中最大的一个，并输出index
            completed_ratios = []
            for i in range(index):
                for (cust, prod) in total_data[i]:
                    completed_ratios.append((i, total_data[i][(cust, prod)]['completed_ratio']))
                print(f"completed_ratios: {completed_ratios}")
                
            if completed_ratios:
                # 最大比率对应的 index
                max_completed_ratio_index = max(completed_ratios, key=lambda x: x[1])[0]
                # 最大比率值
                max_completed_ratio = max([r for _, r in completed_ratios])
            else:
                # 如果没有找到任何匹配，给默认值或者处理逻辑
                max_completed_ratio_index = None
                max_completed_ratio = 0    
            
            # 获取所有订单详情，using
            details = {}
                  
            # 获取物料库存
            mat_inven = self.pic_inventory[mat]
            for i, order_combine in enumerate(order_names):
                details[i] = self.get_pic_details(order_combine[0], order_combine[1])

            using = []
            for ind in range(index):
                using_value = 0
                for m in details[ind]:
                    if m['mat'] == mat:
                        using_value = m['using']
                        break
                using.append(using_value)

            # 获取当前有多少个（cust, prod）订单
            num_orders = len(order_names)
            if num_orders == index:
                print(f"yesyesyes, index: {index}, num_orders: {num_orders}")
            
            print(f"total_data: {total_data}")
            # 定义系数矩阵A，num_orders行，num_orders列
            A = np.zeros((num_orders, num_orders))
            zeroDict = total_data[0]
            print(f"zeroDict: {zeroDict}")
            for (cust, prod) in zeroDict:
                d0 = zeroDict[(cust, prod)]['all_demand']
                p0 = zeroDict[(cust, prod)]['already_produced']
            print(f"d0: {d0}")
            print(f"p0: {p0}")

            # 填充系数矩阵A
            for i in range(num_orders):
                if i == 0:
                    for j in range(num_orders):
                        A[0][j] = using[j]
                else:
                    iDict = total_data[i]
                    for (cust, prod) in iDict:
                        pi = iDict[(cust, prod)]['already_produced']
                        di = iDict[(cust, prod)]['all_demand']
                    print(f"pi: {pi}, di: {di}")
                    for j in range(num_orders):
                        if j == 0:
                            A[i][0] = 1 / d0
                        elif i == j:
                            A[i][j] = - 1 / di
                        else:
                            A[i][j] = 0



            # 填充常数矩阵B，长度为num_orders的一维向量
            B = np.zeros((num_orders,))
            for i in range(num_orders):
                if i == 0:
                    B[i] = mat_inven
                else:
                    iDict = total_data[i]
                    for (cust, prod) in iDict:
                        pi = iDict[(cust, prod)]['already_produced']
                        di = iDict[(cust, prod)]['all_demand']
                    print(f"pi: {pi}, di: {di}")

                    B[i] = pi/di - p0/d0

            print(f"A: {A}")
            print(f"B: {B}")

            # 利用numpy构建方程组，并求解
            X = np.linalg.solve(A, B)
            if min(X) < 0:
                if max_completed_ratio_index in total_data:
                    total_data.pop(max_completed_ratio_index)
                else:
                    print(f"negative value, and no order to pop out!")
                    return "pop failed!", order_names
                # 重建一个新字典并重新编号
                new_total_data = {}
                for new_index, old_key in enumerate(sorted(total_data.keys())):
                    new_total_data[new_index] = total_data[old_key]

                total_data = new_total_data
                index = len(total_data)
                return self.not_sufficient(key, total_data, order_remaining, index, completed_orders, production_num, production_record)
            else:
                return X, order_names 
        # pop 订单后，物料足够了，此时直接全额生产
        else:      
            for cust, prod in order_names:
                completed_orders.append((cust, prod))
                if (cust, prod) not in production_num:
                    production_num[(cust, prod)] = {}
                if (mat, priority) not in production_num[(cust, prod)]:
                    production_num[(cust, prod)][(mat, priority)] = 0
                production_num[(cust, prod)][(mat, priority)] += order_remaining[(cust, prod)]
                order_remaining[(cust, prod)] = 0

            # 更新库存
            self.pic_inventory[mat] -= total_needed
            # 记录生产结果
            if (mat, priority) not in production_record:
                production_record[(mat, priority)] = {}
            for cust, prod in order_names:
                if (cust, prod) not in production_record[(mat, priority)]:
                    production_record[(mat, priority)][(cust, prod)] = {
                        'demanded': pic_demand[(cust, prod)]['demands'][date],
                        'remaining': 0
                    }
                else:
                    production_record[(mat, priority)][(cust, prod)]['remaining'] = 0
            
            return "enough", order_names


        
        
    





    """
    计算当前订单已生产的总产量
    order_production: 
        production_num[(cust, prod)] = {
            (mat, priority): produced_num
        }
    """
    def cal_order_produced_num(self, production_num):
        produced_num = {}
        for key, value in production_num.items():
            produced_num[key] = sum(num for num in value.values())
        return produced_num






# ============= test ==============
if __name__ == "__main__":
    manager = PIC_ProductionManager()
    test_date = ["2025-12","2026-01","2026-02","2026-03","2026-04","2026-05","2026-06","2026-07","2026-08","2026-09","2026-10"
                 ,"2026-11","2026-12"]
    # 全年生产情况记录字典
    annual_production_summary = {}
    # 全年生产细节记录字典
    annual_production_record = {}
    # 全年生产数量记录字典
    annual_production_num = {}
    # 全年需求记录字典
    annual_init_pic_demand = {}


    for date in test_date:
        if date not in annual_production_summary.keys():
            annual_production_summary[date] = {}
        if date not in annual_production_record.keys():
            annual_production_record[date] = {}
        if date not in annual_production_num.keys():
            annual_production_num[date] = {}
        if date not in annual_init_pic_demand.keys():
            annual_init_pic_demand[date] = {}
        
        # 记录当月生产情况
        monthly_production_summary, production_record, production_num, init_pic_demand = manager.produce_pic_demand_in_month(date)
        # 合并到全年生产情况记录
        annual_production_summary[date].update(monthly_production_summary)
        # 重新组织production_record，把(cust, prod)放到外层，内层记录使用每个物料的生产情况
        annual_production_record[date].update(manager.reorganize_production_record(production_record))
        # 合并到全年生产数量记录
        annual_production_num[date].update(production_num)
        # 合并到全年需求记录
        annual_init_pic_demand[date].update(init_pic_demand)
    
    # 输出全年生产情况到.txt文件
    with open("RATIO_PIC_annual_production_summary.txt", "w") as f:
        for date, summary in annual_production_summary.items():
            f.write(f"Date: {date}\n")
            for (cust, prod), info in summary.items():
                f.write(f"  Customer: {cust}, Product: {prod}, Demanded: {info['demanded']}, Remaining: {info['remaining']}\n")
            f.write("\n")
    # 输出重新组织的全年生产细节到.txt文件
    with open("RATIO_PIC_annual_production_record.txt", "w") as f:
        for date, record in annual_production_record.items():
            f.write(f"Date: {date}\n")
            for (cust, prod), orders in record.items():
                f.write(f"  Customer: {cust}, Product: {prod}\n")
                for (mat, priority), info in orders.items():
                    f.write(f"    Material: {mat}, Priority: {priority}, Demanded: {info['demanded']}, Remaining: {info['remaining']}\n")
            f.write("\n")
    # 输出全年生产数量到.txt文件
    with open("RATIO_PIC_annual_production_num.txt", "w") as f:
        for date, num in annual_production_num.items():
            f.write(f"Date: {date}\n")
            for (cust, prod), orders in num.items():
                order_production_in_all = 0
                f.write(f"  Customer: {cust}, Product: {prod}\n")
                for (mat, priority), info in orders.items():
                    f.write(f"    Material: {mat}, Priority: {priority}, Produced: {info}\n")
                    order_production_in_all += info
                f.write(f"    Total Produced: {order_production_in_all}\n")
                f.write(f"    Total Demanded: {annual_init_pic_demand[date].get((cust, prod), 0)}\n")
                den = annual_init_pic_demand[date].get((cust, prod), 0)
                ratio = order_production_in_all / den if den > 0 else 0.0
                ratio = ratio * 100
                f.write(f"    completion ratio: {ratio:.2f}%\n")
            f.write("\n")